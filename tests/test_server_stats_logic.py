# nite-pebbles/tests/test_server_stats_logic.py
import pytest
from server_stats_ui import render_template_simulated, validate_template
from discord_mocks import MockGuild


class TestServerStatsLogic:
    def test_render_template_simulated_none_or_empty(self):
        assert render_template_simulated(None) is None
        assert render_template_simulated("") is None

    def test_render_template_simulated_default_values(self):
        tmpl = "👥 {members} | 💬 {channels} | 🚀 Lvl {boost_level} ({boost_count})"
        rendered = render_template_simulated(tmpl)
        assert "1000K" in rendered or "999.999K" in rendered or "1M" in rendered
        assert "500" in rendered
        assert "Lvl 3" in rendered
        assert "99" in rendered

    def test_render_template_simulated_custom_values(self):
        tmpl = "{members} members in {channels} channels"
        rendered = render_template_simulated(tmpl, members=50, channels=5)
        assert rendered == "50 members in 5 channels"

    def test_validate_template_empty(self):
        guild = MockGuild()
        warnings, errors = validate_template("", guild)
        assert "template_empty" in errors
        assert len(warnings) == 0

        warnings, errors = validate_template("   ", guild)
        assert "template_empty" in errors

    def test_validate_template_valid(self):
        guild = MockGuild()
        warnings, errors = validate_template("👥 {members} Members", guild)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_template_too_long(self):
        guild = MockGuild()
        # Create a template that when rendered with simulated numbers exceeds 100 characters
        long_prefix = "A" * 95
        tmpl = f"{long_prefix} {{members}} {{channels}} {{boost_level}}"
        warnings, errors = validate_template(tmpl, guild)
        assert len(errors) == 0
        assert any(w[0] == "template_too_long" for w in warnings)
