import discord
from .base import send_log_message
from locales import get_string
import traceback

async def handle_guild_available(bot, guild_obj):
    settings = await bot.server_settings.get_settings(guild_obj.id)
    if not settings.get("logging_enabled"): return
    from ..ui import LoggingFlags
    if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.GUILD_UPDATE): return
    lang = settings.get("language", "en")
    await send_log_message(bot, guild_obj.id, "discord_logo", f"Guild became available: **{guild_obj.name}**")

async def handle_guild_remove(bot, guild_obj):
    settings = await bot.server_settings.get_settings(guild_obj.id)
    if not settings.get("logging_enabled"): return
    from ..ui import LoggingFlags
    if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.GUILD_UPDATE): return
    lang = settings.get("language", "en")
    await send_log_message(bot, guild_obj.id, "channel_remove", f"Guild removed/deleted: **{guild_obj.name}**")

async def handle_guild_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.GUILD_UPDATE): return

        lang = settings.get("language", "en")
        changes = []
        if before.name != after.name:
            changes.append(get_string("moderation.logging.event_formats.guild_update_name", lang, before=before.name, after=after.name))
        if before.owner_id != after.owner_id:
            changes.append(get_string("moderation.logging.event_formats.guild_owner_change", lang, before=before.owner_id, after=after.owner_id))
        if before.afk_timeout != after.afk_timeout:
            changes.append(get_string("moderation.logging.event_formats.guild_afk_change", lang, before=before.afk_timeout, after=after.afk_timeout))
        
        if not changes: return

        action_by = None
        reason = "**No Reason**"
        if after.me.guild_permissions.view_audit_log:
            async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
                action_by = entry.user
                reason = entry.reason or "**No Reason**"
                break

        content = "\n".join(changes)
        content += f"\nReason: **{reason}**"

        await send_log_message(bot, after.id, "guild_update", content, accessory_img=after.icon.url if after.icon else None, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_role_create(bot, role):
    try:
        settings = await bot.server_settings.get_settings(role.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.ROLE_CREATE): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if role.guild.me.guild_permissions.view_audit_log:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, role.guild.id, "role_add", get_string("moderation.logging.event_formats.role_create", lang, role=role.mention, id=role.id, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()

async def handle_role_delete(bot, role):
    try:
        settings = await bot.server_settings.get_settings(role.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.ROLE_DELETE): return

        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if role.guild.me.guild_permissions.view_audit_log:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        await send_log_message(bot, role.guild.id, "role_remove", get_string("moderation.logging.event_formats.role_delete", lang, name=role.name, id=role.id, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()

async def handle_role_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.ROLE_UPDATE): return

        lang = settings.get("language", "en")
        changes = []
        if before.name != after.name:
            changes.append(get_string("moderation.logging.event_formats.role_update_name", lang, before=before.name, after=after.name))
        if before.colour != after.colour:
            changes.append(get_string("moderation.logging.event_formats.role_colour_change", lang, before=str(before.colour), after=str(after.colour)))
        if before.permissions != after.permissions:
            changes.append(get_string("moderation.logging.event_formats.role_perm_change", lang))
        
        if not changes: return

        action_by = None
        reason = "**No Reason**"
        if after.guild.me.guild_permissions.view_audit_log:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
                if entry.target.id == after.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = "\n".join(changes)
        content += f"\nReason: **{reason}**"

        await send_log_message(bot, after.guild.id, "role_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_integration_create(bot, integration):
    try:
        settings = await bot.server_settings.get_settings(integration.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.INTEGRATION_ALL): return
        lang = settings.get("language", "en")
        
        action_by = None
        reason = "**No Reason**"
        if integration.guild.me.guild_permissions.view_audit_log:
            async for entry in integration.guild.audit_logs(limit=1, action=discord.AuditLogAction.integration_create):
                if entry.target.id == integration.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = get_string("moderation.logging.event_formats.integration_create", lang, name=integration.name)
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, integration.guild.id, "intergration_add", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_integration_update(bot, integration):
    try:
        settings = await bot.server_settings.get_settings(integration.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.INTEGRATION_ALL): return
        lang = settings.get("language", "en")
        
        action_by = None
        reason = "**No Reason**"
        if integration.guild.me.guild_permissions.view_audit_log:
            async for entry in integration.guild.audit_logs(limit=1, action=discord.AuditLogAction.integration_update):
                if entry.target.id == integration.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break
        
        content = get_string("moderation.logging.event_formats.integration_update", lang, name=integration.name)
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, integration.guild.id, "integration_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_guild_integrations_update(bot, guild):
    try:
        settings = await bot.server_settings.get_settings(guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.INTEGRATION_ALL): return
        
        action_by = None
        reason = "**No Reason**"
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.integration_update):
                action_by = entry.user
                reason = entry.reason or "**No Reason**"
                break
        
        content = "Integrations updated."
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, guild.id, "integration_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_integration_delete(bot, payload):
    try:
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        settings = await bot.server_settings.get_settings(payload.guild_id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.INTEGRATION_ALL): return
        lang = settings.get("language", "en")
        
        action_by = None
        reason = "**No Reason**"
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.integration_delete):
                # We don't have the integration object here, but we have integration_id in payload
                # entry.target might be discord.Object with ID
                if entry.target.id == payload.integration_id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = get_string("moderation.logging.event_formats.integration_delete", lang, name=str(payload.integration_id))
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, payload.guild_id, "integration_remove", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_emoji_update(bot, guild, before, after):
    try:
        settings = await bot.server_settings.get_settings(guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        flags = settings.get("logging_flags_bitfield", 0)
        lang = settings.get("language", "en")
        
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        
        if added and (flags & LoggingFlags.EMOJI_ADD):
            for e in added:
                reason = "**No Reason**"
                action_by = None
                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.emoji_create):
                        if entry.target.id == e.id:
                            action_by = entry.user
                            reason = entry.reason or "**No Reason**"
                            break
                await send_log_message(bot, guild.id, "emoji_add", get_string("moderation.logging.event_formats.emoji_create", lang, emoji=str(e), name=e.name) + f"\nReason: **{reason}**", action_by=action_by)
        if removed and (flags & LoggingFlags.EMOJI_REMOVE):
            for e in removed:
                reason = "**No Reason**"
                action_by = None
                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.emoji_delete):
                        if entry.target.id == e.id:
                            action_by = entry.user
                            reason = entry.reason or "**No Reason**"
                            break
                await send_log_message(bot, guild.id, "emoji_remove", get_string("moderation.logging.event_formats.emoji_delete", lang, name=e.name) + f"\nReason: **{reason}**", action_by=action_by)
    except:
        traceback.print_exc()

async def handle_sticker_update(bot, guild, before, after):
    try:
        settings = await bot.server_settings.get_settings(guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        flags = settings.get("logging_flags_bitfield", 0)
        lang = settings.get("language", "en")
        
        added = [s for s in after if s not in before]
        removed = [s for s in before if s not in after]
        
        if added and (flags & LoggingFlags.EMOJI_ADD):
            for s in added:
                reason = "**No Reason**"
                action_by = None
                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.sticker_create):
                        if entry.target.id == s.id:
                            action_by = entry.user
                            reason = entry.reason or "**No Reason**"
                            break
                await send_log_message(bot, guild.id, "sticker_add", get_string("moderation.logging.event_formats.sticker_create", lang, name=s.name) + f"\nReason: **{reason}**", accessory_img=s.url, action_by=action_by)
        if removed and (flags & LoggingFlags.EMOJI_REMOVE):
            for s in removed:
                reason = "**No Reason**"
                action_by = None
                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.sticker_delete):
                        if entry.target.id == s.id:
                            action_by = entry.user
                            reason = entry.reason or "**No Reason**"
                            break
                await send_log_message(bot, guild.id, "sticker_remove", get_string("moderation.logging.event_formats.sticker_delete", lang, name=s.name) + f"\nReason: **{reason}**", action_by=action_by)
    except:
        traceback.print_exc()

