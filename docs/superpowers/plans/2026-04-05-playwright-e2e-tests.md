# Playwright E2E Tests for Command App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Playwright end-to-end tests that verify all user-facing functionality of the Command encrypted communication app running on a live Streamlit server.

**Architecture:** Tests launch a Streamlit server as a subprocess fixture, interact with the app through Chromium, and clean up between tests by using the clear-chat button and re-seeding the DB. Streamlit custom components render inside iframes, so tests must use `frame_locator()` to reach into the `chat_decryptor` component DOM. A shared helper module (`e2e/helpers.py`) provides login, send-message, and iframe-accessor utilities to keep tests DRY.

**Tech Stack:** Playwright for Python (`playwright`), pytest-playwright, Streamlit (existing)

---

## File Structure

| Path | Responsibility |
|---|---|
| `e2e/conftest.py` | pytest fixtures: start/stop Streamlit server, fresh browser page, DB cleanup |
| `e2e/helpers.py` | Reusable helpers: `login()`, `send_command()`, `get_decryptor_frame()`, `clear_chat()` |
| `e2e/test_login.py` | Login page: valid/invalid credentials, user switching |
| `e2e/test_send_message.py` | Sending commands: message appears encrypted, empty message rejected |
| `e2e/test_decrypt.py` | Decryption: PIN sequence triggers decrypt, auto re-encrypt after 5s, status updates |
| `e2e/test_sidebar.py` | Hidden sidebar: revealed via PIN on title input, settings accessible |
| `e2e/test_mobile_keyboard.py` | Mobile support: tapping message focuses hidden input, PIN typed into hidden input triggers decrypt |
| `e2e/test_clear_chat.py` | Clear chat: delete button clears all messages |
| `playwright.config.py` | Playwright configuration (base URL, timeouts, headless) |

---

### Task 1: Install dependencies and configure Playwright

**Files:**
- Modify: `requirements.txt`
- Create: `playwright.config.py`
- Create: `e2e/__init__.py`

- [ ] **Step 1: Add test dependencies to requirements.txt**

Append to `requirements.txt`:
```
pytest>=8.0.0
playwright>=1.40.0
pytest-playwright>=0.4.0
```

- [ ] **Step 2: Install dependencies and Playwright browsers**

Run:
```bash
pip install playwright pytest-playwright --break-system-packages
python3 -m playwright install chromium
```
Expected: Chromium downloads successfully

- [ ] **Step 3: Create Playwright config**

Create `playwright.config.py`:
```python
# Playwright pytest config — imported by conftest.py
BASE_URL = "http://localhost:8599"
STREAMLIT_PORT = 8599
STREAMLIT_STARTUP_TIMEOUT = 15  # seconds to wait for server
DEFAULT_TIMEOUT = 10000  # ms for Playwright actions
```

- [ ] **Step 4: Create e2e package init**

Create `e2e/__init__.py` (empty file).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt playwright.config.py e2e/__init__.py
git commit -m "chore: add Playwright E2E test dependencies and config"
```

---

### Task 2: Server fixture and helpers

**Files:**
- Create: `e2e/conftest.py`
- Create: `e2e/helpers.py`

- [ ] **Step 1: Create conftest.py with server fixture**

```python
import subprocess
import time
import socket
import pytest
import os

# Add project root to path so Streamlit can find modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import Page
from playwright_config import BASE_URL, STREAMLIT_PORT, STREAMLIT_STARTUP_TIMEOUT, DEFAULT_TIMEOUT


