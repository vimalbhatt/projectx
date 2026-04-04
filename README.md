# Command

Encrypted communication app for two users (A and B). Commands are encrypted at rest using Fernet symmetric encryption. Users decrypt commands temporarily using a personal key combination.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Default Credentials

| User | Key |
|------|-----|
| A | `changeme` |
| B | `changeme` |

Default decrypt key combo: **Ctrl+Shift+Z**

## Usage

1. Open two browser tabs
2. Log in as **A** in one tab and **B** in the other
3. Type a command and press the send icon
4. Commands appear encrypted on both sides

### Decrypting Commands

1. Click on an encrypted command to select it (blue glow)
2. Press your key combo (default: Ctrl+Shift+Z) to reveal the plaintext
3. Plaintext auto-hides after 5 seconds
4. Both sender and recipient can decrypt any command

### Settings (Hidden Sidebar)

The settings panel is hidden by default. To access it:

1. Click the **Command** title input at the top
2. Press your key combo (Ctrl+Shift+Z)
3. The sidebar appears with options to:
   - Change your login key
   - Change your decrypt key combo
   - Logout

## Architecture

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app - login, command display, settings |
| `db.py` | SQLite layer (WAL mode) - users and commands tables |
| `crypto.py` | Fernet encrypt/decrypt utilities |
| `auth.py` | bcrypt key hashing, user seeding |
| `components/chat_decryptor/` | Custom Streamlit component for decrypt UX |

## Encryption

- Each user has a unique Fernet key stored in the database
- Commands are encrypted with the **recipient's** Fernet key
- Decryption happens server-side; the frontend only handles display toggling
- Login keys are hashed with bcrypt

## Status Labels

- **PENDING** - command has not been decrypted by the recipient
- **PROCESSED** - command has been decrypted at least once by the recipient

## Color Coding

- User A commands: dark blue background
- User B commands: dark purple background
