import asyncio
import discord
from discord import ui
from locales import get_string
from pathlib import Path
import json
import traceback
from discord.utils import utcnow

_MAX_CONTAINERS_PER_MESSAGE = 10
_BATCH_DELAY_SECONDS = 0.25
_batchers = {}
_webhooks = {}


class _LogBatcher:
    """Collect a short burst of log events into one Components V2 message."""

    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.pending = []
        self.worker = None

    def enqueue(self, item):
        self.pending.append(item)
        if self.worker is None or self.worker.done():
            self.worker = asyncio.create_task(self._run())

    async def _run(self):
        # A small debounce lets bursts from bulk actions share a message.
        while self.pending:
            await asyncio.sleep(_BATCH_DELAY_SECONDS)
            items = self.pending[:_MAX_CONTAINERS_PER_MESSAGE]
            del self.pending[:len(items)]
            await _send_log_batch(self.bot, self.guild_id, items)


async def _send_log_batch(bot, guild_id, items):
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

        base_path = Path(__file__).parent.parent.parent.parent
        emoji_path = base_path / "moderation-icons" / "emojis.json"
        with open(emoji_path, "r") as f:
            emojis = json.load(f)

        # LayoutView has a 40-descendant limit. Build each message by trial so
        # containers with galleries/accessories cannot overflow that limit.
        view_batches = []
        current_view = ui.LayoutView()
        current_files = []
        for item in items:
            try:
                current_view.add_item(item["container"])
            except ValueError:
                if not current_view.children:
                    raise
                view_batches.append((current_view, current_files))
                current_view = ui.LayoutView()
                current_files = []
                current_view.add_item(item["container"])
            if item["file"]:
                current_files.append(item["file"])
        if current_view.children:
            view_batches.append((current_view, current_files))

        webhook_key = (id(bot), guild_id, int(channel_id))
        webhook = _webhooks.get(webhook_key)
        if webhook is None:
            webhooks = await channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Mod-Logs", user=bot.user)
            if not webhook:
                avatar_val = emojis.get("moderation_png", "moderation.png")
                avatar_path = base_path / "moderation-icons" / avatar_val
                with open(avatar_path, "rb") as f:
                    webhook = await channel.create_webhook(name="Mod-Logs", avatar=f.read())
            _webhooks[webhook_key] = webhook

        for view, files in view_batches:
            send_kwargs = {
                "view": view,
                "username": "Nite Mod-Logs",
                "avatar_url": bot.user.display_avatar.url,
                "allowed_mentions": discord.AllowedMentions.none()
            }
            if len(files) == 1:
                send_kwargs["file"] = files[0]
            elif files:
                send_kwargs["files"] = files

            for attempt in range(3):
                try:
                    await webhook.send(**send_kwargs)
                    break
                except discord.HTTPException as error:
                    if error.status != 429 or attempt == 2:
                        raise
                    retry_after = getattr(error, "retry_after", None)
                    if retry_after is None:
                        retry_after = float(error.response.headers.get("X-RateLimit-Reset-After", 1.0))
                    await asyncio.sleep(max(float(retry_after), 0.5))
    except Exception as e:
        print(f"[Moderation Logs] Error sending log message in guild {guild_id}: {e}")
        traceback.print_exc()


async def send_log_message(bot, guild_id, event_type, content_text, accessory_img=None, action_by=None, is_raw=False, gallery_imgs=None, file=None):
    """Queue a log event so bursts can be sent as up to ten containers per message."""
    try:
        settings = await bot.server_settings.get_settings(guild_id)
        if not settings.get("logging_enabled"):
            return

        channel_id = settings.get("logging_channel")
        if not channel_id:
            return

        guild = bot.get_guild(guild_id)
        if not guild or not guild.get_channel(int(channel_id)):
            return

        base_path = Path(__file__).parent.parent.parent.parent
        emoji_path = base_path / "moderation-icons" / "emojis.json"
        with open(emoji_path, "r") as f:
            emojis = json.load(f)

        emoji_val = emojis.get(event_type, "")
        lang = settings.get("language", "en")
        name = get_string(f"moderation.logging.event_titles.{event_type}", lang)
        if name == f"[moderation.logging.event_titles.{event_type}]":
            name = event_type.replace('_', ' ').title()

        container_items = []
        if is_raw:
            container_items.append(ui.TextDisplay(content=get_string("moderation.logging.warning_literally_everything", lang)))
        container_items.append(ui.TextDisplay(content=f"## {emoji_val} {name}"))

        if accessory_img:
            container_items.append(ui.Section(ui.TextDisplay(content=content_text), accessory=ui.Thumbnail(accessory_img)))
        else:
            container_items.append(ui.TextDisplay(content=content_text))

        if gallery_imgs and len(gallery_imgs) >= 2:
            container_items.append(ui.TextDisplay(content=get_string("moderation.logging.gallery_comparison", lang)))
            gallery_items = []
            for i, img_url in enumerate(gallery_imgs):
                desc_key = "old_avatar" if i == 0 else "new_avatar"
                gallery_items.append(discord.MediaGalleryItem(media=img_url, description=get_string(f"moderation.logging.{desc_key}", lang)))
            container_items.append(discord.ui.MediaGallery(*gallery_items))

        if action_by:
            container_items.append(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
            container_items.append(ui.Section(
                ui.TextDisplay(content=get_string("moderation.logging.event_formats.action_by", lang, mention=action_by.mention)),
                accessory=ui.Thumbnail(action_by.display_avatar.url)
            ))

        now = utcnow()
        container_items.append(ui.TextDisplay(content=f"-# {now.strftime('%Y-%m-%d')} - {now.strftime('%H:%M:%S')}"))
        item = {"container": ui.Container(*container_items, accent_colour=discord.Colour.blue()), "file": file}
        key = (id(bot), guild_id)
        batcher = _batchers.setdefault(key, _LogBatcher(bot, guild_id))
        batcher.enqueue(item)
    except Exception as e:
        print(f"[Moderation Logs] Error queueing log message in guild {guild_id}: {e}")
        traceback.print_exc()
