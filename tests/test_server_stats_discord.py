# nite-pebbles/tests/test_server_stats_discord.py
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from server_stats import ServerStats
from server_stats_ui import (
    ServerStatsView,
    ServerStatsButton,
    ChannelCreationWizard,
    ChannelTypeCategoryWizard,
    NewChannelTemplateModal,
    ChannelTemplateModal,
    ChannelEditWizard,
    RemoveConfirmView,
)
from discord_mocks import (
    MockBot,
    MockGuild,
    MockUser,
    MockMember,
    MockRole,
    MockTextChannel,
    MockVoiceChannel,
    MockCategoryChannel,
    MockInteraction,
    MockMessage,
    MockAuditLogEntry,
)


class TestServerStatsDiscord:
    @pytest.fixture
    def stats_cog(self, mock_bot):
        cog = ServerStats(mock_bot)
        return cog

    @pytest.mark.asyncio
    async def test_update_stats_disabled(self, stats_cog, mock_guild, mock_server_settings):
        # Settings disabled
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": False,
                "server_name_template": "Server {members}"
            }
        })
        orig_name = mock_guild.name

        await stats_cog.update_stats()
        assert mock_guild.name == orig_name

    @pytest.mark.asyncio
    async def test_update_stats_enabled_renames_guild(self, stats_cog, mock_guild, mock_server_settings):
        mock_guild.member_count = 500
        mock_guild.approximate_member_count = 500
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "server_name_template": "Awesome Guild ({members})"
            }
        })

        await stats_cog.update_stats()
        assert mock_guild.name == "Awesome Guild (500)"

    @pytest.mark.asyncio
    async def test_update_stats_throttles_guild_rename(self, stats_cog, mock_guild, mock_server_settings):
        mock_guild.member_count = 500
        mock_guild.approximate_member_count = 500
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "server_name_template": "Guild ({members})"
            }
        })

        # Run twice to fill the 2/hour throttle
        await stats_cog.update_stats()
        assert mock_guild.name == "Guild (500)"

        mock_guild.name = "Guild (500)"
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "server_name_template": "Guild 2 ({members})"
            }
        })
        await stats_cog.update_stats()
        assert mock_guild.name == "Guild 2 (500)"

        # Third rename within an hour should be throttled
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "server_name_template": "Guild 3 ({members})"
            }
        })
        await stats_cog.update_stats()
        # Still Guild 2 (500) because throttled
        assert mock_guild.name == "Guild 2 (500)"

    @pytest.mark.asyncio
    async def test_update_stats_channels_and_category(self, stats_cog, mock_guild, mock_server_settings):
        v_chan = mock_guild.voice_channel
        cat_chan = mock_guild.stats_category
        mock_guild.member_count = 100
        mock_guild.approximate_member_count = 100

        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "stat_channels": {
                    str(v_chan.id): "👥 Members: {members}",
                    str(cat_chan.id): "📊 STATS ({members})"
                }
            }
        })

        await stats_cog.update_stats()
        assert cat_chan.name == "📊 STATS (100)"
        assert v_chan.name == "👥 Members: 100"

    @pytest.mark.asyncio
    async def test_on_guild_update_conflict_detection(self, stats_cog, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "server_stats": {
                "enabled": True,
                "server_name_template": "Stats Guild"
            }
        })

        # Non-bot user renamed the guild manually
        human_user = MockUser(id=7777, name="HumanAdmin", bot=False)
        mock_guild.audit_log_entries.append(
            MockAuditLogEntry(
                action=discord.AuditLogAction.guild_update,
                user=human_user,
                target=mock_guild
            )
        )

        before_guild = MockGuild(id=mock_guild.id, name="Stats Guild")
        after_guild = MockGuild(id=mock_guild.id, name="Manual Name")
        after_guild.channels = mock_guild.channels
        after_guild.owner = mock_guild.owner
        after_guild.me = mock_guild.me
        after_guild.audit_log_entries = mock_guild.audit_log_entries

        await stats_cog.on_guild_update(before_guild, after_guild)
        # Conflict sent to human user who made the edit
        assert len(human_user.sent_messages) > 0

    @pytest.mark.asyncio
    async def test_server_stats_button_opens_view(self, stats_cog, mock_guild, mock_server_settings):
        btn = ServerStatsButton(stats_cog.bot, mock_server_settings, lang="en")
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)
        await btn.callback(inter)
        assert len(inter.sent_followups) == 1
        view = inter.sent_followups[0]["view"]
        assert isinstance(view, ServerStatsView)

    @pytest.mark.asyncio
    async def test_server_stats_view_toggle(self, stats_cog, mock_guild, mock_server_settings):
        view = ServerStatsView(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner)
        await view.build()
        assert len(view.children) > 0

    @pytest.mark.asyncio
    async def test_server_stats_wizards_and_modals(self, stats_cog, mock_guild, mock_server_settings):
        root_view = ServerStatsView(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner)
        await root_view.build()

        # ChannelCreationWizard
        wiz = ChannelCreationWizard(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner, "en", root_view)
        await wiz.build()
        assert wiz is not None

        # Type/Category Wizard
        type_wiz = ChannelTypeCategoryWizard(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner, "en", root_view)
        await type_wiz.build()
        assert type_wiz is not None

        # NewChannelTemplateModal submit
        modal = NewChannelTemplateModal(mock_server_settings, mock_guild.id, "en", root_view, discord.ChannelType.voice, mock_guild.stats_category.id, "SERVER STATS")
        modal.template_input._value = "👥 {members}"
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        # Mock interaction.response.edit_message
        await modal.on_submit(inter)
        settings = await mock_server_settings.get_settings(mock_guild.id)
        stat_channels = settings.get("server_stats", {}).get("stat_channels", {})
        assert len(stat_channels) > 0

        # ChannelEditWizard and RemoveConfirmView
        chan_id = list(stat_channels.keys())[0]
        channel_item = {"id": chan_id, "template": stat_channels[chan_id], "type": "stat"}
        edit_wiz = ChannelEditWizard(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner, "en", root_view, channel_item)
        await edit_wiz.build()
        assert edit_wiz is not None


        remove_confirm = RemoveConfirmView(stats_cog.bot, mock_server_settings, mock_guild, mock_guild.owner, "en", root_view, channel_item)
        await remove_confirm.build()
        assert remove_confirm is not None
        await remove_confirm._remove_from_settings()

        settings_after = await mock_server_settings.get_settings(mock_guild.id)
        assert chan_id not in settings_after.get("server_stats", {}).get("stat_channels", {})



