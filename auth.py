import bcrypt
import db
import crypto

DEFAULT_PASSWORD = "changeme"
DEFAULT_KEY_COMBOS = {
    "A": {"ctrl": True, "shift": True, "key": "z"},
    "B": {"ctrl": True, "shift": True, "key": "z"},
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def seed_users():
    """Create users A and B with default passwords and Fernet keys if they don't exist."""
    db.init_db()
    for username in ("A", "B"):
        if db.get_user(username) is None:
            pw_hash = hash_password(DEFAULT_PASSWORD)
            fernet_key = crypto.generate_fernet_key()
            key_combo = DEFAULT_KEY_COMBOS[username]
            db.create_user(username, pw_hash, key_combo, fernet_key)
