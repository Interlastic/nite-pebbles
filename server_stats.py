import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from pebble_utils import render_template
from locales import get_string, resolve_locale

class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rename_throttle = {} # guild_id -> list of timestamps

    async def cog_load(self):
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=6)
    async def update_stats(self):
        for guild_cached in self.bot.guilds:
            try:
                # 1. Fetch guild with counts
                fetched = await self.bot.fetch_guild(guild_cached.id, with_counts=True)
                
                # 2. Fetch bot member for permissions
                me = await guild_cached.fetch_member(self.bot.user.id)
                
                # 3. Get online count
                online_count = getattr(fetched, 'approximate_presence_count', 0)
                if online_count == 0:
                    try:
                        widget = await guild_cached.fetch_widget()
                        online_count = widget.presence_count
                    except:
                        pass
                
                await self.process_guild_updates(guild_cached, fetched, me, online_count)
            except Exception as e:
                print(f"[ServerStats] Error processing {guild_cached.name}: {e}")

    @update_stats.before_loop
    async def before_update_stats(self):
        try:
            await self.bot.wait_until_ready()
        except RuntimeError:
            while not self.bot.is_closed():
                if getattr(self.bot, "_connection", None) and self.bot.is_ready():
                    break
                await asyncio.sleep(1)

    async def process_guild_updates(self, guild, fetched, me, online_count):
        settings = await self.bot.server_settings.get_settings(guild.id)
        config = settings.get("server_stats", {})
        if not config.get("enabled", False):
            return

        # 1. Server Name
        template = config.get("server_name_template")
        if template:
            new_name = render_template(template, fetched, online_count)
            if new_name and guild.name != new_name:
                # Check throttle (2 per hour)
                now = datetime.now()
                history = self.rename_throttle.get(guild.id, [])
                # Filter history to last hour
                history = [t for t in history if now - t < timedelta(hours=1)]
                self.rename_throttle[guild.id] = history
                
                if len(history) < 2:
                    if me.guild_permissions.manage_guild:
                        await guild.edit(name=new_name, reason="Nite Server Stats Update")
                        self.rename_throttle[guild.id].append(now)
                    else:
                        print(f"[ServerStats] Missing MANAGE_GUILD in {guild.name}")
                else:
                    print(f"[ServerStats] Throttled guild rename for {guild.name}")

        # 2. Channel Overrides
        overrides = config.get("channel_overrides", {})
        for ch_id, ch_template in overrides.items():
            channel = guild.get_channel(int(ch_id))
            if channel:
                await self.update_channel_name(channel, ch_template, fetched, me, online_count)

        # 3. Stat Channels
        stat_channels = config.get("stat_channels", {})
        for ch_id, ch_template in stat_channels.items():
            channel = guild.get_channel(int(ch_id))
            if channel:
                await self.update_channel_name(channel, ch_template, fetched, me, online_count)

    async def update_channel_name(self, channel, template, fetched, me, online_count):
        new_name = render_template(template, fetched, online_count)
        if new_name and channel.name != new_name:
            if channel.permissions_for(me).manage_channels:
                try:
                    await channel.edit(name=new_name, reason="Nite Server Stats Update")
                except discord.HTTPException as e:
                    if e.code == 50035: # Rate limit or invalid name
                        print(f"[ServerStats] Failed to rename {channel.name}: {e}")
                    else:
                        raise e
            else:
                print(f"[ServerStats] Missing MANAGE_CHANNELS for {channel.name} in {channel.guild.name}")

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        settings = await self.bot.server_settings.get_settings(after.id)
        config = settings.get("server_stats", {})
        if not config.get("enabled", False) or not config.get("server_name_template"):
            return
        
        # In listener, we might not have online_count easily, but we can try to render with what we have
        # This might cause false conflicts if {online} is used.
        # For now, let's just render with 0 online and hope for the best, or skip if {online} in template.
        template = config["server_name_template"]
        if "{online}" in template:
            return # Skip conflict check for templates with online count

        expected_name = render_template(template, after)
        if after.name != expected_name:
            me = after.me or await after.fetch_member(self.bot.user.id)
            user = await self.get_audit_user(after, me, discord.AuditLogAction.guild_update, after.id)
            if user and user.id != self.bot.user.id:
                await self.notify_conflict(after, me, user, "server name")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        settings = await self.bot.server_settings.get_settings(after.guild.id)
        config = settings.get("server_stats", {})
        if not config.get("enabled", False):
            return

        ch_id_str = str(after.id)
        template = config.get("channel_overrides", {}).get(ch_id_str) or config.get("stat_channels", {}).get(ch_id_str)
        
        if template:
            if "{online}" in template:
                return

            expected_name = render_template(template, after.guild)
            if after.name != expected_name:
                me = after.guild.me or await after.guild.fetch_member(self.bot.user.id)
                user = await self.get_audit_user(after.guild, me, discord.AuditLogAction.channel_update, after.id)
                if user and user.id != self.bot.user.id:
                    await self.notify_conflict(after.guild, me, user, f"#{after.name} channel")

    async def get_audit_user(self, guild, me, action, target_id):
        if not me.guild_permissions.view_audit_log:
            return None
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target and entry.target.id == target_id:
                    # Check if entry is recent (e.g. last 1 minute)
                    if (discord.utils.utcnow() - entry.created_at).total_seconds() < 60:
                        return entry.user
        except:
            pass
        return None

    async def notify_conflict(self, guild, me, user, target_type):
        lang = await resolve_locale(guild)
        msg = get_string("server_stats.conflict.notify", lang, type=target_type)
        
        # 1. DM
        try:
            await user.send(msg)
            return
        except:
            pass
        
        # 2. Private channel
        for channel in guild.text_channels:
            perms = channel.permissions_for(user)
            bot_perms = channel.permissions_for(me)
            if perms.read_messages and bot_perms.send_messages and not channel.permissions_for(guild.default_role).read_messages:
                try:
                    await channel.send(f"{user.mention} {msg}")
                    return
                except:
                    continue
        
        # 3. Any channel
        for channel in guild.text_channels:
            if channel.permissions_for(me).send_messages:
                try:
                    await channel.send(f"{user.mention} {msg}")
                    return
                except:
                    continue

async def setup(bot):
    await bot.add_cog(ServerStats(bot))
