import discord
from .base import send_log_message
import json
from locales import get_string
import traceback
from datetime import datetime
from discord.utils import utcnow

async def handle_socket_raw(bot, msg):
    try:
        event_name = msg.get('t')
        data = msg.get('d')
        if not event_name or not data: return
        
        guild_id = data.get('guild_id')
        if not guild_id: return
        
        settings = await bot.server_settings.get_settings(int(guild_id))
        if not settings.get("logging_enabled"): return
        
        handled_events = [
            'GUILD_UPDATE', 'CHANNEL_CREATE', 'CHANNEL_DELETE', 'CHANNEL_UPDATE',
            'WEBHOOKS_UPDATE', 'GUILD_ROLE_CREATE', 'GUILD_ROLE_DELETE', 'GUILD_ROLE_UPDATE',
            'MESSAGE_DELETE', 'MESSAGE_UPDATE', 'GUILD_BAN_ADD', 'GUILD_BAN_REMOVE',
            'GUILD_MEMBER_ADD', 'GUILD_MEMBER_REMOVE', 'GUILD_MEMBER_UPDATE',
            'THREAD_CREATE', 'THREAD_DELETE', 'THREAD_UPDATE', 'INVITE_CREATE', 'INVITE_DELETE', 
            'CHANNEL_PINS_UPDATE', 'INTEGRATION_CREATE', 'INTEGRATION_DELETE', 'GUILD_EMOJIS_UPDATE',
            'GUILD_STICKERS_UPDATE', 'GUILD_SCHEDULED_EVENT_CREATE', 'GUILD_SCHEDULED_EVENT_DELETE',
            'GUILD_SCHEDULED_EVENT_UPDATE', 'STAGE_INSTANCE_CREATE', 'STAGE_INSTANCE_DELETE',
            'STAGE_INSTANCE_UPDATE', 'AUTO_MODERATION_RULE_CREATE', 'AUTO_MODERATION_RULE_DELETE',
            'AUTO_MODERATION_RULE_UPDATE', 'AUTO_MODERATION_ACTION_EXECUTION',
            'MESSAGE_REACTION_ADD', 'MESSAGE_REACTION_REMOVE', 'MESSAGE_REACTION_REMOVE_ALL',
            'MESSAGE_REACTION_REMOVE_EMOJI', 'GUILD_SCHEDULED_EVENT_USER_ADD', 'GUILD_SCHEDULED_EVENT_USER_REMOVE',
            'GUILD_SOUNDBOARD_SOUND_CREATE', 'GUILD_SOUNDBOARD_SOUND_UPDATE', 'GUILD_SOUNDBOARD_SOUND_DELETE',
            'ENTITLEMENT_CREATE', 'ENTITLEMENT_UPDATE', 'ENTITLEMENT_DELETE',
            'SUBSCRIPTION_CREATE', 'SUBSCRIPTION_UPDATE', 'SUBSCRIPTION_DELETE',
            'INTERACTION_CREATE', 'PRESENCE_UPDATE', 'TYPING_START', 'VOICE_SERVER_UPDATE', 'VOICE_CHANNEL_EFFECT_SEND'
        ]
        
        if event_name in handled_events: return

        lang = settings.get("language", "en")
        await send_log_message(
            bot, int(guild_id), "id",
            get_string("moderation.logging.event_formats.raw_event", lang, name=event_name, data=json.dumps(data, indent=2)[:1800]),
            is_raw=True
        )
    except:
        traceback.print_exc()

