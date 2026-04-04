import os
import streamlit.components.v1 as components

_RELEASE = False
_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

if _RELEASE:
    _component_func = components.declare_component("chat_decryptor", path=_COMPONENT_DIR)
else:
    _component_func = components.declare_component("chat_decryptor", path=_COMPONENT_DIR)


def chat_decryptor(msg_id, ciphertext, sender, plaintext=None, key_combo=None, key=None):
    """Render a single chat message with decrypt-on-keycombo behavior.

    Args:
        msg_id: Message ID
        ciphertext: The encrypted text to display by default
        sender: 'A' or 'B' for color coding
        plaintext: If provided, the decrypted text to show temporarily
        key_combo: Dict like {"ctrl": true, "shift": true, "key": "d"}
        key: Unique component key
    """
    return _component_func(
        msg_id=msg_id,
        ciphertext=ciphertext,
        sender=sender,
        plaintext=plaintext,
        key_combo=key_combo or {},
        key=key,
        default=None,
    )
