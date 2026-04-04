from cryptography.fernet import Fernet


def generate_fernet_key() -> bytes:
    return Fernet.generate_key()


def encrypt_message(plaintext: str, fernet_key: bytes) -> str:
    f = Fernet(fernet_key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_message(ciphertext: str, fernet_key: bytes) -> str:
    f = Fernet(fernet_key)
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
