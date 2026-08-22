# nite-pebbles/tests/test_moderation_logs_discord.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
import discord
from moderation_logs.entry import ModerationLogs
from moderation_logs.ui import LoggingFlags, PRESETS, LoggingConfigView, PresetModal
from moderation_logs.handlers.base import send_log_message
from moderation_logs.handlers import messages, members, channels, guild, everything
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
    MockMessageReference,
    MockAttachment,
    MockAuditLogEntry,
    MockWebhook,
)


class TestModerationLogsDiscord:
    @pytest.fixture
    def logs_cog(self, mock_bot):
        cog = ModerationLogs(mock_bot)
        return cog

    @pytest.mark.asyncio
    async def test_send_log_message_disabled(self, mock_bot, mock_guild, mock_server_settings):
        # Disabled
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": False,
            "logging_channel": str(mock_guild.general_channel.id)
        })

        await send_log_message(mock_bot, mock_guild.id, "message_delete", "Deleted a message")
        # No webhook created
        assert len(mock_guild.general_channel._webhooks) == 0

    @pytest.mark.asyncio
    async def test_send_log_message_success(self, mock_bot, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": True,
            "logging_channel": str(mock_guild.general_channel.id)
        })

        # Pre-create webhook
        wh = await mock_guild.general_channel.create_webhook(name="Mod-Logs")
        wh.user = mock_bot.user

        fake_emojis = '{"message_delete": "🗑️", "moderation_png": "icon.png"}'
        with patch("builtins.open", mock_open(read_data=fake_emojis)):
            await send_log_message(
                mock_bot, mock_guild.id, "message_delete", "Test log content",
                accessory_img="https://example.com/avatar.png",
                action_by=mock_guild.owner
            )

        assert len(wh.sent_messages) == 1
        msg_payload = wh.sent_messages[0]
        assert msg_payload["username"] == "Nite Mod-Logs"
        assert msg_payload["view"] is not None

    @pytest.mark.asyncio
    async def test_messages_handler_delete_and_edit(self, mock_bot, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": True,
            "logging_channel": str(mock_guild.general_channel.id),
            "logging_flags_bitfield": LoggingFlags.MESSAGE_DELETE.value | LoggingFlags.MESSAGE_EDIT.value
        })
        wh = await mock_guild.general_channel.create_webhook(name="Mod-Logs")
        wh.user = mock_bot.user

        author = MockMember(id=4001, name="Chatter", guild=mock_guild)
        mock_guild.members.append(author)
        msg = MockMessage(id=8001, content="Hello World", author=author, channel=mock_guild.general_channel, guild=mock_guild)

        fake_emojis = '{"message_delete": "🗑️", "message_edit": "✏️"}'
        with patch("builtins.open", mock_open(read_data=fake_emojis)):
            # Message Delete
            await messages.handle_message_delete(mock_bot, msg)
            assert len(wh.sent_messages) == 1

            # Message Edit
            before_msg = MockMessage(id=8001, content="Hello World", author=author, channel=mock_guild.general_channel, guild=mock_guild)
            after_msg = MockMessage(id=8001, content="Hello Edited", author=author, channel=mock_guild.general_channel, guild=mock_guild)
            await messages.handle_message_edit(mock_bot, before_msg, after_msg)
            assert len(wh.sent_messages) == 2

    @pytest.mark.asyncio
    async def test_members_handler_join_and_ban(self, mock_bot, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": True,
            "logging_channel": str(mock_guild.general_channel.id),
            "logging_flags_bitfield": LoggingFlags.MEMBER_JOIN.value | LoggingFlags.MEMBER_BAN_UNBAN.value
        })
        wh = await mock_guild.general_channel.create_webhook(name="Mod-Logs")
        wh.user = mock_bot.user

        new_member = MockMember(id=5001, name="Newcomer", guild=mock_guild)
        mock_guild.members.append(new_member)

        fake_emojis = '{"member_join": "📥", "member_ban": "🔨"}'
        with patch("builtins.open", mock_open(read_data=fake_emojis)):
            # Member Join
            await members.handle_member_join(mock_bot, new_member)
            assert len(wh.sent_messages) == 1

            # Member Ban
            await members.handle_member_ban(mock_bot, mock_guild, new_member)
            assert len(wh.sent_messages) == 2

    @pytest.mark.asyncio
    async def test_channels_and_guild_handlers(self, mock_bot, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": True,
            "logging_channel": str(mock_guild.general_channel.id),
            "logging_flags_bitfield": LoggingFlags.CHANNEL_CREATE.value | LoggingFlags.ROLE_CREATE.value
        })
        wh = await mock_guild.general_channel.create_webhook(name="Mod-Logs")
        wh.user = mock_bot.user

        fake_emojis = '{"channel_create": "📁", "role_create": "🏷️"}'
        with patch("builtins.open", mock_open(read_data=fake_emojis)):
            # Channel Create
            new_ch = MockTextChannel(id=9001, name="new-channel", guild=mock_guild)
            await channels.handle_channel_create(mock_bot, new_ch)
            assert len(wh.sent_messages) == 1

            # Role Create
            new_role = MockRole(id=9002, name="NewRole", guild=mock_guild)
            await guild.handle_role_create(mock_bot, new_role)
            assert len(wh.sent_messages) == 2

    @pytest.mark.asyncio
    async def test_everything_voice_state_update(self, mock_bot, mock_guild, mock_server_settings):
        await mock_server_settings.update_settings(mock_guild.id, {
            "logging_enabled": True,
            "logging_channel": str(mock_guild.general_channel.id),
            "logging_flags_bitfield": LoggingFlags.VOICE_JOIN.value
        })
        wh = await mock_guild.general_channel.create_webhook(name="Mod-Logs")
        wh.user = mock_bot.user

        member = MockMember(id=6001, name="VoiceUser", guild=mock_guild)
        mock_guild.members.append(member)

        v1 = mock_guild.voice_channel
        before_state = MagicMock(channel=None)
        after_state = MagicMock(channel=v1, self_mute=False, self_deaf=False, self_stream=False, self_video=False)

        fake_emojis = '{"voice_join": "🔊"}'
        with patch("builtins.open", mock_open(read_data=fake_emojis)):
            # Voice Join
            await everything.handle_voice_state_update(mock_bot, member, before_state, after_state, {})
            assert len(wh.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_logging_config_view(self, logs_cog, mock_guild, mock_server_settings):
        view = LoggingConfigView(logs_cog, mock_guild, mock_guild.owner)
        await view.build()
        assert len(view.children) > 0

        # Test Page Navigation
        view.page = 2
        await view.build()
        assert view.page == 2
        assert len(view.children) > 0

    @pytest.mark.asyncio
    async def test_apply_presets_via_modal(self, logs_cog, mock_guild, mock_server_settings):
        view = LoggingConfigView(logs_cog, mock_guild, mock_guild.owner)
        await view.build()

        modal = PresetModal(view, "en")
        modal.select._values = ["essential"]

        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)
        await modal.on_submit(inter)

        settings = await mock_server_settings.get_settings(mock_guild.id)
        saved_flags = settings.get("logging_flags_bitfield", 0)
        assert saved_flags == PRESETS["essential"].value


