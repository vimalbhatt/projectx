"""Tests for the chat_decryptor component's frontend HTML/JS logic."""

import pytest


@pytest.fixture()
def html_content():
    with open("components/chat_decryptor/frontend/index.html") as f:
        return f.read()


class TestComponentHtml:
    def test_hidden_input_present(self, html_content):
        """Each encrypted message should have a hidden input for mobile keyboard."""
        assert 'class="hidden-input"' in html_content

    def test_hidden_input_has_numeric_inputmode(self, html_content):
        """Hidden input should trigger numeric keyboard on mobile."""
        assert 'inputmode="numeric"' in html_content

    def test_hidden_input_disables_autocorrect(self, html_content):
        assert 'autocorrect="off"' in html_content
        assert 'autocapitalize="off"' in html_content
        assert 'spellcheck="false"' in html_content

    def test_click_focuses_hidden_input(self, html_content):
        """Clicking the message container should focus the hidden input."""
        assert "kinput.focus()" in html_content

    def test_sequence_mode_key_buffer(self, html_content):
        """JS should buffer keys for sequence matching."""
        assert "keyBuffer" in html_content

    def test_sequence_mode_detection(self, html_content):
        """Sequence mode activates when no modifiers and key length > 1."""
        assert "combo.key.length > 1" in html_content

    def test_buffer_timeout_resets(self, html_content):
        """Key buffer should reset after timeout to prevent stale input."""
        assert "keyBufferTimeout" in html_content
        assert "3000" in html_content  # 3 second timeout

    def test_modifier_mode_still_supported(self, html_content):
        """Single key + modifier combo should still work."""
        assert "combo.ctrl" in html_content
        assert "combo.shift" in html_content
        assert "combo.alt" in html_content

    def test_decrypt_duration(self, html_content):
        assert "DECRYPT_DURATION = 5000" in html_content

    def test_re_encrypt_on_timeout(self, html_content):
        assert '"re_encrypt"' in html_content

    def test_re_encrypt_on_blur(self, html_content):
        assert "focusout" in html_content

    def test_user_color_coding(self, html_content):
        assert "#1a1a2e" in html_content  # User A
        assert "#2e1a2e" in html_content  # User B
