import json
import pytest

import auth
import db


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = auth.hash_password("test")
        assert isinstance(h, str)

    def test_verify_correct_password(self):
        h = auth.hash_password("mypassword")
        assert auth.verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = auth.hash_password("mypassword")
        assert auth.verify_password("wrong", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = auth.hash_password("same")
        h2 = auth.hash_password("same")
        assert h1 != h2  # bcrypt salts differ

    def test_verify_still_works_with_different_hashes(self):
        h1 = auth.hash_password("same")
        h2 = auth.hash_password("same")
        assert auth.verify_password("same", h1) is True
        assert auth.verify_password("same", h2) is True


class TestDefaultKeyCombos:
    def test_default_combo_is_sequence(self):
        for user in ("A", "B"):
            combo = auth.DEFAULT_KEY_COMBOS[user]
            assert combo["ctrl"] is False
            assert combo["shift"] is False
            assert combo["alt"] is False
            assert combo["key"] == "1234"

    def test_default_combo_has_no_modifiers(self):
        for combo in auth.DEFAULT_KEY_COMBOS.values():
            assert not combo["ctrl"]
            assert not combo["shift"]
            assert not combo["alt"]


class TestSeedUsers:
    @pytest.fixture(autouse=True)
    def _use_tmp_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))

    def test_creates_both_users(self):
        auth.seed_users()
        user_a = db.get_user("A")
        user_b = db.get_user("B")
        assert user_a is not None
        assert user_b is not None

    def test_default_password_works(self):
        auth.seed_users()
        user_a = db.get_user("A")
        assert auth.verify_password("changeme", user_a["password_hash"])

    def test_users_have_fernet_keys(self):
        auth.seed_users()
        for name in ("A", "B"):
            user = db.get_user(name)
            assert user["fernet_key"] is not None
            assert len(user["fernet_key"]) > 0

    def test_users_have_key_combos(self):
        auth.seed_users()
        for name in ("A", "B"):
            user = db.get_user(name)
            combo = json.loads(user["key_combo"])
            assert combo["key"] == "1234"

    def test_seed_is_idempotent(self):
        auth.seed_users()
        user_a_key = db.get_user("A")["fernet_key"]
        auth.seed_users()
        assert db.get_user("A")["fernet_key"] == user_a_key

    def test_different_fernet_keys_per_user(self):
        auth.seed_users()
        key_a = db.get_user("A")["fernet_key"]
        key_b = db.get_user("B")["fernet_key"]
        assert key_a != key_b