async def handle_voice_state_update(bot, member, before, after, join_times):
    try:
        settings = await bot.server_settings.get_settings(member.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        flags = settings.get("logging_flags_bitfield", 0)
        lang = settings.get("language", "en")
        guild_id = member.guild.id
        
        duration_text = ""
        if before.channel:
            join_time = join_times.get((member.id, guild_id))
            if join_time:
                delta = utcnow() - join_time
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_text = get_string("moderation.logging.event_formats.voice_duration", lang, duration=f"{hours}h {minutes}m {seconds}s")
                if after.channel is None:
                    del join_times[(member.id, guild_id)]

        if before.channel != after.channel:
            if before.channel is None and (flags & LoggingFlags.VOICE_JOIN):
                join_times[(member.id, guild_id)] = utcnow()
                await send_log_message(bot, guild_id, "voice_update", get_string("moderation.logging.event_formats.voice_join", lang, member=member.mention, channel=after.channel.mention), accessory_img=member.display_avatar.url)
            elif after.channel is None and (flags & LoggingFlags.VOICE_LEAVE):
                await send_log_message(bot, guild_id, "voice_update", get_string("moderation.logging.event_formats.voice_leave", lang, member=member.mention, channel=before.channel.mention) + duration_text, accessory_img=member.display_avatar.url)
            elif before.channel and after.channel and (flags & LoggingFlags.VOICE_MOVE):
                join_times[(member.id, guild_id)] = utcnow()
                await send_log_message(bot, guild_id, "voice_update", get_string("moderation.logging.event_formats.voice_move", lang, member=member.mention, before=before.channel.mention, after=after.channel.mention) + duration_text, accessory_img=member.display_avatar.url)

        if (flags & LoggingFlags.VOICE_STATE_ALL):
            if before.self_mute != after.self_mute or before.self_deaf != after.self_deaf or before.mute != after.mute or before.deaf != after.deaf:
                status = f"Mute: {after.self_mute} (Server: {after.mute}), Deaf: {after.self_deaf} (Server: {after.deaf})"
                await send_log_message(bot, guild_id, "voice_update", f"Voice state update for {member.mention}: {status}", accessory_img=member.display_avatar.url)
    except:
        traceback.print_exc()

async def handle_voice_server_update(bot, data):
    pass

async def handle_voice_channel_effect(bot, payload):
    try:
        settings = await bot.server_settings.get_settings(payload.guild_id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.VOICE_EFFECT): return
        await send_log_message(bot, payload.guild_id, "emoji_add", f"Voice effect sent in <#{payload.channel_id}> by <@{payload.user_id}>")
    except:
        traceback.print_exc()

async def handle_automod_action(bot, execution):
    try:
        settings = await bot.server_settings.get_settings(execution.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.AUTO_MOD): return
        lang = settings.get("language", "en")
        rule_name = "Unknown"
        try:
            rule = await execution.fetch_rule()
            rule_name = rule.name
        except:
            rule_name = f"Rule {execution.rule_id}"
        await send_log_message(bot, execution.guild.id, "moderation_swords", get_string("moderation.logging.event_formats.automod_execution", lang, rule=rule_name, action=execution.action.type.name, user=execution.user.mention))
    except:
        traceback.print_exc()

async def handle_reaction_add(bot, reaction, user):
    try:
        settings = await bot.server_settings.get_settings(user.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.REACTION_ADD): return
        lang = settings.get("language", "en")
        await send_log_message(bot, user.guild.id, "reaction_add", get_string("moderation.logging.event_formats.reaction_add", lang, member=user.mention, emoji=str(reaction.emoji), url=reaction.message.jump_url), action_by=user)
    except:
        traceback.print_exc()

async def handle_reaction_remove(bot, reaction, user):
    try:
        settings = await bot.server_settings.get_settings(user.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.REACTION_REMOVE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, user.guild.id, "reaction_remove", get_string("moderation.logging.event_formats.reaction_remove", lang, member=user.mention, emoji=str(reaction.emoji), url=reaction.message.jump_url), action_by=user)
    except:
        traceback.print_exc()

async def handle_reaction_clear(bot, message, reactions):
    try:
        settings = await bot.server_settings.get_settings(message.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.REACTION_REMOVE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, message.guild.id, "reaction_remove", get_string("moderation.logging.event_formats.reaction_clear", lang, url=message.jump_url))
    except:
        traceback.print_exc()

async def handle_reaction_clear_emoji(bot, reaction):
    try:
        settings = await bot.server_settings.get_settings(reaction.message.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.REACTION_REMOVE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, reaction.message.guild.id, "reaction_remove", get_string("moderation.logging.event_formats.reaction_emoji_clear", lang, emoji=str(reaction.emoji), url=reaction.message.jump_url))
    except:
        traceback.print_exc()

async def handle_poll_vote_add(bot, user, answer):
    try:
        settings = await bot.server_settings.get_settings(user.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.POLL_VOTE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, user.guild.id, "poll_vote_add", get_string("moderation.logging.event_formats.poll_vote_add", lang, member=user.mention, url=answer.poll.message.jump_url), action_by=user)
    except:
        traceback.print_exc()

async def handle_poll_vote_remove(bot, user, answer):
    try:
        settings = await bot.server_settings.get_settings(user.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.POLL_VOTE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, user.guild.id, "poll_vote_remove", get_string("moderation.logging.event_formats.poll_vote_remove", lang, member=user.mention, url=answer.poll.message.jump_url), action_by=user)
    except:
        traceback.print_exc()

async def handle_sound_create(bot, sound):
    try:
        settings = await bot.server_settings.get_settings(sound.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SOUND_ADD): return
        lang = settings.get("language", "en")
        await send_log_message(bot, sound.guild.id, "emoji_add", get_string("moderation.logging.event_formats.sound_create", lang, name=sound.name), action_by=sound.user)
    except:
        traceback.print_exc()

async def handle_sound_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SOUND_UPDATE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, after.guild.id, "emoji_update", get_string("moderation.logging.event_formats.sound_update", lang, name=after.name))
    except:
        traceback.print_exc()

async def handle_sound_delete(bot, sound):
    try:
        settings = await bot.server_settings.get_settings(sound.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SOUND_REMOVE): return
        lang = settings.get("language", "en")
        await send_log_message(bot, sound.guild.id, "emoji_remove", get_string("moderation.logging.event_formats.sound_delete", lang, name=sound.name))
    except:
        traceback.print_exc()

async def handle_entitlement_create(bot, entitlement):
    try:
        if not entitlement.guild_id: return
        settings = await bot.server_settings.get_settings(entitlement.guild_id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.ENTITLEMENTS): return
        await send_log_message(bot, entitlement.guild_id, "community_boosted", get_string("moderation.logging.event_formats.entitlement_create", "en", id=entitlement.id))
    except:
        traceback.print_exc()

async def handle_subscription_create(bot, subscription):
    try:
        if not subscription.guild_id: return
        settings = await bot.server_settings.get_settings(subscription.guild_id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SUBSCRIPTIONS): return
        await send_log_message(bot, subscription.guild_id, "community_boosted", get_string("moderation.logging.event_formats.subscription_create", "en", id=subscription.id))
    except:
        traceback.print_exc()

async def handle_audit_log_entry_create(bot, entry):
    try:
        settings = await bot.server_settings.get_settings(entry.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.AUDIT_LOG): return
        lang = settings.get("language", "en")
        await send_log_message(bot, entry.guild.id, "id", get_string("moderation.logging.event_formats.audit_entry", lang, action=entry.action.name), action_by=entry.user)
    except:
        traceback.print_exc()

async def handle_interaction(bot, interaction):
    pass

async def handle_presence_update(bot, before, after):
    pass

async def handle_typing(bot, channel, user, when):
    pass

async def handle_entitlement_update(bot, entitlement):
    pass

async def handle_entitlement_delete(bot, entitlement):
    pass