def _port_open(port, host="localhost"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def streamlit_server():
    """Start Streamlit server once for the entire test session."""
    # Remove stale DB so tests start clean
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chat.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", str(STREAMLIT_PORT),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    deadline = time.time() + STREAMLIT_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _port_open(STREAMLIT_PORT):
            # Give Streamlit a moment to fully initialize
            time.sleep(1)
            break
        time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError(f"Streamlit server did not start within {STREAMLIT_STARTUP_TIMEOUT}s")

    yield proc

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture()
def app_page(streamlit_server, page: Page):
    """Provide a Playwright page pointed at the running app with clean DB state."""
    page.set_default_timeout(DEFAULT_TIMEOUT)
    # Clear messages between tests to prevent pollution
    import db as _db
    _db.clear_chat()
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    return page
```

- [ ] **Step 2: Create helpers.py**

```python
from __future__ import annotations

from playwright.sync_api import Page, FrameLocator


def login(page: Page, user: str = "A", password: str = "changeme"):
    """Log in as the specified user."""
    # Select user button
    page.get_by_role("button", name=user, exact=True).click()
    page.wait_for_timeout(500)
    # Fill password and submit
    page.get_by_label("Key").fill(password)
    page.locator('[data-testid="stFormSubmitButton"] button').first.click()
    # Wait for chat page to fully load
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)


def send_command(page: Page, text: str):
    """Type a command and click send."""
    # Target the send form specifically (has the Command input)
    send_form = page.locator('[data-testid="stForm"]').filter(has_text="command")
    send_form.get_by_role("textbox").fill(text)
    send_form.locator('[data-testid="stFormSubmitButton"] button').click()
    page.wait_for_timeout(1000)


def get_decryptor_frames(page: Page) -> list[FrameLocator]:
    """Return all chat_decryptor iframe frame locators.

    Streamlit doesn't guarantee component names in iframe titles,
    so we find all iframes and skip the first one (title header).
    We identify decryptor frames by checking for .msg-container inside.
    """
    iframes = page.locator("iframe")
    count = iframes.count()
    frames = []
    for i in range(count):
        fl = page.frame_locator(f"iframe >> nth={i}")
        # Check if this iframe contains a msg-container (decryptor)
        if fl.locator(".msg-container").count() > 0:
            frames.append(fl)
    return frames


def get_title_frame(page: Page) -> FrameLocator:
    """Return the title/header iframe frame locator."""
    # The title iframe contains .title-input
    iframes = page.locator("iframe")
    count = iframes.count()
    for i in range(count):
        fl = page.frame_locator(f"iframe >> nth={i}")
        if fl.locator(".title-input").count() > 0:
            return fl
    return page.frame_locator("iframe").first


def clear_chat(page: Page):
    """Click the delete/clear button to remove all messages."""
    page.get_by_role("button", name="delete_outline").click()
    page.wait_for_timeout(1000)


def type_pin_in_frame(frame: FrameLocator, pin: str = "1234"):
    """Click a message container inside a decryptor frame, then type PIN.

    Clicking the container focuses the hidden input inside it.
    Then we type each digit into the hidden input.
    """
    container = frame.locator(".msg-container")
    container.click()
    hidden_input = frame.locator(".hidden-input")
    for char in pin:
        hidden_input.press(char)
```

- [ ] **Step 3: Verify server starts and page loads**

Run:
```bash
python3 -m pytest e2e/ -v --co
```
Expected: Test collection succeeds with no import errors

- [ ] **Step 4: Commit**

```bash
git add e2e/conftest.py e2e/helpers.py
git commit -m "test: add Playwright server fixtures and E2E helpers"
```

---

### Task 3: Login tests

**Files:**
- Create: `e2e/test_login.py`

- [ ] **Step 1: Write login tests**

```python
import pytest
from e2e.helpers import login


