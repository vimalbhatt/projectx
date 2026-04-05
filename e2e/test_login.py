import pytest
from e2e.helpers import login


class TestLogin:
    def test_login_page_shows_title(self, app_page):
        title = app_page.get_by_role("heading", name="Command")
        title.wait_for(state="visible", timeout=10000)
        assert title.is_visible()

    def test_login_page_shows_user_buttons(self, app_page):
        assert app_page.get_by_role("button", name="A", exact=True).is_visible()
        assert app_page.get_by_role("button", name="B", exact=True).is_visible()

    def test_login_with_valid_key(self, app_page):
        login(app_page, "A", "changeme")
        # After login, the title-input iframe should contain "You are A"
        frame = app_page.frame_locator("iframe").first
        frame.get_by_text("You are A").wait_for(state="visible", timeout=10000)
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
        frame.get_by_text("You are B").wait_for(state="visible", timeout=10000)
        assert frame.get_by_text("You are B").is_visible()
