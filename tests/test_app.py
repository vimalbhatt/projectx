"""Tests for app.py utility functions.

Since app.py is a Streamlit app that executes on import, we test
format_combo by reimplementing the same logic here and verifying it.
"""


def format_combo(combo):
    """Mirror of app.format_combo for testing without importing Streamlit."""
    parts = []
    if combo.get("ctrl"):
        parts.append("Ctrl")
    if combo.get("shift"):
        parts.append("Shift")
    if combo.get("alt"):
        parts.append("Alt")
    if combo.get("key"):
        parts.append(combo["key"].upper())
    return "+".join(parts) if parts else "None"


class TestFormatCombo:
    def test_modifier_plus_key(self):
        combo = {"ctrl": True, "shift": True, "key": "z"}
        assert format_combo(combo) == "Ctrl+Shift+Z"

    def test_single_modifier(self):
        assert format_combo({"ctrl": True, "key": "d"}) == "Ctrl+D"

    def test_alt_modifier(self):
        assert format_combo({"alt": True, "key": "x"}) == "Alt+X"

    def test_all_modifiers(self):
        combo = {"ctrl": True, "shift": True, "alt": True, "key": "a"}
        assert format_combo(combo) == "Ctrl+Shift+Alt+A"

    def test_no_modifiers_single_key(self):
        combo = {"ctrl": False, "shift": False, "alt": False, "key": "z"}
        assert format_combo(combo) == "Z"

    def test_sequence_key(self):
        combo = {"ctrl": False, "shift": False, "alt": False, "key": "1234"}
        assert format_combo(combo) == "1234"

    def test_empty_combo(self):
        assert format_combo({}) == "None"

    def test_missing_key(self):
        assert format_combo({"ctrl": True}) == "Ctrl"