class TestLogin:
    def test_login_page_shows_title(self, app_page):
        assert app_page.get_by_text("Command").first.is_visible()

    def test_login_page_shows_user_buttons(self, app_page):
        assert app_page.get_by_role("button", name="A", exact=True).is_visible()
        assert app_page.get_by_role("button", name="B", exact=True).is_visible()

    def test_login_with_valid_key(self, app_page):
        login(app_page, "A", "changeme")
        # After login, the title-input iframe should contain "You are A"
        frame = app_page.frame_locator("iframe").first
        assert frame.get_by_text("You are A").is_visible()

    def test_login_with_invalid_key(self, app_page):
        app_page.get_by_role("button", name="A", exact=True).click()
        app_page.wait_for_timeout(500)
        app_page.get_by_label("Key").fill("wrongpassword")
        app_page.locator('[data-testid="stFormSubmitButton"] button').first.click()
        app_page.wait_for_timeout(1000)
        assert app_page.get_by_text("Invalid key").is_visible()

    def test_switch_user_before_login(self, app_page):
        # Default is A, switch to B
        app_page.get_by_role("button", name="B", exact=True).click()
        app_page.wait_for_timeout(500)
        login(app_page, "B", "changeme")
        frame = app_page.frame_locator("iframe").first
        assert frame.get_by_text("You are B").is_visible()
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_login.py -v --headed
```
Expected: All 5 tests pass. Use `--headed` first time to visually verify, then switch to headless.

- [ ] **Step 3: Commit**

```bash
git add e2e/test_login.py
git commit -m "test: add Playwright login E2E tests"
```

---

### Task 4: Send message tests

**Files:**
- Create: `e2e/test_send_message.py`

- [ ] **Step 1: Write send message tests**

```python
import pytest
from e2e.helpers import login, send_command, get_decryptor_frames, clear_chat


class TestSendMessage:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")

    def test_send_command_appears_in_chat(self):
        send_command(self.page, "hello from A")
        # At least one decryptor iframe should exist
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        # Message should show as ciphertext (monospace, not plaintext)
        first_frame = frames[-1]  # Most recent message
        msg_text = first_frame.locator(".msg-text").first
        assert msg_text.is_visible()
        # Ciphertext should NOT equal our plaintext
        text_content = msg_text.text_content()
        assert text_content != "hello from A"

    def test_send_empty_command_rejected(self):
        send_command(self.page, "")
        assert self.page.get_by_text("Command cannot be empty").is_visible()

    def test_message_shows_sender_label(self):
        send_command(self.page, "test sender label")
        # Sender label should say "You" for our own messages
        assert self.page.get_by_text("You").first.is_visible()

    def test_message_status_pending(self):
        send_command(self.page, "check status")
        assert self.page.get_by_text("PENDING").first.is_visible()
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_send_message.py -v
```
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add e2e/test_send_message.py
git commit -m "test: add Playwright send message E2E tests"
```

---

### Task 5: Decrypt tests (PIN sequence)

**Files:**
- Create: `e2e/test_decrypt.py`

- [ ] **Step 1: Write decrypt tests**

This is the most critical test file. The decrypt flow involves:
1. Click on an encrypted message inside its iframe
2. Type PIN "1234" into the hidden input inside the iframe
3. Streamlit re-renders with plaintext visible
4. After 5s, message re-encrypts automatically

