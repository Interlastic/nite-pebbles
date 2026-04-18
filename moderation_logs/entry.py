import discord
from discord.ext import commands
from .handlers import guild, channels, members, messages, everything
from .ui import LoggingFlags

class ModerationLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_join_times = {}

    async def _is_logged(self, guild_id, flag):
        settings = await self.bot.server_settings.get_settings(guild_id)
        if not settings.get("logging_enabled"): return False
        flags = settings.get("logging_flags_bitfield", 0)
        return bool(flags & flag)

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        await everything.handle_socket_raw(self.bot, msg)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        await guild.handle_guild_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await guild.handle_role_create(self.bot, role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await guild.handle_role_delete(self.bot, role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await guild.handle_role_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild_obj, before, after):
        await guild.handle_emoji_update(self.bot, guild_obj, before, after)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild_obj, before, after):
        await guild.handle_sticker_update(self.bot, guild_obj, before, after)

    @commands.Cog.listener()
    async def on_integration_create(self, integration):
        await guild.handle_integration_create(self.bot, integration)

    @commands.Cog.listener()
    async def on_integration_update(self, integration):
        await guild.handle_integration_update(self.bot, integration)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild_obj):
        await guild.handle_guild_integrations_update(self.bot, guild_obj)

    @commands.Cog.listener()
    async def on_raw_integration_delete(self, payload):
        await guild.handle_integration_delete(self.bot, payload)

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event):
        await guild.handle_scheduled_event_create(self.bot, event)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        await guild.handle_scheduled_event_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event):
        await guild.handle_scheduled_event_delete(self.bot, event)

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event, user):
        await guild.handle_scheduled_event_user_add(self.bot, event, user)

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event, user):
        await guild.handle_scheduled_event_user_remove(self.bot, event, user)

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule):
        await guild.handle_automod_rule_create(self.bot, rule)

    @commands.Cog.listener()
    async def on_automod_rule_update(self, before, after):
        await guild.handle_automod_rule_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule):
        await guild.handle_automod_rule_delete(self.bot, rule)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await channels.handle_channel_create(self.bot, channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await channels.handle_channel_delete(self.bot, channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        await channels.handle_channel_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        await channels.handle_webhook_update(self.bot, channel)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        await channels.handle_thread_create(self.bot, thread)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        await channels.handle_thread_delete(self.bot, thread)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        await channels.handle_thread_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_thread_member_update(self, member):
        await channels.handle_thread_member_update(self.bot, member)

    @commands.Cog.listener()
    async def on_thread_members_update(self, payload):
        await channels.handle_thread_members_update(self.bot, payload)

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage):
        await channels.handle_stage_instance_create(self.bot, stage)

    @commands.Cog.listener()
    async def on_stage_instance_update(self, before, after):
        await channels.handle_stage_instance_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage):
        await channels.handle_stage_instance_delete(self.bot, stage)

    @commands.Cog.listener()
    async def on_member_ban(self, guild_obj, user):
        await members.handle_member_ban(self.bot, guild_obj, user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild_obj, user):
        await members.handle_member_unban(self.bot, guild_obj, user)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await members.handle_member_join(self.bot, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await members.handle_member_remove(self.bot, member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        await members.handle_member_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_member_join_request(self, member):
        await members.handle_member_join_request(self.bot, member)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        await members.handle_user_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        if await self._is_logged(message.guild.id, LoggingFlags.MESSAGE_CREATE):
            await messages.handle_message_create(self.bot, message)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        await messages.handle_message_delete(self.bot, message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await messages.handle_message_edit(self.bot, before, after)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages_list):
        await messages.handle_bulk_message_delete(self.bot, messages_list)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await messages.handle_invite_create(self.bot, invite)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await messages.handle_invite_delete(self.bot, invite)

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        await messages.handle_pin_update(self.bot, channel, last_pin)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await everything.handle_voice_state_update(self.bot, member, before, after, self.voice_join_times)

    @commands.Cog.listener()
    async def on_voice_server_update(self, data):
        await everything.handle_voice_server_update(self.bot, data)

    @commands.Cog.listener()
    async def on_voice_channel_effect(self, payload):
        await everything.handle_voice_channel_effect(self.bot, payload)

    @commands.Cog.listener()
    async def on_automod_action(self, execution):
        await everything.handle_automod_action(self.bot, execution)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await everything.handle_reaction_add(self.bot, reaction, user)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        await everything.handle_reaction_remove(self.bot, reaction, user)

    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        await everything.handle_reaction_clear(self.bot, message, reactions)

    @commands.Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        await everything.handle_reaction_clear_emoji(self.bot, reaction)

    @commands.Cog.listener()
    async def on_poll_vote_add(self, user, answer):
        await everything.handle_poll_vote_add(self.bot, user, answer)

    @commands.Cog.listener()
    async def on_poll_vote_remove(self, user, answer):
        await everything.handle_poll_vote_remove(self.bot, user, answer)

    @commands.Cog.listener()
    async def on_guild_soundboard_sound_create(self, sound):
        await everything.handle_sound_create(self.bot, sound)

    @commands.Cog.listener()
    async def on_guild_soundboard_sound_update(self, before, after):
        await everything.handle_sound_update(self.bot, before, after)

    @commands.Cog.listener()
    async def on_guild_soundboard_sound_delete(self, sound):
        await everything.handle_sound_delete(self.bot, sound)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry):
        await everything.handle_audit_log_entry_create(self.bot, entry)

    @commands.Cog.listener()
    async def on_entitlement_create(self, entitlement):
        await everything.handle_entitlement_create(self.bot, entitlement)

    @commands.Cog.listener()
    async def on_entitlement_update(self, entitlement):
        await everything.handle_entitlement_update(self.bot, entitlement)

    @commands.Cog.listener()
    async def on_entitlement_delete(self, entitlement):
        await everything.handle_entitlement_delete(self.bot, entitlement)

async def setup(bot):
    await bot.add_cog(ModerationLogs(bot))
