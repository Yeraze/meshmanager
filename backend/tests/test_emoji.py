"""Tests for emoji decoding across collectors."""


class TestDecodeEmoji:
    """Tests for MeshMonitorCollector._decode_emoji()."""

    def _make_collector(self):
        """Create a MeshMonitorCollector with a mock source."""
        from unittest.mock import MagicMock

        from app.collectors.meshmonitor import MeshMonitorCollector

        source = MagicMock()
        source.id = "test-source"
        source.config = {"url": "http://test", "token": "test"}
        return MeshMonitorCollector(source)

    def test_none_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji(None) is None

    def test_int_codepoint_thumbs_up(self):
        c = self._make_collector()
        assert c._decode_emoji(128077) == "\U0001f44d"  # 👍

    def test_int_codepoint_heart(self):
        c = self._make_collector()
        assert c._decode_emoji(10084) == "\u2764"  # ❤

    def test_int_zero_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji(0) is None

    def test_int_out_of_range_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji(0x110000) is None

    def test_string_emoji_passthrough(self):
        c = self._make_collector()
        assert c._decode_emoji("\U0001f44d") == "\U0001f44d"

    def test_numeric_string_converted(self):
        c = self._make_collector()
        assert c._decode_emoji("128077") == "\U0001f44d"

    def test_empty_string_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji("") is None

    def test_control_char_0x01_returns_none(self):
        """Meshtastic sends 0x01 as a 'reaction present' flag, not a real emoji."""
        c = self._make_collector()
        assert c._decode_emoji(1) is None

    def test_control_char_string_0x01_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji("1") is None

    def test_numeric_string_below_0x20_returns_none(self):
        c = self._make_collector()
        assert c._decode_emoji("15") is None