async def handle_scheduled_event_create(bot, event):
    try:
        settings = await bot.server_settings.get_settings(event.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SCHEDULED_EVENT_ALL): return
        lang = settings.get("language", "en")
        
        action_by = None
        reason = "**No Reason**"
        if event.guild.me.guild_permissions.view_audit_log:
            async for entry in event.guild.audit_logs(limit=1, action=discord.AuditLogAction.scheduled_event_create):
                if entry.target.id == event.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = get_string("moderation.logging.event_formats.event_create", lang, name=event.name)
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, event.guild.id, "invite_add", content, accessory_img=event.cover_image.url if event.cover_image else None, action_by=action_by or event.creator)
    except:
        traceback.print_exc()

async def handle_scheduled_event_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SCHEDULED_EVENT_ALL): return
        lang = settings.get("language", "en")
        if before.name != after.name:
            action_by = None
            reason = "**No Reason**"
            if after.guild.me.guild_permissions.view_audit_log:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.scheduled_event_update):
                    if entry.target.id == after.id:
                        action_by = entry.user
                        reason = entry.reason or "**No Reason**"
                        break
            
            content = get_string("moderation.logging.event_formats.event_update", lang, name=after.name)
            content += f"\nReason: **{reason}**"
            await send_log_message(bot, after.guild.id, "invite_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_scheduled_event_delete(bot, event):
    try:
        settings = await bot.server_settings.get_settings(event.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SCHEDULED_EVENT_ALL): return
        lang = settings.get("language", "en")
        
        action_by = None
        reason = "**No Reason**"
        if event.guild.me.guild_permissions.view_audit_log:
            async for entry in event.guild.audit_logs(limit=1, action=discord.AuditLogAction.scheduled_event_delete):
                if entry.target.id == event.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break

        content = get_string("moderation.logging.event_formats.event_delete", lang, name=event.name)
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, event.guild.id, "invite_remove", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_scheduled_event_user_add(bot, event, user):
    try:
        settings = await bot.server_settings.get_settings(event.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SCHEDULED_EVENT_ALL): return
        await send_log_message(bot, event.guild.id, "member_add", f"{user.mention} is interested in event: **{event.name}**")
    except:
        traceback.print_exc()

async def handle_scheduled_event_user_remove(bot, event, user):
    try:
        settings = await bot.server_settings.get_settings(event.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.SCHEDULED_EVENT_ALL): return
        await send_log_message(bot, event.guild.id, "member_remove", f"{user.name} is no longer interested in event: **{event.name}**")
    except:
        traceback.print_exc()

async def handle_automod_rule_create(bot, rule):
    try:
        settings = await bot.server_settings.get_settings(rule.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.AUTOMOD_RULE_ALL): return
        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if rule.guild.me.guild_permissions.view_audit_log:
            async for entry in rule.guild.audit_logs(limit=1, action=discord.AuditLogAction.automod_rule_create):
                if entry.target.id == rule.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break
        await send_log_message(bot, rule.guild.id, "role_add", get_string("moderation.logging.event_formats.automod_rule_create", lang, name=rule.name, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()

async def handle_automod_rule_update(bot, before, after):
    try:
        settings = await bot.server_settings.get_settings(after.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.AUTOMOD_RULE_ALL): return
        
        lang = settings.get("language", "en")
        changes = []
        if before.name != after.name:
            changes.append(f"Name: **{before.name}** -> **{after.name}**")
        if before.trigger_type != after.trigger_type:
            changes.append(f"Trigger: **{before.trigger_type.name}** -> **{after.trigger_type.name}**")
        if before.enabled != after.enabled:
            changes.append(f"Enabled: **{before.enabled}** -> **{after.enabled}**")
        
        if not changes: return
        
        action_by = None
        reason = "**No Reason**"
        if after.guild.me.guild_permissions.view_audit_log:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.automod_rule_update):
                if entry.target.id == after.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break
        
        content = get_string("moderation.logging.event_formats.automod_rule_update", lang, name=after.name)
        content += get_string("moderation.logging.event_formats.automod_diff", lang, changes=", ".join(changes))
        content += f"\nReason: **{reason}**"
        
        await send_log_message(bot, after.guild.id, "role_update", content, action_by=action_by)
    except:
        traceback.print_exc()

async def handle_automod_rule_delete(bot, rule):
    try:
        settings = await bot.server_settings.get_settings(rule.guild.id)
        if not settings.get("logging_enabled"): return
        from ..ui import LoggingFlags
        if not (settings.get("logging_flags_bitfield", 0) & LoggingFlags.AUTOMOD_RULE_ALL): return
        lang = settings.get("language", "en")
        action_by = None
        reason = "**No Reason**"
        if rule.guild.me.guild_permissions.view_audit_log:
            async for entry in rule.guild.audit_logs(limit=1, action=discord.AuditLogAction.automod_rule_delete):
                if entry.target.id == rule.id:
                    action_by = entry.user
                    reason = entry.reason or "**No Reason**"
                    break
        await send_log_message(bot, rule.guild.id, "role_remove", get_string("moderation.logging.event_formats.automod_rule_delete", lang, name=rule.name, reason=reason), action_by=action_by)
    except:
        traceback.print_exc()
