import pytest
from e2e.helpers import login, get_title_frame


class TestSidebar:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page
        login(self.page, "A", "changeme")

    def test_sidebar_hidden_by_default(self):
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        # Sidebar exists in DOM but is hidden via CSS display:none
        assert sidebar.count() > 0
        assert not sidebar.is_visible()

    def test_pin_on_title_reveals_sidebar(self):
        title_frame = get_title_frame(self.page)
        title_input = title_frame.locator(".title-input")
        title_input.click()
        self.page.wait_for_timeout(300)
        for char in "1234":
            title_input.press(char)
        self.page.wait_for_timeout(500)
        sidebar = self.page.locator('[data-testid="stSidebar"]')
        assert sidebar.is_visible()

    def test_pin_toggles_sidebar(self):
        title_frame = get_title_frame(self.page)
        title_input = title_frame.locator(".title-input")
        title_input.click()
        self.page.wait_for_timeout(300)
        for char in "1234":
            title_input.press(char)
        self.page.wait_for_timeout(500)
        assert self.page.locator('[data-testid="stSidebar"]').is_visible()
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