```python
import pytest
from e2e.helpers import login, send_command, get_decryptor_frames, type_pin_in_frame


class TestDecrypt:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")
        send_command(self.page, "secret message 123")
        self.page.wait_for_timeout(1000)

    def test_pin_sequence_decrypts_message(self):
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        frame = frames[-1]
        type_pin_in_frame(frame, "1234")
        # Wait for Streamlit rerun
        self.page.wait_for_timeout(2000)
        # After decrypt, re-fetch frames (DOM may have changed)
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        # Should show decrypted text with .plain class
        plain = frame.locator(".msg-text.plain")
        assert plain.is_visible(timeout=5000)
        assert plain.text_content() == "secret message 123"

    def test_decrypted_message_has_timer_bar(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        type_pin_in_frame(frame, "1234")
        self.page.wait_for_timeout(2000)
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        timer = frame.locator(".timer-bar")
        assert timer.is_visible(timeout=5000)

    def test_message_re_encrypts_after_timeout(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        type_pin_in_frame(frame, "1234")
        self.page.wait_for_timeout(2000)
        # Verify it decrypted
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        assert frame.locator(".msg-text.plain").is_visible(timeout=5000)
        # Wait for 5s re-encrypt timeout + Streamlit rerun buffer
        self.page.wait_for_timeout(7000)
        # Should be back to ciphertext
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        # .plain class should be gone after re-encrypt
        from playwright.sync_api import expect
        expect(frame.locator(".msg-text.plain")).not_to_be_visible(timeout=3000)

    def test_wrong_pin_does_not_decrypt(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        type_pin_in_frame(frame, "9999")
        self.page.wait_for_timeout(2000)
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        # Should still show ciphertext, not plain
        plain = frame.locator(".msg-text.plain")
        assert plain.count() == 0

    def test_status_changes_to_processed_after_decrypt(self):
        """When recipient decrypts, status changes from PENDING to PROCESSED."""
        # Log out and log in as B (the recipient)
        # First, we need to reveal sidebar to log out
        # Use a fresh page instead for simplicity
        self.page.goto(self.page.url)
        self.page.wait_for_load_state("networkidle")
        login(self.page, "B", "changeme")
        self.page.wait_for_timeout(1000)
        # B should see the message from A
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        frame = frames[-1]
        type_pin_in_frame(frame, "1234")
        self.page.wait_for_timeout(2000)
        # After decrypt as recipient, status should update
        assert self.page.get_by_text("PROCESSED").first.is_visible(timeout=5000)

    def test_cross_user_full_flow(self):
        """A sends a message, B logs in and can decrypt it."""
        # A already sent "secret message 123" in setup
        # Navigate to login as B
        self.page.goto(self.page.url)
        self.page.wait_for_load_state("networkidle")
        login(self.page, "B", "changeme")
        self.page.wait_for_timeout(1000)
        # B sees A's message
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        frame = frames[-1]
        type_pin_in_frame(frame, "1234")
        self.page.wait_for_timeout(2000)
        frames = get_decryptor_frames(self.page)
        plain = frames[-1].locator(".msg-text.plain")
        assert plain.is_visible(timeout=5000)
        assert plain.text_content() == "secret message 123"
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_decrypt.py -v --headed
```
Expected: All 5 tests pass. The `test_message_re_encrypts_after_timeout` test takes ~8s due to the 5s decrypt timer.

- [ ] **Step 3: Commit**

```bash
git add e2e/test_decrypt.py
git commit -m "test: add Playwright decryption E2E tests (PIN sequence, auto re-encrypt, status)"
```

---

### Task 6: Mobile keyboard / hidden input tests

**Files:**
- Create: `e2e/test_mobile_keyboard.py`

- [ ] **Step 1: Write mobile keyboard tests**

These tests verify the mobile-specific fix: clicking a message focuses a hidden input, and typing into it triggers decryption.

```python
import pytest
from e2e.helpers import login, send_command, get_decryptor_frames


class TestMobileKeyboard:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")
        send_command(self.page, "mobile test message")
        self.page.wait_for_timeout(1000)

    def test_hidden_input_exists_in_encrypted_message(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        hidden_input = frame.locator(".hidden-input")
        assert hidden_input.count() == 1

    def test_hidden_input_has_numeric_inputmode(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        hidden_input = frame.locator(".hidden-input")
        assert hidden_input.get_attribute("inputmode") == "numeric"

    def test_click_message_focuses_hidden_input(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        container = frame.locator(".msg-container")
        container.click()
        self.page.wait_for_timeout(500)
        # After click, the container should have "selected" class
        classes = container.get_attribute("class") or ""
        assert "selected" in classes

    def test_message_selected_styling_on_click(self):
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        container = frame.locator(".msg-container")
        container.click()
        self.page.wait_for_timeout(300)
        classes = container.get_attribute("class") or ""
        assert "selected" in classes
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_mobile_keyboard.py -v
```
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add e2e/test_mobile_keyboard.py
git commit -m "test: add Playwright mobile keyboard/hidden input E2E tests"
```

---

### Task 7: Sidebar tests

**Files:**
- Create: `e2e/test_sidebar.py`

- [ ] **Step 1: Write sidebar tests**

The sidebar is hidden by default via CSS. It's revealed by typing the PIN "1234" into the title input. Tests must interact with the title input inside its iframe.

```python
import pytest
from e2e.helpers import login, get_title_frame


