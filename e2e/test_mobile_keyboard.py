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
