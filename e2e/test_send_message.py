import pytest
from e2e.helpers import login, send_command, get_decryptor_frames, clear_chat


class TestSendMessage:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")

    def test_send_command_appears_in_chat(self):
        send_command(self.page, "hello from A")
        # Wait for Streamlit to rerun and iframe to appear
        self.page.wait_for_timeout(2000)
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        first_frame = frames[-1]
        msg_text = first_frame.locator(".msg-text").first
        assert msg_text.is_visible()
        # The displayed text should be encrypted (not plaintext)
        text_content = msg_text.text_content()
        assert text_content != "hello from A"

    def test_send_empty_command_rejected(self):
        send_command(self.page, "")
        assert self.page.get_by_text("Command cannot be empty").is_visible()

    def test_message_shows_sender_label(self):
        send_command(self.page, "test sender label")
        assert self.page.get_by_text("You").first.is_visible()

    def test_message_status_pending(self):
        send_command(self.page, "check status")
        assert self.page.get_by_text("PENDING").first.is_visible()
