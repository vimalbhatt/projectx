import pytest
from cryptography.fernet import Fernet, InvalidToken

import crypto


class TestGenerateFernetKey:
    def test_returns_valid_fernet_key(self):
        key = crypto.generate_fernet_key()
        # Should not raise
        Fernet(key)

    def test_returns_bytes(self):
        key = crypto.generate_fernet_key()
        assert isinstance(key, bytes)

    def test_generates_unique_keys(self):
        keys = {crypto.generate_fernet_key() for _ in range(10)}
        assert len(keys) == 10


class TestEncryptDecrypt:
    @pytest.fixture()
    def fernet_key(self):
        return crypto.generate_fernet_key()

    def test_roundtrip(self, fernet_key):
        plaintext = "hello world"
        ciphertext = crypto.encrypt_message(plaintext, fernet_key)
        assert crypto.decrypt_message(ciphertext, fernet_key) == plaintext

    def test_ciphertext_is_string(self, fernet_key):
        ciphertext = crypto.encrypt_message("test", fernet_key)
        assert isinstance(ciphertext, str)

    def test_ciphertext_differs_from_plaintext(self, fernet_key):
        plaintext = "secret"
        ciphertext = crypto.encrypt_message(plaintext, fernet_key)
        assert ciphertext != plaintext

    def test_same_plaintext_produces_different_ciphertext(self, fernet_key):
        ct1 = crypto.encrypt_message("same", fernet_key)
        ct2 = crypto.encrypt_message("same", fernet_key)
        assert ct1 != ct2

    def test_wrong_key_fails(self):
        key1 = crypto.generate_fernet_key()
        key2 = crypto.generate_fernet_key()
        ciphertext = crypto.encrypt_message("secret", key1)
        with pytest.raises(InvalidToken):
            crypto.decrypt_message(ciphertext, key2)

    def test_empty_string(self, fernet_key):
        ciphertext = crypto.encrypt_message("", fernet_key)
        assert crypto.decrypt_message(ciphertext, fernet_key) == ""

    def test_unicode(self, fernet_key):
        plaintext = "hello 🔒 world 日本語"
        ciphertext = crypto.encrypt_message(plaintext, fernet_key)
        assert crypto.decrypt_message(ciphertext, fernet_key) == plaintext
