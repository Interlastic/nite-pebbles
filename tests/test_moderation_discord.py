# nite-pebbles/tests/test_moderation_discord.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import discord
from moderation import (
    Moderation,
    ModerationSuccessView,
    ModerationErrorView,
    ModerationSettingsView,
    FuzzyUserSelect,
)
from discord_mocks import (
    MockBot,
    MockGuild,
    MockUser,
    MockMember,
    MockRole,
    MockInteraction,
    MockTextChannel,
    MockMessage,
    MockMessageReference,
)


class TestModerationDiscord:
    @pytest.fixture
    def mod_cog(self, mock_bot):
        cog = Moderation(mock_bot)
        return cog

    @pytest.mark.asyncio
    async def test_check_hierarchy_cannot_mod_self(self, mod_cog, mock_guild):
        mod = mock_guild.owner
        inter = MockInteraction(user=mod, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, mod, "ban")
        assert not ok
        assert "yourself" in res

    @pytest.mark.asyncio
    async def test_check_hierarchy_cannot_mod_bot(self, mod_cog, mock_guild):
        mod = mock_guild.owner
        inter = MockInteraction(user=mod, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, mock_guild.me, "ban")
        assert not ok
        assert "myself" in res

    @pytest.mark.asyncio
    async def test_check_hierarchy_cannot_mod_owner(self, mod_cog, mock_guild):
        # A moderator trying to moderate the guild owner
        mod = MockMember(id=5555, name="Mod", guild=mock_guild, roles=[mock_guild.mod_role])
        inter = MockInteraction(user=mod, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, mock_guild.owner, "ban")
        assert not ok
        assert "server owner" in res

    @pytest.mark.asyncio
    async def test_check_hierarchy_role_too_low(self, mod_cog, mock_guild):
        # Mod has mod_role (pos 5), target has admin_role (pos 10)
        mod = MockMember(id=5555, name="Mod", guild=mock_guild, roles=[mock_guild.mod_role])
        target = MockMember(id=6666, name="AdminUser", guild=mock_guild, roles=[mock_guild.admin_role])
        inter = MockInteraction(user=mod, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, target, "ban")
        assert not ok
        assert "highest role" in res

    @pytest.mark.asyncio
    async def test_check_hierarchy_bot_role_too_low(self, mod_cog, mock_guild):
        # Mod is owner (pos max), target has super_admin (pos 20), bot has admin (pos 10)
        super_admin = MockRole(id=9999, name="SuperAdmin", guild=mock_guild, position=20)
        target = MockMember(id=7777, name="SuperUser", guild=mock_guild, roles=[super_admin])
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, target, "ban")
        assert not ok
        assert "higher than mine" in res

    @pytest.mark.asyncio
    async def test_check_hierarchy_valid(self, mod_cog, mock_guild):
        mod = mock_guild.owner
        target = MockMember(id=8888, name="RegularMember", guild=mock_guild, roles=[mock_guild.default_role])
        inter = MockInteraction(user=mod, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, target, "ban")
        assert ok
        assert res is None

    @pytest.mark.asyncio
    async def test_check_hierarchy_from_user_id_string(self, mod_cog, mock_guild):
        target = MockMember(id=123456789012345678, name="RegularMember", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)
        ok, res = await mod_cog.check_hierarchy(inter, "123456789012345678", "ban")
        assert ok
        assert res is None

    @pytest.mark.asyncio
    async def test_moderation_settings(self, mod_cog, mock_guild):
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)
        await mod_cog.moderation_settings.callback(mod_cog, inter)
        assert len(inter.sent_responses) == 1
        view = inter.sent_responses[0]["view"]
        assert isinstance(view, ModerationSettingsView)

    @pytest.mark.asyncio
    async def test_ban_command_success(self, mod_cog, mock_guild):
        target = MockMember(id=2002, name="BadActor", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        await mod_cog.ban.callback(mod_cog, inter, user=target, reason="Spamming")
        assert any(b.user.id == target.id for b in mock_guild.banned_users)
        assert len(inter.sent_followups) == 1
        view = inter.sent_followups[0]["view"]
        assert isinstance(view, ModerationSuccessView)

    @pytest.mark.asyncio
    async def test_softban_command(self, mod_cog, mock_guild):
        target = MockMember(id=2003, name="Troll", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        await mod_cog.softban.callback(mod_cog, inter, user=target, reason="Clearing messages")
        # Softban bans and instantly unbans
        assert not any(b.user.id == target.id for b in mock_guild.banned_users)
        assert len(inter.sent_followups) == 1
        view = inter.sent_followups[0]["view"]
        assert isinstance(view, ModerationSuccessView)

    @pytest.mark.asyncio
    async def test_kick_command(self, mod_cog, mock_guild):
        target = MockMember(id=2004, name="RuleBreaker", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        await mod_cog.kick.callback(mod_cog, inter, user=target, reason="Breaking rules")
        assert target not in mock_guild.members
        assert len(inter.sent_followups) == 1
        view = inter.sent_followups[0]["view"]
        assert isinstance(view, ModerationSuccessView)

    @pytest.mark.asyncio
    async def test_timeout_and_untimeout(self, mod_cog, mock_guild):
        target = MockMember(id=2005, name="LoudUser", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        # Timeout 600 seconds
        await mod_cog.timeout.callback(mod_cog, inter, user=target, duration=600, reason="Mute")
        assert target.timed_out_until is not None
        assert len(inter.sent_followups) == 1

        # Untimeout
        inter.sent_followups.clear()
        await mod_cog.untimeout.callback(mod_cog, inter, user=target, reason="Apologized")
        assert target.timed_out_until is None
        assert len(inter.sent_followups) == 1

    @pytest.mark.asyncio
    async def test_unban_command(self, mod_cog, mock_guild):
        banned_user = MockUser(id=2006, name="BannedGuy")
        await mock_guild.ban(banned_user, reason="Prior ban")
        inter = MockInteraction(user=mock_guild.owner, guild=mock_guild)

        await mod_cog.unban.callback(mod_cog, inter, username=str(banned_user.id), reason="Pardoned")
        assert not any(b.user.id == banned_user.id for b in mock_guild.banned_users)
        assert len(inter.sent_followups) == 1

    @pytest.mark.asyncio
    async def test_unban_autocomplete(self, mod_cog, mock_guild):
        banned1 = MockUser(id=3001, name="SpammerOne")
        banned2 = MockUser(id=3002, name="TrollTwo")
        await mock_guild.ban(banned1)
        await mock_guild.ban(banned2)

        inter = MockInteraction(guild=mock_guild)
        choices = await mod_cog.unban_autocomplete(inter, current="spam")
        assert isinstance(choices, list)
        assert any("SpammerOne" in c.name for c in choices)

    @pytest.mark.asyncio
    async def test_on_message_prefix_command(self, mod_cog, mock_guild):
        target = MockMember(id=2007, name="ChatOffender", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)

        msg = MockMessage(
            id=4001,
            content=f",ban {target.mention} Spamming channels",
            author=mock_guild.owner,
            guild=mock_guild,
            channel=mock_guild.general_channel
        )

        await mod_cog.on_message(msg)
        assert any(b.user.id == target.id for b in mock_guild.banned_users)
        assert len(mock_guild.general_channel.sent_messages) > 0

    @pytest.mark.asyncio
    async def test_on_message_reply_context(self, mod_cog, mock_guild):
        target = MockMember(id=2008, name="RepliedUser", guild=mock_guild, roles=[mock_guild.default_role])
        mock_guild.members.append(target)

        orig_msg = MockMessage(id=5001, content="Bad message", author=target, guild=mock_guild, channel=mock_guild.general_channel)
        ref = MockMessageReference(message=orig_msg)

        kick_msg = MockMessage(
            id=5002,
            content=",kk Inappropriate behavior",
            author=mock_guild.owner,
            guild=mock_guild,
            channel=mock_guild.general_channel,
            reference=ref
        )

        await mod_cog.on_message(kick_msg)
        assert target not in mock_guild.members

    @pytest.mark.asyncio
    async def test_moderation_success_and_error_views(self, mod_cog, mock_guild):
        target = MockMember(id=2009, name="ViewTarget", guild=mock_guild)
        mock_guild.members.append(target)

        success_view = ModerationSuccessView(
            mod_cog, "🔨", "banned", target, "Test reason", mock_guild.owner,
            attempt=1, button_label="Unban", button_emoji="↩️", lang="en"
        )
        assert success_view is not None

        error_view = ModerationErrorView(
            mod_cog, "❌", "kick", target, "Hierarchy error", mock_guild.owner,
            attempt=1, reason="Test", lang="en"
        )
        assert error_view is not None


