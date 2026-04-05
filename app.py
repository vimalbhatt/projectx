import json
import streamlit as st
import streamlit.components.v1 as st_components
from datetime import datetime

import db
import crypto
import auth
from components.chat_decryptor import chat_decryptor


def format_combo(combo):
    parts = []
    if combo.get("ctrl"):
        parts.append("Ctrl")
    if combo.get("shift"):
        parts.append("Shift")
    if combo.get("alt"):
        parts.append("Alt")
    if combo.get("key"):
        parts.append(combo["key"].upper())
    return "+".join(parts) if parts else "None"


# --- Init ---
auth.seed_users()

st.set_page_config(page_title="Command", page_icon="🔒", layout="centered")

# Hide password visibility toggle icon
st.markdown("""
<style>
    [data-testid="stTextInput"] button[kind="icon"] {
        display: none !important;
    }
    .stTextInput button {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Defaults ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "decrypted_messages" not in st.session_state:
    st.session_state.decrypted_messages = {}  # msg_id -> plaintext


def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.decrypted_messages = {}


# --- Login Page ---
if not st.session_state.logged_in:
    st.title("Command")
    st.markdown("Log in as User **A** or **B**")

    if "selected_user" not in st.session_state:
        st.session_state.selected_user = "A"

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("A", use_container_width=True, type="primary" if st.session_state.selected_user == "A" else "secondary"):
            st.session_state.selected_user = "A"
            st.rerun()
    with col_b:
        if st.button("B", use_container_width=True, type="primary" if st.session_state.selected_user == "B" else "secondary"):
            st.session_state.selected_user = "B"
            st.rerun()

    username = st.session_state.selected_user
    with st.form("login_form"):
        password = st.text_input("Key", type="password")
        submitted = st.form_submit_button(":material/lock_open:", use_container_width=True)
        if submitted:
            user = db.get_user(username)
            if user and auth.verify_password(password, user["password_hash"]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid key.")
    st.stop()

# --- Chat Page (logged in) ---
me = st.session_state.username
other = "B" if me == "A" else "A"
my_user = db.get_user(me)
my_fernet_key = my_user["fernet_key"]
my_key_combo = json.loads(my_user["key_combo"])

# --- Hide sidebar by default, reveal with key combo in title input ---
combo_js = json.dumps(my_key_combo)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebar"].revealed { display: flex !important; }
    [data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: Settings ---
with st.sidebar:
    st.markdown(f"### Logged in as **{me}**")
    if st.button("Logout"):
        logout()
        st.rerun()

    st.divider()
    st.subheader("Change Key")
    with st.form("change_pw", clear_on_submit=True):
        old_pw = st.text_input("Current key", type="password", key="old_pw")
        new_pw = st.text_input("New key", type="password", key="new_pw")
        new_pw2 = st.text_input("Confirm new key", type="password", key="new_pw2")
        if st.form_submit_button("Update Key"):
            if not auth.verify_password(old_pw, my_user["password_hash"]):
                st.error("Current key is wrong.")
            elif not new_pw or new_pw != new_pw2:
                st.error("New keys don't match or are empty.")
            else:
                db.update_password(me, auth.hash_password(new_pw))
                st.success("Key updated.")

    st.divider()
    st.subheader("Decrypt Key Combo")

    st.markdown("Set a new key combination:")
    kc_col1, kc_col2, kc_col3 = st.columns(3)
    with kc_col1:
        kc_ctrl = st.checkbox("Ctrl", value=False, key="kc_ctrl")
    with kc_col2:
        kc_shift = st.checkbox("Shift", value=False, key="kc_shift")
    with kc_col3:
        kc_alt = st.checkbox("Alt", value=False, key="kc_alt")
    kc_key = st.text_input("Key (character or PIN sequence)", value="", max_chars=10, key="kc_key")

    if st.button("Save Key Combo"):
        if not kc_key:
            st.error("Key cannot be empty.")
        else:
            new_combo = {"ctrl": kc_ctrl, "shift": kc_shift, "alt": kc_alt, "key": kc_key.lower()}
            db.update_key_combo(me, new_combo)
            st.success("Key combo updated.")
            st.rerun()

# --- Main Chat Area (title as input that captures key combo) ---
st_components.html(f"""
<style>
  .title-input {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #fafafa;
    background: transparent;
    border: none;
    outline: none;
    width: 100%;
    caret-color: transparent;
    cursor: text;
    padding: 0;
    margin: 0 0 4px 0;
  }}
  .title-input::placeholder {{ color: #fafafa; }}
  .title-input:focus {{ caret-color: transparent; }}
  .title-input.primed {{ color: #89b4fa; }}
  .caption {{ font-size: 0.85rem; color: #6c7086; margin: 0; }}
</style>
<input class="title-input" type="text" value="Command" placeholder="Command" id="titleInput" inputmode="numeric" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
<p class="caption">You are <b>{me}</b> &middot; connected to <b>{other}</b></p>
<script>
(function() {{
    const combo = {combo_js};
    const input = document.getElementById("titleInput");
    const parent = window.parent.document;

    let titleKeyBuffer = "";
    let titleKeyTimeout = null;
    const hasModifiers = !!combo.ctrl || !!combo.shift || !!combo.alt;
    const isSequence = !hasModifiers && combo.key && combo.key.length > 1;

    input.addEventListener("keydown", function(e) {{
        e.preventDefault();
        let matched = false;

        if (isSequence) {{
            if (e.key.length === 1) {{
                titleKeyBuffer += e.key.toLowerCase();
                if (titleKeyBuffer.length > combo.key.length) {{
                    titleKeyBuffer = titleKeyBuffer.slice(-combo.key.length);
                }}
                clearTimeout(titleKeyTimeout);
                titleKeyTimeout = setTimeout(function() {{ titleKeyBuffer = ""; }}, 3000);
                matched = (titleKeyBuffer === combo.key.toLowerCase());
                if (matched) titleKeyBuffer = "";
            }}
        }} else {{
            matched =
                (!!combo.ctrl === e.ctrlKey) &&
                (!!combo.shift === e.shiftKey) &&
                (!!combo.alt === e.altKey) &&
                (e.key.toLowerCase() === combo.key.toLowerCase());
        }}

        if (matched) {{
            const sidebar = parent.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {{
                sidebar.classList.toggle("revealed");
            }}
        }}
    }});

    input.addEventListener("focus", function() {{
        input.classList.add("primed");
    }});
    input.addEventListener("blur", function() {{
        input.classList.remove("primed");
    }});

}})();
</script>
""", height=75)

# Display messages in a scrollable container
messages = db.get_messages()
chat_container = st.container(height=400)
with chat_container:
    if not messages:
        st.info("No commands yet. Send the first one!")
    else:
        for msg in messages:
            msg_id = msg["id"]
            is_mine = msg["sender"] == me
            is_to_me = msg["recipient"] == me
            sender_label = "You" if is_mine else msg["sender"]

            # Parse timestamp
            try:
                ts = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            except (ValueError, TypeError):
                ts = msg["timestamp"]

            # Status badge
            status = msg["status"]
            badge = "🔵 " if status == "PENDING" and is_to_me else ""

            # Message header
            align = "right" if is_mine else "left"
            st.markdown(
                f"<div style='text-align:{align};'>"
                f"<small style='color:#6c7086;'>{badge}{sender_label} &middot; {ts} &middot; {status}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Use decryptor component for all messages
            plaintext = st.session_state.decrypted_messages.get(msg_id)
            result = chat_decryptor(
                msg_id=msg_id,
                ciphertext=msg["ciphertext"],
                sender=msg["sender"],
                plaintext=plaintext,
                key_combo=my_key_combo,
                key=f"decrypt_{msg_id}",
            )

            # Handle component signals
            if result and isinstance(result, dict):
                action = result.get("action")
                if action == "decrypt_requested" and msg_id not in st.session_state.decrypted_messages:
                    try:
                        # Decrypt with recipient's key
                        recipient_key = db.get_user(msg["recipient"])["fernet_key"]
                        decrypted = crypto.decrypt_message(msg["ciphertext"], recipient_key)
                        st.session_state.decrypted_messages[msg_id] = decrypted
                        if is_to_me and msg["status"] == "PENDING":
                            db.update_message_status(msg_id, "PROCESSED")
                        st.rerun()
                    except Exception:
                        st.error(f"Failed to decrypt command {msg_id}.")
                elif action == "re_encrypt":
                    st.session_state.decrypted_messages.pop(msg_id, None)
                    st.rerun()

            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

# Send message input at bottom
with st.form("send_msg", clear_on_submit=True):
    col_input, col_send = st.columns([4, 1])
    with col_input:
        msg_text = st.text_input("Command", placeholder=f"Type a command to {other}...", key="msg_input", label_visibility="collapsed")
    with col_send:
        sent = st.form_submit_button(":material/send:", use_container_width=True)
    if sent and msg_text.strip():
        recipient_user = db.get_user(other)
        ciphertext = crypto.encrypt_message(msg_text.strip(), recipient_user["fernet_key"])
        db.create_message(me, other, ciphertext)
        st.session_state.decrypted_messages = {}
        st.rerun()
    elif sent:
        st.warning("Command cannot be empty.")

# Action buttons
col_clear, col_refresh = st.columns(2)
with col_clear:
    if st.button(":material/delete_outline:", use_container_width=True):
        db.clear_chat()
        st.session_state.decrypted_messages = {}
        st.rerun()
with col_refresh:
    if st.button(":material/refresh:", use_container_width=True):
        st.rerun()

# Auto-refresh using streamlit fragment
@st.fragment(run_every=5)
def _auto_refresh():
    pass

_auto_refresh()
