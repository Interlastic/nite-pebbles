import discord
from .base import send_log_message
from locales import get_string
import traceback

async def handle_channel_create(bot, channel):
    try:
        settings = await bot.server_settings.get_settings(channel.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.CHANNEL_CREATE): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if channel.guild.me.guild_permissions.view_audit_log:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, channel.guild.id, "channel_add", get_string("moderation.logging.event_formats.channel_create", lang, channel=channel.mention, id=channel.id, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()

async def handle_channel_delete(bot, channel):
    try:
        settings = await bot.server_settings.get_settings(channel.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.CHANNEL_DELETE): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if channel.guild.me.guild_permissions.view_audit_log:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, channel.guild.id, "channel_remove", get_string("moderation.logging.event_formats.channel_delete", lang, name=channel.name, id=channel.id, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()

async def handle_channel_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.CHANNEL_UPDATE): return

        lang = settings.get("language", "en")
        changes = []
        if before.name != after.name:
            changes.append(get_string("moderation.logging.event_formats.channel_update_name", lang, before=before.name, after=after.name))
        if getattr(before, "slowmode_delay", None) != getattr(after, "slowmode_delay", None):
            changes.append(get_string("moderation.logging.event_formats.channel_slowmode_change", lang, before=before.slowmode_delay, after=after.slowmode_delay))
        if getattr(before, "topic", None) != getattr(after, "topic", None):
            changes.append(get_string("moderation.logging.event_formats.channel_topic_change", lang))
        if getattr(before, "nsfw", None) != getattr(after, "nsfw", None):
            changes.append(get_string("moderation.logging.event_formats.channel_nsfw_change", lang, before=before.nsfw, after=after.nsfw))
        
        if not changes: return

        action_by = None
        reason = "**No Reason**"
        if after.guild.me.guild_permissions.view_audit_log:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                if entry.target.id == after.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = "\n".join(changes)
        content += f"\nReason: **{reason}**"

        await send_log_message(bot, after.guild.id, "channel_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_webhook_update(bot, channel):
    try:
        settings = await bot.server_settings.get_settings(channel.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.WEBHOOK_UPDATE): return

        lang = settings.get("language", "en")
        action_by = None
        content = get_string("moderation.logging.event_formats.webhook_update_info", lang, channel=channel.mention)
        
        if channel.guild.me.guild_permissions.view_audit_log:
            async for entry in channel.guild.audit_logs(limit=1):
                if entry.action in (discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_delete, discord.AuditLogAction.webhook_update):
                    action_by = entry.user
                    if entry.action == discord.AuditLogAction.webhook_create:
                        content = get_string("moderation.logging.event_formats.webhook_create_detailed", lang, name=entry.target.name)
                    elif entry.action == discord.AuditLogAction.webhook_delete:
                        content = get_string("moderation.logging.event_formats.webhook_delete_detailed", lang, name=entry.before.name or "Unknown")
                    elif entry.action == discord.AuditLogAction.webhook_update:
                        content = get_string("moderation.logging.event_formats.webhook_update_detailed", lang, name=entry.target.name)
                    break

        await send_log_message(bot, channel.guild.id, "bot_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_thread_create(bot, thread):
    try:
        settings = await bot.server_settings.get_settings(thread.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.THREAD_CREATE): return

        lang = settings.get("language", "en")
        await send_log_message(bot, thread.guild.id, "channel_add", get_string("moderation.logging.event_formats.thread_create", lang, thread=thread.mention), action_by=thread.owner)
    except:
        traceback.print_exc()

async def handle_thread_delete(bot, thread):
    try:
        settings = await bot.server_settings.get_settings(thread.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.THREAD_DELETE): return

        lang = settings.get("language", "en")
        await send_log_message(bot, thread.guild.id, "channel_remove", get_string("moderation.logging.event_formats.thread_delete", lang, name=thread.name))
    except:
        traceback.print_exc()

async def handle_thread_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.THREAD_UPDATE): return
        lang = settings.get("language", "en")
        if before.name != after.name:
            await send_log_message(bot, after.guild.id, "thread_update", get_string("moderation.logging.event_formats.thread_update_name", lang, thread=after.mention, name=after.name))
    except:
        traceback.print_exc()

async def handle_stage_instance_create(bot, stage):
    try:
        settings = await bot.server_settings.get_settings(stage.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.STAGE_INSTANCE_ALL): return
        lang = settings.get("language", "en")
        await send_log_message(bot, stage.guild.id, "channel_add", get_string("moderation.logging.event_formats.stage_create", lang, topic=stage.topic, channel=stage.channel.mention))
    except:
        traceback.print_exc()

async def handle_stage_instance_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.STAGE_INSTANCE_ALL): return
        lang = settings.get("language", "en")
        if before.topic != after.topic:
            await send_log_message(bot, after.guild.id, "channel_update", get_string("moderation.logging.event_formats.stage_update", lang, before=before.topic, after=after.topic))
    except:
        traceback.print_exc()

async def handle_stage_instance_delete(bot, stage):
    try:
        settings = await bot.server_settings.get_settings(stage.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.STAGE_INSTANCE_ALL): return
        lang = settings.get("language", "en")
        await send_log_message(bot, stage.guild.id, "channel_remove", get_string("moderation.logging.event_formats.stage_delete", lang, channel=stage.channel.mention))
    except:
        traceback.print_exc()
