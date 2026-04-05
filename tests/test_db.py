import json
import pytest

import db
import crypto
import auth


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture()
def seeded_users():
    auth.seed_users()
    return db.get_user("A"), db.get_user("B")


class TestInitDb:
    def test_creates_tables(self):
        # init_db already called by autouse fixture; just verify users table exists
        assert db.get_user("nonexistent") is None

    def test_idempotent(self):
        db.init_db()
        db.init_db()
        assert db.get_user("nonexistent") is None


class TestUserCrud:
    def test_create_and_get_user(self):
        key = crypto.generate_fernet_key()
        combo = {"ctrl": False, "shift": False, "alt": False, "key": "1234"}
        db.create_user("X", "hash123", combo, key)
        user = db.get_user("X")
        assert user["username"] == "X"
        assert user["password_hash"] == "hash123"
        assert json.loads(user["key_combo"]) == combo
        assert user["fernet_key"] == key

    def test_get_nonexistent_user(self):
        assert db.get_user("nobody") is None

    def test_create_duplicate_user_ignored(self):
        key = crypto.generate_fernet_key()
        combo = {"key": "a"}
        db.create_user("Y", "hash1", combo, key)
        db.create_user("Y", "hash2", combo, key)
        assert db.get_user("Y")["password_hash"] == "hash1"

    def test_update_password(self):
        key = crypto.generate_fernet_key()
        db.create_user("Z", "old_hash", {"key": "x"}, key)
        db.update_password("Z", "new_hash")
        assert db.get_user("Z")["password_hash"] == "new_hash"

    def test_update_key_combo(self):
        key = crypto.generate_fernet_key()
        db.create_user("W", "hash", {"key": "a"}, key)
        new_combo = {"ctrl": True, "shift": False, "alt": False, "key": "d"}
        db.update_key_combo("W", new_combo)
        assert json.loads(db.get_user("W")["key_combo"]) == new_combo


class TestMessageCrud:
    def test_create_and_get_message(self, seeded_users):
        user_a, user_b = seeded_users
        ct = crypto.encrypt_message("hello", user_b["fernet_key"])
        db.create_message("A", "B", ct)
        messages = db.get_messages()
        assert len(messages) == 1
        assert messages[0]["sender"] == "A"
        assert messages[0]["recipient"] == "B"
        assert messages[0]["ciphertext"] == ct
        assert messages[0]["status"] == "PENDING"

    def test_messages_ordered_by_timestamp(self, seeded_users):
        user_a, user_b = seeded_users
        for i in range(3):
            ct = crypto.encrypt_message(f"msg{i}", user_b["fernet_key"])
            db.create_message("A", "B", ct)
        messages = db.get_messages()
        assert len(messages) == 3
        # Timestamps should be non-decreasing
        for i in range(len(messages) - 1):
            assert messages[i]["timestamp"] <= messages[i + 1]["timestamp"]

    def test_update_message_status(self, seeded_users):
        user_a, user_b = seeded_users
        ct = crypto.encrypt_message("test", user_b["fernet_key"])
        db.create_message("A", "B", ct)
        msg_id = db.get_messages()[0]["id"]
        db.update_message_status(msg_id, "PROCESSED")
        assert db.get_messages()[0]["status"] == "PROCESSED"

    def test_clear_chat(self, seeded_users):
        user_a, user_b = seeded_users
        ct = crypto.encrypt_message("test", user_b["fernet_key"])
        db.create_message("A", "B", ct)
        db.create_message("B", "A", ct)
        assert len(db.get_messages()) == 2
        db.clear_chat()
        assert len(db.get_messages()) == 0

    def test_empty_messages(self):
        assert db.get_messages() == []


class TestEncryptionIntegration:
    """Test the full encrypt-with-recipient-key / decrypt flow."""

    def test_sender_and_recipient_can_decrypt(self, seeded_users):
        user_a, user_b = seeded_users
        plaintext = "secret command"
        # A sends to B: encrypted with B's key
        ct = crypto.encrypt_message(plaintext, user_b["fernet_key"])
        db.create_message("A", "B", ct)
        msg = db.get_messages()[0]
        # Both decrypt using recipient's (B's) key
        assert crypto.decrypt_message(msg["ciphertext"], user_b["fernet_key"]) == plaintext

    def test_wrong_user_key_cannot_decrypt(self, seeded_users):
        user_a, user_b = seeded_users
        ct = crypto.encrypt_message("secret", user_b["fernet_key"])
        db.create_message("A", "B", ct)
        msg = db.get_messages()[0]
        # A's key should NOT decrypt a message encrypted with B's key
        with pytest.raises(Exception):
            crypto.decrypt_message(msg["ciphertext"], user_a["fernet_key"])
