import pytest
from playwright.sync_api import expect
from e2e.helpers import login, send_command, get_decryptor_frames, type_pin_in_frame


class TestDecrypt:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")
        send_command(self.page, "secret message 123")
        self.page.wait_for_timeout(1000)

    def _decrypt_last_message(self, pin="1234"):
        """Helper: type PIN in last decryptor frame, wait for rerun, return new last frame."""
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        frame = frames[-1]
        type_pin_in_frame(frame, pin)
        # Wait for Streamlit rerun (component sends decrypt_requested, Streamlit reruns)
        self.page.wait_for_timeout(3000)
        # Re-fetch frames since iframes are recreated after rerun
        frames = get_decryptor_frames(self.page)
        assert len(frames) >= 1
        return frames[-1]

    def test_pin_sequence_decrypts_message(self):
        frame = self._decrypt_last_message("1234")
        plain = frame.locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("secret message 123")

    def test_decrypted_message_has_timer_bar(self):
        frame = self._decrypt_last_message("1234")
        timer = frame.locator(".timer-bar")
        expect(timer).to_be_visible(timeout=5000)

    def test_message_re_encrypts_after_timeout(self):
        frame = self._decrypt_last_message("1234")
        expect(frame.locator(".msg-text.plain")).to_be_visible(timeout=5000)
        # Wait for 5s re-encrypt timeout + Streamlit rerun buffer
        self.page.wait_for_timeout(7000)
        frames = get_decryptor_frames(self.page)
        frame = frames[-1]
        expect(frame.locator(".msg-text.plain")).not_to_be_visible(timeout=5000)

    def test_wrong_pin_does_not_decrypt(self):
        frame = self._decrypt_last_message("9999")
        plain = frame.locator(".msg-text.plain")
        assert plain.count() == 0

    def test_status_changes_to_processed_after_decrypt(self):
        """When recipient decrypts, status changes from PENDING to PROCESSED."""
        # Navigate away and log in as B (the recipient)
        self.page.goto(self.page.url)
        self.page.wait_for_load_state("networkidle")
        login(self.page, "B", "changeme")
        self.page.wait_for_timeout(1000)
        # Decrypt as B
        frame = self._decrypt_last_message("1234")
        expect(frame.locator(".msg-text.plain")).to_be_visible(timeout=5000)
        # Status should change to PROCESSED
        expect(self.page.get_by_text("PROCESSED").first).to_be_visible(timeout=5000)

    def test_cross_user_full_flow(self):
        """A sends a message, B logs in and can decrypt it."""
        self.page.goto(self.page.url)
        self.page.wait_for_load_state("networkidle")
        login(self.page, "B", "changeme")
        self.page.wait_for_timeout(1000)
        frame = self._decrypt_last_message("1234")
        plain = frame.locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("secret message 123")
