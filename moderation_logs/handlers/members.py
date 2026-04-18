import discord
from .base import send_log_message
from locales import get_string
import traceback

async def handle_member_ban(bot, guild, user):
    try:
        settings = await bot.server_settings.get_settings(guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_BAN_UNBAN): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, guild.id, "ban", get_string("moderation.logging.event_formats.member_ban", lang, member=user.mention, id=user.id, reason=reason), accessory_img=user.display_avatar.url, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_member_unban(bot, guild, user):
    try:
        settings = await bot.server_settings.get_settings(guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_BAN_UNBAN): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, guild.id, "unban", get_string("moderation.logging.event_formats.member_unban", lang, member=user.mention, id=user.id, reason=reason), accessory_img=user.display_avatar.url, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_member_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        flags = settings.get("logging_flags_bitfield", 0)

        lang = settings.get("language", "en")
        changes = []
        event_type = "member_update"
        action_by = None
        gallery = None
        reason = "**No Reason**"

        if before.timed_out_until != after.timed_out_until and (flags & LoggingFlags.MEMBER_BAN_UNBAN):
            if after.guild.me.guild_permissions.view_audit_log:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id:
                        action_by = entry.user
                        reason = entry.reason or "**No Reason**"
                        break
            
            if after.timed_out_until:
                changes.append(get_string("moderation.logging.event_formats.member_timeout", lang, until=int(after.timed_out_until.timestamp()), reason=reason))
                event_type = "timeout"
            else:
                changes.append(get_string("moderation.logging.event_formats.member_untimeout", lang, reason=reason))
                event_type = "timeout"

        if before.roles != after.roles and (flags & LoggingFlags.MEMBER_UPDATE):
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            if added: changes.append(get_string("moderation.logging.event_formats.member_role_add", lang, roles=", ".join(added)))
            if removed: changes.append(get_string("moderation.logging.event_formats.member_role_remove", lang, roles=", ".join(removed)))

        if before.premium_since != after.premium_since and (flags & LoggingFlags.MEMBER_UPDATE):
            if after.premium_since:
                changes.append(get_string("moderation.logging.event_formats.member_boost", lang))
            else:
                changes.append(get_string("moderation.logging.event_formats.member_unboost", lang))

        if before.nick != after.nick and (flags & LoggingFlags.MEMBER_UPDATE):
            changes.append(get_string("moderation.logging.event_formats.member_nick_change", lang, before=str(before.nick), after=str(after.nick)))

        if before.guild_avatar != after.guild_avatar and (flags & LoggingFlags.MEMBER_UPDATE):
            changes.append(get_string("moderation.logging.event_formats.user_avatar_update", lang))
            gallery = [str(before.display_avatar.url), str(after.display_avatar.url)]

        if not changes: return

        if after.guild.me.guild_permissions.view_audit_log:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    action_by = entry.user
                    break

        await send_log_message(bot, after.guild.id, event_type, get_string("moderation.logging.event_formats.member_update_title", lang, member=after.mention) + "\n" + "\n".join(changes), accessory_img=after.display_avatar.url, action_by=action_by, gallery_imgs=gallery)
    except:
        traceback.print_exc()

async def handle_member_remove(bot, member):
    try:
        settings = await bot.server_settings.get_settings(member.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_LEAVE_KICK): return

        lang = settings.get("language", "en")
        action_by = None
        event_type = "member_remove"
        content = get_string("moderation.logging.event_formats.member_remove", lang, name=member.name)

        if member.guild.me.guild_permissions.view_audit_log:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    action_by = entry.user
                    event_type = "kick"
                    content = get_string("moderation.logging.event_formats.member_kick", lang, member=member.mention, id=member.id, reason=entry.reason or "None")
                    break

        await send_log_message(bot, member.guild.id, event_type, content, accessory_img=member.display_avatar.url, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_member_join(bot, member):
    try:
        settings = await bot.server_settings.get_settings(member.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_JOIN): return

        lang = settings.get("language", "en")
        await send_log_message(bot, member.guild.id, "member_add", get_string("moderation.logging.event_formats.member_join", lang, member=member.mention), accessory_img=member.display_avatar.url)
    except:
        traceback.print_exc()

async def handle_member_join_request(bot, member):
    try:
        settings = await bot.server_settings.get_settings(member.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_JOIN_REQ): return
        lang = settings.get("language", "en")
        await send_log_message(bot, member.guild.id, "member_add", f"Join request created/updated for **{member.name}**")
    except:
        traceback.print_exc()

async def handle_user_update(bot, before, after):
    try:
        for guild in after.mutual_guilds:
            settings = await bot.server_settings.get_settings(guild.id)
            if not settings.get("logging_enabled"): continue
            from ..ui import LoggingFlags
            if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.MEMBER_UPDATE): continue
            
            lang = settings.get("language", "en")
            changes = []
            gallery = None
            if before.name != after.name:
                changes.append(get_string("moderation.logging.event_formats.member_username_change", lang, before=before.name, after=after.name))
            if before.display_name != after.display_name:
                changes.append(get_string("moderation.logging.event_formats.member_global_name_change", lang, before=before.display_name, after=after.display_name))
            if before.avatar != after.avatar:
                changes.append(get_string("moderation.logging.event_formats.user_avatar_update", lang))
                gallery = [str(before.display_avatar.url), str(after.display_avatar.url)]
            
            if not changes: continue
            
            await send_log_message(bot, guild.id, "member_update", get_string("moderation.logging.event_formats.member_update_title", lang, member=after.mention) + "\n" + "\n".join(changes), accessory_img=after.display_avatar.url, gallery_imgs=gallery)
    except:
        traceback.print_exc()
