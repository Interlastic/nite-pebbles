# nite-pebbles/tests/test_extension_lifecycle.py
import pytest
import fun_commands
import moderation
import server_stats
import moderation_logs.entry
from discord_mocks import MockBot


class TestExtensionLifecycle:
    @pytest.mark.asyncio
    async def test_fun_commands_setup(self, mock_bot):
        await fun_commands.setup(mock_bot)
        assert "FunCommands" in mock_bot.cogs
        cog = mock_bot.get_cog("FunCommands")
        assert isinstance(cog, fun_commands.FunCommands)
        assert cog.bot == mock_bot

    @pytest.mark.asyncio
    async def test_moderation_setup(self, mock_bot):
        await moderation.setup(mock_bot)
        assert "Moderation" in mock_bot.cogs
        cog = mock_bot.get_cog("Moderation")
        assert isinstance(cog, moderation.Moderation)
        assert cog.bot == mock_bot

    @pytest.mark.asyncio
    async def test_server_stats_setup_and_unload(self, mock_bot):
        import asyncio
        await server_stats.setup(mock_bot)
        assert "ServerStats" in mock_bot.cogs
        cog = mock_bot.get_cog("ServerStats")
        assert isinstance(cog, server_stats.ServerStats)

        # In discord.py, bot.add_cog automatically invokes cog_load which starts the loop
        assert cog.update_stats.is_running()

        # Test cog_unload cancels task
        cog.cog_unload()
        await asyncio.sleep(0.05)
        assert not cog.update_stats.is_running()



    @pytest.mark.asyncio
    async def test_moderation_logs_setup(self, mock_bot):
        await moderation_logs.entry.setup(mock_bot)
        assert "ModerationLogs" in mock_bot.cogs
        cog = mock_bot.get_cog("ModerationLogs")
        assert isinstance(cog, moderation_logs.entry.ModerationLogs)
        assert cog.bot == mock_bot
