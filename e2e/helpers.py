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
    so we find all iframes and identify decryptor frames by checking
    for .msg-container inside.
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
