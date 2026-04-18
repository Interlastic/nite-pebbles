import discord
from .base import send_log_message
from locales import get_string
from ..ui import LoggingFlags
import io
import datetime

async def handle_message_create(bot, message):
    settings = await bot.server_settings.get_settings(message.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.MESSAGE_CREATE): return
    
    lang = settings.get("language", "en")
    content = f"Message by {message.author.mention} in {message.channel.mention}\n**Content**: {message.content or '[No Content]'}"
    
    if message.attachments:
        urls = ", ".join([f"[{a.filename}]({a.url})" for a in message.attachments])
        content += get_string("moderation.logging.event_formats.attachments", lang, urls=urls)
        
    await send_log_message(
        bot, message.guild.id, "message_add",
        content,
        accessory_img=message.author.display_avatar.url
    )

async def handle_message_delete(bot, message):
    if not message.guild: return
    settings = await bot.server_settings.get_settings(message.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.MESSAGE_DELETE): return

    lang = settings.get("language", "en")
    content_text = message.content or "[No Content]"
    action_by = None
    reason = "**No Reason**"
    if message.guild.me.guild_permissions.view_audit_log:
        async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            if entry.target.id == message.author.id:
                action_by = entry.user
                reason = entry.reason or "**No Reason**"
                break

    full_content = get_string("moderation.logging.event_formats.message_delete", lang, author=message.author.mention, channel=message.channel.mention, content=content_text)
    full_content += f"\nReason: **{reason}**"
    
    if message.attachments:
        urls = ", ".join([f"[{a.filename}]({a.url})" for a in message.attachments])
        full_content += get_string("moderation.logging.event_formats.attachments", lang, urls=urls)
        
    if message.poll:
        options = ", ".join([f"**{o.text}**" for o in message.poll.answers])
        full_content += get_string("moderation.logging.event_formats.poll_info", lang, question=message.poll.question.get('text', 'Unknown'), options=options)

    await send_log_message(
        bot, message.guild.id, "message_remove",
        full_content,
        accessory_img=message.author.display_avatar.url,
        action_by=action_by
    )

async def handle_message_edit(bot, before, after):
    if not after.guild or after.author.bot: return
    settings = await bot.server_settings.get_settings(after.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.MESSAGE_EDIT): return

    if before.content == after.content: return

    lang = settings.get("language", "en")
    await send_log_message(
        bot, after.guild.id, "message_update",
        get_string("moderation.logging.event_formats.message_edit", lang, author=after.author.mention, channel=after.channel.mention, before=before.content, after=after.content),
        accessory_img=after.author.display_avatar.url
    )

async def handle_bulk_message_delete(bot, messages):
    if not messages: return
    guild = messages[0].guild
    settings = await bot.server_settings.get_settings(guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.BULK_DELETE): return

    lang = settings.get("language", "en")
    channel = messages[0].channel
    
    log_content = get_string("moderation.logging.event_formats.bulk_delete_file_header", lang, channel=channel.name, count=len(messages))
    
    for msg in reversed(messages):
        timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        attachments = ""
        if msg.attachments:
            attachments = " [Attachments: " + ", ".join([a.url for a in msg.attachments]) + "]"
        
        line = f"[{timestamp}] {msg.author} ({msg.author.id}): {msg.content or '[No Content]'}{attachments}\n"
        
        if len(log_content.encode('utf-8')) + len(line.encode('utf-8')) > 300 * 1024:
            break
        log_content += line

    file_bytes = io.BytesIO(log_content.encode('utf-8'))
    log_file = discord.File(file_bytes, filename=get_string("moderation.logging.event_formats.bulk_delete_file_name", lang))

    await send_log_message(
        bot, guild.id, "bulk_message_delete", 
        get_string("moderation.logging.event_formats.bulk_delete_info", lang, count=len(messages), channel=channel.mention),
        file=log_file
    )

async def handle_invite_create(bot, invite):
    settings = await bot.server_settings.get_settings(invite.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.INVITE_ALL): return

    lang = settings.get("language", "en")
    duration = "Infinite" if invite.max_age == 0 else f"{invite.max_age}s"
    max_uses = "Infinite" if invite.max_uses == 0 else str(invite.max_uses)
    
    await send_log_message(
        bot, invite.guild.id, "invite_add",
        get_string("moderation.logging.event_formats.invite_create_detailed", lang, url=invite.url, duration=duration, max_uses=max_uses, temporary=str(invite.temporary)),
        action_by=invite.inviter
    )

async def handle_invite_delete(bot, invite):
    settings = await bot.server_settings.get_settings(invite.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.INVITE_ALL): return

    lang = settings.get("language", "en")
    await send_log_message(
        bot, invite.guild.id, "invite_remove",
        get_string("moderation.logging.event_formats.invite_delete", lang, code=invite.code)
    )

async def handle_pin_update(bot, channel, last_pin):
    settings = await bot.server_settings.get_settings(channel.guild.id)
    if not settings.get("logging_enabled"): return
    flags = settings.get("logging_flags_bitfield", 0)
    if not (flags & LoggingFlags.MESSAGE_PIN): return

    lang = settings.get("language", "en")
    await send_log_message(bot, channel.guild.id, "message_pin", get_string("moderation.logging.event_formats.pin_update", lang, channel=channel.mention))
