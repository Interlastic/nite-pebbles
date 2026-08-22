# nite-pebbles/tests/test_locales_mock.py
import pytest
import discord
from locales import (
    get_string,
    get_list,
    resolve_locale,
    get_localized,
    clear_cache,
    load_pebble_language,
    DEFAULT_LANGUAGE,
)
from discord_mocks import MockInteraction, MockGuild, MockUser, MockMember, MockMessage


class TestLocalesMock:
    def test_get_string_basic_english(self):
        # games.rps.tie in en.json
        text = get_string("games.rps.tie", "en")
        assert text == "🤝 **It's a tie!**"

    def test_get_string_with_interpolation(self):
        # games.rps.winner in en.json -> "🎉 **{user} wins!**"
        text = get_string("games.rps.winner", "en", user="Alice")
        assert text == "🎉 **Alice wins!**"

    def test_get_string_german(self):
        text_de = get_string("games.rps.tie", "de")
        assert "Unentschieden" in text_de

    def test_get_string_polish(self):
        text_pl = get_string("games.rps.tie", "pl")
        assert "Remis" in text_pl

    def test_get_string_fallback_to_english_on_missing_lang(self):
        # Non-supported language defaults to english
        text = get_string("games.rps.tie", "fr")
        assert text == "🤝 **It's a tie!**"


    def test_get_string_missing_key_returns_bracketed(self):
        text = get_string("totally.fake.and.nonexistent.key", "en")
        assert text == "[totally.fake.and.nonexistent.key]"

    def test_get_list(self):
        eightball_responses = get_list("games.eightball.responses", "en")
        assert isinstance(eightball_responses, list)
        assert len(eightball_responses) > 0
        assert any("Yes" in r for r in eightball_responses)

    def test_get_list_missing_returns_empty_list(self):
        assert get_list("nonexistent.list.key", "en") == []

    @pytest.mark.asyncio
    async def test_resolve_locale_user_override(self, mock_db):
        user = MockUser(id=12345)
        # Set user override in DB
        await mock_db.save_user_info(user.id, "language_override", "de")

        inter = MockInteraction(user=user, locale=discord.Locale.american_english)
        resolved = await resolve_locale(inter)
        assert resolved == "de"

    @pytest.mark.asyncio
    async def test_resolve_locale_discord_locale(self):
        user = MockUser(id=54321)
        inter = MockInteraction(user=user, locale=discord.Locale.german)
        resolved = await resolve_locale(inter)
        assert resolved == "de"

    @pytest.mark.asyncio
    async def test_resolve_locale_guild_setting(self, mock_server_settings, mock_guild):
        await mock_server_settings.update_settings(mock_guild.id, {"language": "pl"})
        user = MockUser(id=99999)
        inter = MockInteraction(user=user, guild=mock_guild, locale=None)
        resolved = await resolve_locale(inter)
        assert resolved == "pl"

    @pytest.mark.asyncio
    async def test_resolve_locale_default_fallback(self):
        user = MockUser(id=88888)
        inter = MockInteraction(user=user, locale=None)
        resolved = await resolve_locale(inter)
        assert resolved == "en"

    @pytest.mark.asyncio
    async def test_get_localized_convenience(self):
        user = MockUser(id=77777)
        inter = MockInteraction(user=user, locale=discord.Locale.american_english)
        localized = await get_localized(inter, "games.rps.winner", user="Bob")
        assert localized == "🎉 **Bob wins!**"


    def test_clear_cache(self):
        data1 = load_pebble_language("en")
        assert data1 is not None
        clear_cache()
        data2 = load_pebble_language("en")
        assert data2 == data1
