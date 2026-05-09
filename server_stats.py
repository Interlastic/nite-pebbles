import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from pebble_utils import render_template
from server_stats_ui import get_string

class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats.start()
        self.rename_throttle = {} # guild_id -> list of timestamps

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=10)
    async def update_stats(self):
        for guild in self.bot.guilds:
            try:
                await self.process_guild_updates(guild)
            except Exception as e:
                print(f"[ServerStats] Error processing {guild.name}: {e}")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

    async def process_guild_updates(self, guild):
        settings = await self.bot.server_settings.get_settings(guild.id)
        config = settings.get("server_stats", {})
        if not config.get("enabled", False):
            return

        # 1. Server Name
        template = config.get("server_name_template")
        if template:
            new_name = render_template(template, guild)
            if new_name and guild.name != new_name:
                # Check throttle (2 per hour)
                now = datetime.now()
                history = self.rename_throttle.get(guild.id, [])
                # Filter history to last hour
                history = [t for t in history if now - t < timedelta(hours=1)]
                self.rename_throttle[guild.id] = history
                
                if len(history) < 2:
                    if guild.me.guild_permissions.manage_guild:
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
                await self.update_channel_name(channel, ch_template)

        # 3. Stat Channels
        stat_channels = config.get("stat_channels", {})
        for ch_id, ch_template in stat_channels.items():
            channel = guild.get_channel(int(ch_id))
            if channel:
                await self.update_channel_name(channel, ch_template)

    async def update_channel_name(self, channel, template):
        new_name = render_template(template, channel.guild)
        if new_name and channel.name != new_name:
            if channel.permissions_for(channel.guild.me).manage_channels:
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

        expected_name = render_template(config["server_name_template"], after)
        if after.name != expected_name:
            user = await self.get_audit_user(after, discord.AuditLogAction.guild_update, after.id)
            if user and user.id != self.bot.user.id:
                await self.notify_conflict(after, user, "server name")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        settings = await self.bot.server_settings.get_settings(after.guild.id)
        config = settings.get("server_stats", {})
        if not config.get("enabled", False):
            return

        ch_id_str = str(after.id)
        template = config.get("channel_overrides", {}).get(ch_id_str) or config.get("stat_channels", {}).get(ch_id_str)
        
        if template:
            expected_name = render_template(template, after.guild)
            if after.name != expected_name:
                user = await self.get_audit_user(after.guild, discord.AuditLogAction.channel_update, after.id)
                if user and user.id != self.bot.user.id:
                    await self.notify_conflict(after.guild, user, f"#{after.name} channel")

    async def get_audit_user(self, guild, action, target_id):
        if not guild.me.guild_permissions.view_audit_log:
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

    async def notify_conflict(self, guild, user, target_type):
        lang = await self.bot.server_settings.get_language(guild.id)
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
            bot_perms = channel.permissions_for(guild.me)
            if perms.read_messages and bot_perms.send_messages and not channel.permissions_for(guild.default_role).read_messages:
                try:
                    await channel.send(f"{user.mention} {msg}")
                    return
                except:
                    continue
        
        # 3. Any channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(f"{user.mention} {msg}")
                    return
                except:
                    continue

async def setup(bot):
    await bot.add_cog(ServerStats(bot))
