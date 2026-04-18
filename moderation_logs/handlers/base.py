import discord
from discord import ui
from locales import get_string
from pathlib import Path
import json
import traceback
from discord.utils import utcnow

async def send_log_message(bot, guild_id, event_type, content_text, accessory_img=None, action_by=None, is_raw=False, gallery_imgs=None, file=None):
    try:
        settings = await bot.server_settings.get_settings(guild_id)
        if not settings.get("logging_enabled"):
            return

        channel_id = settings.get("logging_channel")
        if not channel_id:
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(int(channel_id))
        if not channel:
            return
try:
    base_path = Path(__file__).parent.parent.parent.parent
    emoji_path = base_path / "moderation-icons" / "emojis.json"
    with open(emoji_path, "r") as f:
            emojis = json.load(f)

        emoji_val = emojis.get(event_type, "")
        lang = settings.get("language", "en")
        
        name = get_string(f"moderation.logging.event_titles.{event_type}", lang)
        if name == f"[moderation.logging.event_titles.{event_type}]":
            name = event_type.replace('_', ' ').title()
            
        title = f"## {emoji_val} {name}"
        
        container_items = []
        
        if is_raw:
            container_items.append(ui.TextDisplay(content=get_string("moderation.logging.warning_literally_everything", lang)))

        container_items.append(ui.TextDisplay(content=title))
        
        if accessory_img:
            container_items.append(ui.Section(
                ui.TextDisplay(content=content_text),
                accessory=ui.Thumbnail(accessory_img)
            ))
        else:
            container_items.append(ui.TextDisplay(content=content_text))

        if gallery_imgs and len(gallery_imgs) >= 2:
            container_items.append(ui.TextDisplay(content=get_string("moderation.logging.gallery_comparison", lang)))
            gallery_items = []
            for i, img_url in enumerate(gallery_imgs):
                desc_key = "old_avatar" if i == 0 else "new_avatar"
                gallery_items.append(discord.MediaGalleryItem(
                    media=img_url,
                    description=get_string(f"moderation.logging.{desc_key}", lang)
                ))
            container_items.append(discord.ui.MediaGallery(*gallery_items))

        if action_by:
            container_items.append(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
            container_items.append(ui.Section(
                ui.TextDisplay(content=get_string("moderation.logging.event_formats.action_by", lang, mention=action_by.mention)),
                accessory=ui.Thumbnail(action_by.display_avatar.url)
            ))

        now = utcnow()
        timestamp_text = f"-# {now.strftime('%Y-%m-%d')} - {now.strftime('%H:%M:%S')}"
        container_items.append(ui.TextDisplay(content=timestamp_text))

        view = ui.LayoutView()
        container = ui.Container(*container_items, accent_colour=discord.Colour.blue())
        view.add_item(container)

        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="Mod-Logs", user=bot.user)
        
        if not webhook:
            avatar_val = emojis.get("moderation_png", "moderation.png")
            base_path = Path(__file__).parent.parent.parent.parent
            avatar_path = base_path / "moderation-icons" / avatar_val
            with open(avatar_path, "rb") as f:
                webhook = await channel.create_webhook(name="Mod-Logs", avatar=f.read())

        send_kwargs = {
            "view": view,
            "username": "Nite Mod-Logs",
            "avatar_url": bot.user.display_avatar.url,
            "allowed_mentions": discord.AllowedMentions.none()
        }
        if file:
            send_kwargs["file"] = file

        await webhook.send(**send_kwargs)
    except Exception as e:
        print(f"[Moderation Logs] Error sending log message in guild {guild_id}: {e}")
        traceback.print_exc()