class TestSidebar:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")

    def test_sidebar_hidden_by_default(self):
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        # Sidebar element exists but is hidden via CSS display:none
        assert not sidebar.is_visible()

    def test_pin_on_title_reveals_sidebar(self):
        title_frame = get_title_frame(self.page)
        title_input = title_frame.locator(".title-input")
        title_input.click()
        self.page.wait_for_timeout(300)
        # Type PIN sequence "1234"
        for char in "1234":
            title_input.press(char)
        self.page.wait_for_timeout(500)
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        assert sidebar.is_visible()

    def test_pin_toggles_sidebar(self):
        title_frame = get_title_frame(self.page)
        title_input = title_frame.locator(".title-input")
        title_input.click()
        # First PIN → reveal
        for char in "1234":
            title_input.press(char)
        self.page.wait_for_timeout(500)
        assert self.page.locator('[data-testid="stSidebar"]').is_visible()
        # Second PIN → hide
        for char in "1234":
            title_input.press(char)
        self.page.wait_for_timeout(500)
        assert not self.page.locator('[data-testid="stSidebar"]').is_visible()

    def test_title_input_shows_primed_on_focus(self):
        title_frame = get_title_frame(self.page)
        title_input = title_frame.locator(".title-input")
        title_input.click()
        self.page.wait_for_timeout(300)
        classes = title_input.get_attribute("class") or ""
        assert "primed" in classes
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_sidebar.py -v --headed
```
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add e2e/test_sidebar.py
git commit -m "test: add Playwright sidebar reveal/toggle E2E tests"
```

---

### Task 8: Clear chat tests

**Files:**
- Create: `e2e/test_clear_chat.py`

- [ ] **Step 1: Write clear chat tests**

```python
import pytest
from e2e.helpers import login, send_command, get_decryptor_frames, clear_chat


class TestClearChat:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")

    def test_clear_removes_all_messages(self):
        send_command(self.page, "msg1")
        send_command(self.page, "msg2")
        self.page.wait_for_timeout(500)
        frames_before = get_decryptor_frames(self.page)
        assert len(frames_before) >= 2
        clear_chat(self.page)
        self.page.wait_for_timeout(1000)
        assert self.page.get_by_text("No commands yet").is_visible()

    def test_empty_chat_shows_info(self):
        clear_chat(self.page)
        self.page.wait_for_timeout(1000)
        assert self.page.get_by_text("No commands yet").is_visible()
```

- [ ] **Step 2: Run tests**

Run:
```bash
python3 -m pytest e2e/test_clear_chat.py -v
```
Expected: All 2 tests pass

- [ ] **Step 3: Commit**

```bash
git add e2e/test_clear_chat.py
git commit -m "test: add Playwright clear chat E2E tests"
```

---

### Task 9: Run full suite and finalize

- [ ] **Step 1: Run entire E2E suite**

Run:
```bash
python3 -m pytest e2e/ -v
```
Expected: All tests pass (approximately 24 tests total)

- [ ] **Step 2: Run with headless and check timing**

Run:
```bash
python3 -m pytest e2e/ -v --timeout=60
```
Expected: Full suite completes in under 120 seconds

- [ ] **Step 3: Final commit**

```bash
git add -A e2e/
git commit -m "test: complete Playwright E2E test suite for Command app"
```
