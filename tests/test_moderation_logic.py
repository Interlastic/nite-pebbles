# nite-pebbles/tests/test_moderation_logic.py
import pytest
from moderation import Moderation
from discord_mocks import MockBot, MockInteraction, MockUser


class TestModerationLogic:
    @pytest.fixture
    def mod_cog(self, mock_bot):
        return Moderation(mock_bot)

    def test_parse_duration_seconds(self, mod_cog):
        assert mod_cog.parse_duration("30s") == 30
        assert mod_cog.parse_duration("60") == 60  # Default unit 's'

    def test_parse_duration_minutes(self, mod_cog):
        assert mod_cog.parse_duration("5m") == 300
        assert mod_cog.parse_duration("10m") == 600

    def test_parse_duration_hours(self, mod_cog):
        assert mod_cog.parse_duration("1h") == 3600
        assert mod_cog.parse_duration("24h") == 86400

    def test_parse_duration_days_and_weeks(self, mod_cog):
        assert mod_cog.parse_duration("1d") == 86400
        assert mod_cog.parse_duration("7d") == 604800
        assert mod_cog.parse_duration("1w") == 604800
        assert mod_cog.parse_duration("2w") == 1209600

    def test_parse_duration_case_insensitive(self, mod_cog):
        assert mod_cog.parse_duration("10M") == 600
        assert mod_cog.parse_duration("2H") == 7200
        assert mod_cog.parse_duration("1W") == 604800

    def test_parse_duration_invalid(self, mod_cog):
        assert mod_cog.parse_duration(None) is None
        assert mod_cog.parse_duration("") is None
        assert mod_cog.parse_duration("abc") is None
        assert mod_cog.parse_duration("10x") is None
        assert mod_cog.parse_duration("-5m") is None

    def test_sanitize_empty_or_none(self, mod_cog):
        assert mod_cog.sanitize(None) == "No reason provided"
        assert mod_cog.sanitize("") == "No reason provided"

    def test_sanitize_newlines(self, mod_cog):
        raw = "Line 1\nLine 2\rLine 3"
        sanitized = mod_cog.sanitize(raw)
        assert "\n" not in sanitized
        assert "\r" not in sanitized
        assert "Line 1 Line 2Line 3" in sanitized

    def test_sanitize_markdown_characters(self, mod_cog):
        raw = "Hello *world* _test_ ~strike~ `code` |spoiler| \\backslash"
        sanitized = mod_cog.sanitize(raw)
        assert r"\*" in sanitized
        assert r"\_" in sanitized
        assert r"\~" in sanitized
        assert r"\`" in sanitized
        assert r"\|" in sanitized
        assert r"\\" in sanitized

    def test_get_audit_reason(self, mod_cog):
        user = MockUser(name="ModUser")
        inter = MockInteraction(user=user)

        reason = mod_cog._get_audit_reason(inter, "Spamming in general")
        assert reason == "Spamming in general | By ModUser"

    def test_get_audit_reason_fallback(self, mod_cog):
        user = MockUser(name="ModUser")
        inter = MockInteraction(user=user)

        reason = mod_cog._get_audit_reason(inter, None)
        assert reason == "No reason provided | By ModUser"

    def test_get_audit_reason_truncation(self, mod_cog):
        user = MockUser(name="ModUser")
        inter = MockInteraction(user=user)

        very_long_reason = "X" * 600
        reason = mod_cog._get_audit_reason(inter, very_long_reason)
        assert len(reason) <= 512
        assert reason.endswith("... | By ModUser")
