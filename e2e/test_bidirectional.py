"""
Full bidirectional messaging test:
1. A sends a command to B → visible to both → both can decrypt
2. B sends a command to A → visible to both → both can decrypt
"""
import pytest
from playwright.sync_api import expect
from e2e.helpers import login, send_command, get_decryptor_frames, type_pin_in_frame


class TestBidirectionalMessaging:
    @pytest.fixture(autouse=True)
    def _setup(self, app_page):
        self.page = app_page

    def _logout_and_login(self, user, password="changeme"):
        self.page.goto(self.page.url)
        self.page.wait_for_load_state("networkidle")
        login(self.page, user, password)

    def _wait_for_frames(self, expected, retries=5):
        """Poll until expected number of decryptor frames appear."""
        for _ in range(retries):
            frames = get_decryptor_frames(self.page)
            if len(frames) >= expected:
                return frames
            self.page.get_by_role("button", name="refresh").click()
            self.page.wait_for_timeout(2000)
        return get_decryptor_frames(self.page)

    def _decrypt_at(self, index, pin="1234"):
        """Decrypt message at index, wait for rerun, return updated frames."""
        frames = get_decryptor_frames(self.page)
        assert len(frames) > index, f"Expected at least {index + 1} frames, got {len(frames)}"
        type_pin_in_frame(frames[index], pin)
        self.page.wait_for_timeout(3000)
        return get_decryptor_frames(self.page)

    def test_full_bidirectional_flow(self):
        # === A sends "Alpha to Bravo" to B ===
        login(self.page, "A", "changeme")
        send_command(self.page, "Alpha to Bravo")
        self.page.wait_for_timeout(1500)

        # A sees 1 message
        frames = self._wait_for_frames(1)
        assert len(frames) == 1

        # A can decrypt it
        frames = self._decrypt_at(0)
        plain = frames[0].locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("Alpha to Bravo")

        # Wait for re-encrypt
        self.page.wait_for_timeout(6000)

        # === B logs in, sees A's message, decrypts it ===
        self._logout_and_login("B")
        self.page.wait_for_timeout(1500)

        frames = self._wait_for_frames(1)
        assert len(frames) == 1

        # B decrypts A's message
        frames = self._decrypt_at(0)
        plain = frames[0].locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("Alpha to Bravo")

        # Status changes to PROCESSED (B is recipient)
        expect(self.page.get_by_text("PROCESSED").first).to_be_visible(timeout=5000)

        # Wait for re-encrypt
        self.page.wait_for_timeout(6000)

        # === B sends "Bravo to Alpha" to A ===
        send_command(self.page, "Bravo to Alpha")
        self.page.wait_for_timeout(2000)

        # B sees 2 messages
        frames = self._wait_for_frames(2)
        assert len(frames) == 2, f"B should see 2 messages, got {len(frames)}"

        # B can decrypt their own message
        frames = self._decrypt_at(1)
        plain = frames[1].locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("Bravo to Alpha")

        # Wait for re-encrypt
        self.page.wait_for_timeout(6000)

        # === A logs in, sees both messages, decrypts B's message ===
        self._logout_and_login("A")
        self.page.wait_for_timeout(1500)

        frames = self._wait_for_frames(2)
        assert len(frames) == 2, f"A should see 2 messages, got {len(frames)}"

        # A decrypts B's message (message index 1)
        frames = self._decrypt_at(1)
        plain = frames[1].locator(".msg-text.plain")
        expect(plain).to_be_visible(timeout=5000)
        expect(plain).to_have_text("Bravo to Alpha")
