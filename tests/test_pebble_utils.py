# nite-pebbles/tests/test_pebble_utils.py
import pytest
from pebble_utils import (
    make_loading_bar,
    format_number,
    render_template,
    EMOJIS_NORMAL,
    EMOJIS_END_GREEN,
    EMOJIS_END_RED,
    EMOJIS_END_BOTH,
)
from discord_mocks import MockGuild


class TestMakeLoadingBar:
    def test_single_segment_bar(self):
        # size = 1 tests
        bar_0 = make_loading_bar(0, size=1)
        assert bar_0 == EMOJIS_END_BOTH[30]

        bar_100 = make_loading_bar(10, size=1)
        assert bar_100 == EMOJIS_END_BOTH[1]

        bar_50 = make_loading_bar(5, size=1)
        assert bar_50 in EMOJIS_END_BOTH.values()

    def test_multi_segment_zero_percent(self):
        # 0% on size=10: left end green 30, 8 normal 30, right end red 30
        bar = make_loading_bar(0, size=10)
        assert bar.startswith(EMOJIS_END_GREEN[30])
        assert bar.endswith(EMOJIS_END_RED[30])
        assert bar.count(EMOJIS_NORMAL[30]) == 8

    def test_multi_segment_hundred_percent(self):
        # 100% on size=10: left end green 1, 8 normal 1, right end red 1
        bar = make_loading_bar(100, size=10)
        assert bar.startswith(EMOJIS_END_GREEN[1])
        assert bar.endswith(EMOJIS_END_RED[1])
        assert bar.count(EMOJIS_NORMAL[1]) == 8

    def test_multi_segment_intermediate(self):
        # 50% on size=10 (current=50)
        bar_50 = make_loading_bar(50, size=10)
        assert bar_50.startswith(EMOJIS_END_GREEN[1])
        assert bar_50.endswith(EMOJIS_END_RED[30])
        assert len(bar_50) > 0

        # 25% on size=4 (current=10 out of 40)
        bar_25 = make_loading_bar(10, size=4)
        assert bar_25.startswith(EMOJIS_END_GREEN[1])

    def test_clamping_out_of_bounds(self):
        # Negative clamped to 0
        bar_neg = make_loading_bar(-25, size=5)
        bar_zero = make_loading_bar(0, size=5)
        assert bar_neg == bar_zero

        # Over 100% clamped to max
        bar_over = make_loading_bar(150, size=10)
        bar_hundred = make_loading_bar(100, size=10)
        assert bar_over == bar_hundred


class TestFormatNumber:
    def test_small_numbers(self):
        assert format_number(0) == "0"
        assert format_number(42) == "42"
        assert format_number(999) == "999"

    def test_thousands_k(self):
        assert format_number(1000) == "1K"
        assert format_number(1500) == "1.5K"
        assert format_number(250000) == "250K"
        assert format_number(999999) == "1000K" or format_number(999999) == "999.999K"

    def test_millions_m(self):
        assert format_number(1_000_000) == "1M"
        assert format_number(2_500_000) == "2.5M"
        assert format_number(100_000_000) == "100M"

    def test_precision_raw(self):
        assert format_number(1500, precision="raw") == "1500"
        assert format_number(1_000_000, precision="raw") == "1000000"

    def test_custom_precision(self):
        assert format_number(1500, precision="1") == "1.5K"
        assert format_number(1500, precision="2") == "1.50K"
        assert format_number(1_234_567, precision="2") == "1.23M"

    def test_invalid_precision_fallback(self):
        # Non-numeric precision falls back to :g
        assert format_number(1500, precision="invalid") == "1.5K"


class TestRenderTemplate:
    def test_none_or_empty_template(self):
        guild = MockGuild(id=101, name="Test Guild")
        assert render_template(None, guild) is None
        assert render_template("", guild) is None

    def test_all_standard_variables(self):
        guild = MockGuild(id=101, name="Test Guild")
        guild.member_count = 1500
        guild.approximate_member_count = 1500
        guild.premium_tier = 2
        guild.premium_subscription_count = 7
        guild.channels = [1, 2, 3, 4]

        tmpl = "Members: {members} | Online: {online} | Channels: {channels} | Level: {boost_level} | Boosts: {boost_count}"
        rendered = render_template(tmpl, guild, online_count=45)
        assert rendered == "Members: 1.5K | Online: 45 | Channels: 4 | Level: 2 | Boosts: 7"

    def test_variable_with_precision(self):
        guild = MockGuild(id=101)
        guild.member_count = 12500
        guild.approximate_member_count = 12500

        tmpl = "{members,raw} total ({members,1})"
        rendered = render_template(tmpl, guild)
        assert rendered == "12500 total (12.5K)"

    def test_unrecognized_variables_preserved(self):
        guild = MockGuild(id=101)
        tmpl = "Welcome {unknown_var} to {members}"
        rendered = render_template(tmpl, guild)
        assert "{unknown_var}" in rendered
