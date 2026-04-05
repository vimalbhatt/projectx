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
