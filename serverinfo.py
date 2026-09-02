import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, List, Union
import datetime

from locales import get_string, resolve_locale
from pebble_utils import make_loading_bar

# Custom Emojis (Discord Native from emojis.json)
EMOJI_ID = "<:ID:1493663589246963812>"
EMOJI_DISCORD = "<:dc:1493663575548362842>"
EMOJI_COMMUNITY = "<:cono:1493663579700989972>"
EMOJI_BOOST = "<:cobo:1493663694289371360>"
EMOJI_ADMIN = "<:uad:1493663591239254046>"
EMOJI_VERIF = "<:verif:1493663581974171798>"
EMOJI_SECURITY = "<:mosw:1493663587682484234>"
EMOJI_CHECK = "<:ch:1481722599590334565>"
EMOJI_CROSS = "<:cr:1481722596327297177>"
EMOJI_CLOCK = "<:cl:1481722597312958485>"
EMOJI_CLIPBOARD = "<:cb:1494012289601503324>"
EMOJI_BOT = "<:ba:1494051604289032272>"
EMOJI_MEMBER = "<:mea:1494051555408740472>"
EMOJI_CHANNEL = "<:ca:1494051594877272145>"
EMOJI_ROLE = "<:ra:1494051542922166302>"
EMOJI_EMOJI = "<:ea:1494051589303046174>"
EMOJI_INVITE = "<:ia:1494051563033854022>"
EMOJI_INTEGRATION = "<:ina:1494051569530962060>"
EMOJI_GUILD = "<:gu:1494051571468861627>"
EMOJI_PENDING = "<:pending:1505930291175358665>"
EMOJI_WARNING = "<:wn:1520360511039082537>"

FEATURE_NAMES = {
    "ANIMATED_BANNER": "Animated Server Banner",
    "ANIMATED_ICON": "Animated Server Icon",
    "APPLICATION_COMMAND_PERMISSIONS_V2": "App Permissions V2",
    "AUTO_MODERATION": "Auto-Moderation",
    "BANNER": "Server Banner",
    "COMMUNITY": "Community Features",
    "CREATOR_MONETIZABLE_PROVISIONAL": "Creator Monetization",
    "CREATOR_STORE_PAGE": "Creator Store Page",
    "DEVELOPER_SUPPORT_SERVER": "Developer Support Server",
    "DISCOVERABLE": "Server Discovery",
    "FEATURABLE": "Featured Server",
    "INVITES_DISABLED": "Invites Paused",
    "INVITE_SPLASH": "Custom Invite Splash",
    "MEMBER_VERIFICATION_GATE_ENABLED": "Membership Screening",
    "MONETIZATION_ENABLED": "Monetization Enabled",
    "MORE_STICKERS": "Expanded Stickers",
    "NEWS": "Announcement Channels",
    "PARTNERED": "Discord Partner",
    "PREVIEW_ENABLED": "Server Preview",
    "RAID_ALERTS_DISABLED": "Raid Alerts Disabled",
    "ROLE_ICONS": "Role Icons",
    "ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE": "Role Subscriptions Available",
    "ROLE_SUBSCRIPTIONS_ENABLED": "Role Subscriptions Enabled",
    "SOUNDBOARD": "Soundboard",
    "TICKETED_EVENTS_ENABLED": "Ticketed Events",
    "VANITY_URL": "Vanity Invite URL",
    "VERIFIED": "Verified Server",
    "VIP_REGIONS": "VIP Voice Regions",
    "WELCOME_SCREEN_ENABLED": "Welcome Screen",
}


class ServerInfoTabButton(ui.Button):
    def __init__(self, view_ref: "ServerInfoView", tab_id: str, label: str, emoji: str, is_active: bool = False):
        style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
        super().__init__(label=label, emoji=emoji, style=style, custom_id=f"tab_{tab_id}")
        self.view_ref = view_ref
        self.tab_id = tab_id

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.switch_tab(interaction, self.tab_id)


class ServerInfoRefreshButton(ui.Button):
    def __init__(self, view_ref: "ServerInfoView", label: str):
        super().__init__(label=label, emoji=EMOJI_GUILD, style=discord.ButtonStyle.secondary, custom_id="btn_refresh")
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.refresh(interaction)


class ServerInfoView(ui.LayoutView):
    def __init__(
        self,
        bot: commands.Bot,
        guild: discord.Guild,
        lang: str = "en",
        author_member: Optional[Union[discord.Member, discord.User]] = None
    ):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.lang = lang
        self.author_member = author_member
        self.author_id = author_member.id if author_member else None
        self.current_tab = "home"

        # Fetched Data attributes
        self.member_count: int = guild.member_count or 0
        self.online_count: int = 0
        self.integrations: Optional[List] = None
        self.bot_integrations: Optional[List] = None
        self.invites: Optional[List] = None
        self.automod_rules: Optional[List] = None
        self.bans_count: Optional[int] = None
        self.emojis_list: List = []
        self.stickers_list: List = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(get_string("errors.not_button_owner", self.lang), ephemeral=True)
            return False
        return True

    async def fetch_data(self):
        """
        Fetch dynamic data without relying on member caching.
        """
        # 1. Members and Online Presence Count
        self.member_count = self.guild.member_count or 0
        self.online_count = 0
        try:
            fetched = await self.bot.fetch_guild(self.guild.id, with_counts=True)
            self.member_count = getattr(fetched, "approximate_member_count", self.member_count) or self.member_count
            self.online_count = getattr(fetched, "approximate_presence_count", 0) or 0
        except (discord.HTTPException, discord.Forbidden):
            pass

        if self.online_count == 0 and self.guild.widget_enabled:
            try:
                widget = await self.guild.fetch_widget()
                self.online_count = widget.presence_count or 0
            except (discord.HTTPException, discord.Forbidden):
                pass

        # 2. Integrations and Bot Count (only fetch if bot has manage_guild)
        me = self.guild.me
        if me and me.guild_permissions.manage_guild:
            try:
                integrations = await self.guild.integrations()
                self.integrations = integrations
                self.bot_integrations = [
                    i for i in integrations
                    if isinstance(i, discord.BotIntegration)
                    or getattr(i, "type", "") in ("bot", "discord")
                    or getattr(i, "application", None) is not None
                ]
            except (discord.HTTPException, discord.Forbidden):
                self.integrations = None
                self.bot_integrations = None
        else:
            self.integrations = None
            self.bot_integrations = None

        # 3. Invites
        if me and me.guild_permissions.manage_guild:
            try:
                self.invites = await self.guild.invites()
            except (discord.HTTPException, discord.Forbidden):
                self.invites = None
        else:
            self.invites = None

        # 4. AutoMod Rules
        if me and me.guild_permissions.manage_guild:
            try:
                self.automod_rules = await self.guild.fetch_automod_rules()
            except (discord.HTTPException, discord.Forbidden):
                self.automod_rules = None
        else:
            self.automod_rules = None

        # 5. Bans
        if me and me.guild_permissions.ban_members:
            try:
                ban_count = 0
                async for _ in self.guild.bans(limit=1000):
                    ban_count += 1
                self.bans_count = ban_count
            except (discord.HTTPException, discord.Forbidden):
                self.bans_count = None
        else:
            self.bans_count = None

        # 6. Emojis and Stickers
        self.emojis_list = list(self.guild.emojis)
        self.stickers_list = list(self.guild.stickers)

    async def switch_tab(self, interaction: discord.Interaction, tab_id: str):
        self.current_tab = tab_id
        await self.build()
        await interaction.response.edit_message(view=self)

    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.fetch_data()
        await self.build()
        await interaction.edit_original_response(view=self)

    def _get_verif_level_str(self) -> str:
        lvl = self.guild.verification_level
        if lvl == discord.VerificationLevel.none:
            return get_string("serverinfo.verif_levels.none", self.lang)
        elif lvl == discord.VerificationLevel.low:
            return get_string("serverinfo.verif_levels.low", self.lang)
        elif lvl == discord.VerificationLevel.medium:
            return get_string("serverinfo.verif_levels.medium", self.lang)
        elif lvl == discord.VerificationLevel.high:
            return get_string("serverinfo.verif_levels.high", self.lang)
        elif lvl in (discord.VerificationLevel.highest, discord.VerificationLevel.very_high):
            return get_string("serverinfo.verif_levels.highest", self.lang)
        return str(lvl).title()

    def _get_filter_level_str(self) -> str:
        lvl = self.guild.explicit_content_filter
        if lvl == discord.ContentFilter.disabled:
            return get_string("serverinfo.filter_levels.disabled", self.lang)
        elif lvl == discord.ContentFilter.no_role:
            return get_string("serverinfo.filter_levels.no_role", self.lang)
        elif lvl == discord.ContentFilter.all_members:
            return get_string("serverinfo.filter_levels.all_members", self.lang)
        return str(lvl).title()

    def _get_notif_level_str(self) -> str:
        lvl = self.guild.default_notifications
        if lvl == discord.NotificationLevel.all_messages:
            return get_string("serverinfo.notif_levels.all_messages", self.lang)
        elif lvl == discord.NotificationLevel.only_mentions:
            return get_string("serverinfo.notif_levels.only_mentions", self.lang)
        return str(lvl).title()

    def _get_mfa_level_str(self) -> str:
        lvl = self.guild.mfa_level
        if lvl == discord.MFALevel.require_2fa:
            return get_string("serverinfo.mfa_levels.enabled", self.lang)
        return get_string("serverinfo.mfa_levels.disabled", self.lang)

    def _get_nsfw_level_str(self) -> str:
        lvl = self.guild.nsfw_level
        if lvl == discord.NSFWLevel.default:
            return get_string("serverinfo.nsfw_levels.default", self.lang)
        elif lvl == discord.NSFWLevel.explicit:
            return get_string("serverinfo.nsfw_levels.explicit", self.lang)
        elif lvl == discord.NSFWLevel.safe:
            return get_string("serverinfo.nsfw_levels.safe", self.lang)
        elif lvl == discord.NSFWLevel.age_restricted:
            return get_string("serverinfo.nsfw_levels.age_restricted", self.lang)
        return str(lvl).title()

    async def build(self):
        self.clear_items()
        lang = self.lang
        guild = self.guild
        created_ts = int(guild.created_at.timestamp())

        # Evaluate User Permissions for Option B (Masked Fields)
        user_perms = self.author_member.guild_permissions if isinstance(self.author_member, discord.Member) else discord.Permissions.none()
        can_view_security = user_perms.manage_guild or user_perms.moderate_members or user_perms.administrator
        can_view_integrations = user_perms.manage_guild or user_perms.administrator
        can_view_invites = user_perms.manage_guild or user_perms.administrator
        can_view_bans = user_perms.ban_members or user_perms.administrator

        perm_mod_label = get_string("serverinfo.perms.moderate_members", lang)
        perm_manage_label = get_string("serverinfo.perms.manage_guild", lang)
        perm_bans_label = get_string("serverinfo.perms.ban_members", lang)

        user_missing_mod = get_string("serverinfo.user_missing_perm", lang, perm=perm_mod_label)
        user_missing_manage = get_string("serverinfo.user_missing_perm", lang, perm=perm_manage_label)
        user_missing_bans = get_string("serverinfo.user_missing_perm", lang, perm=perm_bans_label)
        bot_missing_perm = get_string("serverinfo.missing_perm_general", lang)

        # ==========================================
        # TAB 1: HOME (COMPACT OVERVIEW)
        # ==========================================
        if self.current_tab == "home":
            container_items = []

            members_label = get_string("serverinfo.members", lang)
            online_label = get_string("serverinfo.online", lang)
            boosts_label = get_string("serverinfo.boosts", lang)
            tier_str = get_string("serverinfo.tier_format", lang, tier=guild.premium_tier)
            owner_label = get_string("serverinfo.owner", lang)
            created_label = get_string("serverinfo.created", lang)

            details_lines = [
                f"{EMOJI_MEMBER} **{members_label}:** {self.member_count:,} ({self.online_count:,} {online_label})",
                f"{EMOJI_BOOST} **{boosts_label}:** {guild.premium_subscription_count or 0} ({tier_str})",
                f"{EMOJI_ADMIN} **{owner_label}:** <@{guild.owner_id}>",
                f"{EMOJI_CLOCK} **{created_label}:** <t:{created_ts}:D> (<t:{created_ts}:R>)",
                f"-# {EMOJI_ID} ID: {guild.id}",
            ]

            content_text = f"# {guild.name}\n" + "\n".join(details_lines)

            # Compact layout: icon as accessory thumbnail
            if guild.icon:
                container_items.append(
                    ui.Section(
                        ui.TextDisplay(content=content_text),
                        accessory=ui.Thumbnail(guild.icon.url)
                    )
                )
            else:
                container_items.append(ui.TextDisplay(content=content_text))

            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 2: ASSETS & IMAGES
        # ==========================================
        elif self.current_tab == "assets":
            container_items = []
            title = get_string("serverinfo.tabs.assets", lang)

            asset_lines = []
            media_items = []

            # Server Icon
            icon_label = get_string("serverinfo.assets.icon", lang)
            if guild.icon:
                icon_links = f"[PNG]({guild.icon.with_format('png').url}) | [WEBP]({guild.icon.with_format('webp').url})"
                if guild.icon.is_animated():
                    icon_links += f" | [GIF]({guild.icon.with_format('gif').url})"
                asset_lines.append(f"{EMOJI_CHECK} **{icon_label}:** {icon_links}")
            else:
                asset_lines.append(f"{EMOJI_PENDING} **{icon_label}:** {get_string('serverinfo.assets.no_icon', lang)}")

            # Server Banner
            banner_label = get_string("serverinfo.assets.banner", lang)
            if guild.banner:
                banner_links = f"[PNG]({guild.banner.with_format('png').url}) | [WEBP]({guild.banner.with_format('webp').url})"
                if guild.banner.is_animated():
                    banner_links += f" | [GIF]({guild.banner.with_format('gif').url})"
                asset_lines.append(f"{EMOJI_CHECK} **{banner_label}:** {banner_links}")
                media_items.append(discord.MediaGalleryItem(guild.banner.url))
            else:
                asset_lines.append(f"{EMOJI_PENDING} **{banner_label}:** {get_string('serverinfo.assets.no_banner', lang)}")

            # Invite Splash
            splash_label = get_string("serverinfo.assets.splash", lang)
            if guild.splash:
                splash_links = f"[PNG]({guild.splash.with_format('png').url}) | [WEBP]({guild.splash.with_format('webp').url})"
                asset_lines.append(f"{EMOJI_CHECK} **{splash_label}:** {splash_links}")
                media_items.append(discord.MediaGalleryItem(guild.splash.url))
            else:
                asset_lines.append(f"{EMOJI_PENDING} **{splash_label}:** {get_string('serverinfo.assets.no_splash', lang)}")

            # Discovery Splash
            discovery_label = get_string("serverinfo.assets.discovery", lang)
            if guild.discovery_splash:
                discovery_links = f"[PNG]({guild.discovery_splash.with_format('png').url}) | [WEBP]({guild.discovery_splash.with_format('webp').url})"
                asset_lines.append(f"{EMOJI_CHECK} **{discovery_label}:** {discovery_links}")
                media_items.append(discord.MediaGalleryItem(guild.discovery_splash.url))
            else:
                asset_lines.append(f"{EMOJI_PENDING} **{discovery_label}:** {get_string('serverinfo.assets.no_discovery', lang)}")

            header_text = f"# {EMOJI_CLIPBOARD} {guild.name} - {title}\n" + "\n".join(asset_lines)
            if guild.icon:
                container_items.append(
                    ui.Section(
                        ui.TextDisplay(content=header_text),
                        accessory=ui.Thumbnail(guild.icon.url)
                    )
                )
            else:
                container_items.append(ui.TextDisplay(content=header_text))

            if media_items:
                container_items.append(ui.MediaGallery(*media_items))

            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 3: CHANNELS & CATEGORIES
        # ==========================================
        elif self.current_tab == "channels":
            container_items = []
            title = get_string("serverinfo.tabs.channels", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_CHANNEL} {guild.name} - {title}"))

            categories_count = len(guild.categories)
            text_count = len(guild.text_channels)
            voice_count = len(guild.voice_channels)
            stage_count = len(guild.stage_channels)
            forum_count = len(guild.forums)
            threads_count = len(guild.threads)
            total_channels = len(guild.channels)

            breakdown_lines = [
                f"### {EMOJI_CHANNEL} {get_string('serverinfo.channels.total', lang)}: {total_channels}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.categories', lang)}:** {categories_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.text', lang)}:** {text_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.voice', lang)}:** {voice_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.stage', lang)}:** {stage_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.forum', lang)}:** {forum_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.threads', lang)}:** {threads_count}",
                f"### {EMOJI_CLIPBOARD} {get_string('serverinfo.channels.special', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.rules', lang)}:** {guild.rules_channel.mention if guild.rules_channel else get_string('serverinfo.none', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.system', lang)}:** {guild.system_channel.mention if guild.system_channel else get_string('serverinfo.none', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.afk', lang)}:** {guild.afk_channel.name if guild.afk_channel else get_string('serverinfo.none', lang)} ({guild.afk_timeout // 60} min)",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.updates', lang)}:** {guild.public_updates_channel.mention if guild.public_updates_channel else get_string('serverinfo.none', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.safety', lang)}:** {guild.safety_alerts_channel.mention if guild.safety_alerts_channel else get_string('serverinfo.none', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.channels.widget', lang)}:** {guild.widget_channel.name if (guild.widget_enabled and guild.widget_channel) else get_string('serverinfo.none', lang)}",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(breakdown_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 4: ROLES & PERMISSIONS
        # ==========================================
        elif self.current_tab == "roles":
            container_items = []
            title = get_string("serverinfo.tabs.roles", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_ROLE} {guild.name} - {title}"))

            roles_total = len(guild.roles)
            highest_role = guild.roles[-1].mention if guild.roles else get_string("serverinfo.none", lang)
            hoisted_count = len([r for r in guild.roles if r.hoist])
            managed_count = len([r for r in guild.roles if r.is_bot_managed() or r.is_integration()])
            booster_role = guild.premium_subscriber_role.mention if guild.premium_subscriber_role else get_string("serverinfo.none", lang)

            # Top Roles display (sorted descending by position, excluding @everyone)
            top_roles = [r for r in reversed(guild.roles) if not r.is_default()]
            top_roles_display = " ".join([r.mention for r in top_roles[:15]])
            if len(top_roles) > 15:
                top_roles_display += f" ... (+{len(top_roles) - 15})"
            if not top_roles_display:
                top_roles_display = get_string("serverinfo.none", lang)

            # Default @everyone perms
            def_perms = guild.default_role.permissions
            perm_checks = [
                (def_perms.send_messages, get_string("serverinfo.roles.send_messages", lang)),
                (def_perms.create_instant_invite, get_string("serverinfo.roles.create_invites", lang)),
                (def_perms.embed_links, get_string("serverinfo.roles.embed_links", lang)),
                (def_perms.attach_files, get_string("serverinfo.roles.attach_files", lang)),
                (def_perms.mention_everyone, get_string("serverinfo.roles.mention_everyone", lang)),
            ]
            perms_str = " | ".join([
                f"{EMOJI_CHECK if enabled else EMOJI_CROSS} {name}"
                for enabled, name in perm_checks
            ])

            role_lines = [
                f"### {EMOJI_ROLE} {get_string('serverinfo.roles.total', lang)}: {roles_total}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.roles.highest', lang)}:** {highest_role}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.roles.hoisted', lang)}:** {hoisted_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.roles.managed', lang)}:** {managed_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.roles.booster', lang)}:** {booster_role}",
                f"### {EMOJI_ROLE} {get_string('serverinfo.roles.top_roles', lang)}",
                f"{top_roles_display}",
                f"### {EMOJI_SECURITY} {get_string('serverinfo.roles.default_perms', lang)}",
                f"{perms_str}",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(role_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 5: SECURITY & MODERATION
        # ==========================================
        elif self.current_tab == "security":
            container_items = []
            title = get_string("serverinfo.tabs.security", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_SECURITY} {guild.name} - {title}"))

            filter_str = self._get_filter_level_str() if can_view_security else user_missing_mod

            if not can_view_security:
                automod_str = user_missing_mod
            elif self.automod_rules is not None:
                automod_str = get_string("serverinfo.security.active_rules", lang, count=len(self.automod_rules))
            else:
                automod_str = bot_missing_perm

            sec_lines = [
                f"{EMOJI_VERIF} **{get_string('serverinfo.security.verification', lang)}:** {self._get_verif_level_str()}",
                f"{EMOJI_SECURITY} **{get_string('serverinfo.security.mfa', lang)}:** {self._get_mfa_level_str()}",
                f"{EMOJI_CLIPBOARD} **{get_string('serverinfo.security.explicit_filter', lang)}:** {filter_str}",
                f"{EMOJI_CLOCK} **{get_string('serverinfo.security.notifications', lang)}:** {self._get_notif_level_str()}",
                f"{EMOJI_WARNING} **{get_string('serverinfo.security.nsfw', lang)}:** {self._get_nsfw_level_str()}",
                f"{EMOJI_SECURITY} **{get_string('serverinfo.security.automod', lang)}:** {automod_str}",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(sec_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 6: BOOST & FEATURES
        # ==========================================
        elif self.current_tab == "boost":
            container_items = []
            title = get_string("serverinfo.tabs.boost", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_BOOST} {guild.name} - {title}"))

            tier = guild.premium_tier
            boost_count = guild.premium_subscription_count or 0
            vanity_url = f"discord.gg/{guild.vanity_url_code}" if guild.vanity_url_code else get_string("serverinfo.none", lang)

            # Boost progress calculation (Tier 1 = 2, Tier 2 = 7, Tier 3 = 14)
            req_boosts = 14 if tier >= 2 else (7 if tier == 1 else 2)
            progress_ratio = min(1.0, boost_count / req_boosts)
            loading_bar = make_loading_bar(progress_ratio * 100, 10)

            # Features formatting
            features_list = []
            for feat in guild.features:
                name = FEATURE_NAMES.get(feat, feat.replace("_", " ").title())
                features_list.append(f"{EMOJI_CHECK} {name}")
            features_str = "\n".join(features_list) if features_list else f"{EMOJI_PENDING} {get_string('serverinfo.none', lang)}"

            boost_lines = [
                f"### {EMOJI_BOOST} {get_string('serverinfo.boost.level', lang)}: Tier {tier}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.boost.count', lang)}:** {boost_count}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.boost.progress', lang)}:** {loading_bar} ({boost_count}/{req_boosts})",
                f"{EMOJI_COMMUNITY} **{get_string('serverinfo.boost.vanity', lang)}:** {vanity_url}",
                f"### {EMOJI_CLIPBOARD} {get_string('serverinfo.boost.features', lang)}",
                f"{features_str}",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(boost_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 7: EMOJIS & STICKERS
        # ==========================================
        elif self.current_tab == "emojis":
            container_items = []
            title = get_string("serverinfo.tabs.emojis", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_EMOJI} {guild.name} - {title}"))

            static_emojis = [e for e in self.emojis_list if not e.animated]
            animated_emojis = [e for e in self.emojis_list if e.animated]
            soundboard_count = len(getattr(guild, "soundboard_sounds", []))

            # Sample Preview (up to 25 emojis)
            if self.emojis_list:
                sample_emojis = " ".join([str(e) for e in self.emojis_list[:25]])
                if len(self.emojis_list) > 25:
                    sample_emojis += f" ... (+{len(self.emojis_list) - 25})"
            else:
                sample_emojis = get_string("serverinfo.emojis.no_emojis", lang)

            emoji_lines = [
                f"{EMOJI_PENDING} **{get_string('serverinfo.emojis.static', lang)}:** {len(static_emojis)} / {guild.emoji_limit}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.emojis.animated', lang)}:** {len(animated_emojis)} / {guild.emoji_limit}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.emojis.total', lang)}:** {len(self.emojis_list)} / {guild.emoji_limit * 2}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.emojis.stickers', lang)}:** {len(self.stickers_list)} / {guild.sticker_limit}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.emojis.soundboard', lang)}:** {soundboard_count}",
                f"### {EMOJI_EMOJI} {get_string('serverinfo.emojis.preview', lang)}",
                f"{sample_emojis}",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(emoji_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # TAB 8: INTEGRATIONS & ADVANCED
        # ==========================================
        elif self.current_tab == "more":
            container_items = []
            title = get_string("serverinfo.tabs.more", lang)
            container_items.append(ui.TextDisplay(content=f"# {EMOJI_INTEGRATION} {guild.name} - {title}"))

            # Integrations
            if not can_view_integrations:
                integrations_str = user_missing_manage
                bots_str = user_missing_manage
                other_str = user_missing_manage
            elif self.integrations is not None:
                integrations_str = f"{len(self.integrations):,}"
                bots_str = f"{len(self.bot_integrations):,}" if self.bot_integrations is not None else bot_missing_perm
                other_integrations = len(self.integrations) - (len(self.bot_integrations) if self.bot_integrations else 0)
                other_str = f"{other_integrations:,}"
            else:
                integrations_str = bot_missing_perm
                bots_str = bot_missing_perm
                other_str = bot_missing_perm

            # Invites & Bans
            if not can_view_invites:
                invites_str = user_missing_manage
            elif self.invites is not None:
                invites_str = f"{len(self.invites):,}"
            else:
                invites_str = bot_missing_perm

            if not can_view_bans:
                bans_str = user_missing_bans
            elif self.bans_count is not None:
                bans_str = f"{self.bans_count:,}"
            else:
                bans_str = bot_missing_perm

            # Limits & Locale (Public Technical Info)
            events_count = len(guild.scheduled_events)
            filesize_mb = guild.filesize_limit // (1024 * 1024)
            bitrate_kbps = guild.bitrate_limit // 1000
            max_presences_str = f"{guild.max_presences:,}" if guild.max_presences else get_string("serverinfo.unlimited", lang)
            max_members_str = f"{guild.max_members:,}" if guild.max_members else get_string("serverinfo.unknown", lang)

            more_lines = [
                f"### {EMOJI_INTEGRATION} {get_string('serverinfo.more.integrations', lang)}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.integrations', lang)}:** {integrations_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.bots_integrated', lang)}:** {bots_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.other_integrations', lang)}:** {other_str}",
                f"### {EMOJI_INVITE} {get_string('serverinfo.more.invites', lang)} & Moderation",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.invites', lang)}:** {invites_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.bans', lang)}:** {bans_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.events', lang)}:** {events_count}",
                f"### {EMOJI_CLIPBOARD} Technical Limits & Locale",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.locale', lang)}:** `{guild.preferred_locale}`",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.max_members', lang)}:** {max_members_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.max_presences', lang)}:** {max_presences_str}",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.filesize_limit', lang)}:** {filesize_mb} MB",
                f"{EMOJI_PENDING} **{get_string('serverinfo.more.bitrate_limit', lang)}:** {bitrate_kbps} kbps",
            ]

            container_items.append(ui.TextDisplay(content="\n".join(more_lines)))
            container_items.append(ui.Separator(visible=True))
            self.add_item(ui.Container(*container_items))

        # ==========================================
        # CONTAINER 2: BUTTONS & NAVIGATION
        # ==========================================
        # Row 1: Overview (emoji: pending), Assets, Channels, Roles
        row1 = ui.ActionRow(
            ServerInfoTabButton(self, "home", get_string("serverinfo.buttons.home", lang), EMOJI_PENDING, is_active=(self.current_tab == "home")),
            ServerInfoTabButton(self, "assets", get_string("serverinfo.buttons.assets", lang), EMOJI_CLIPBOARD, is_active=(self.current_tab == "assets")),
            ServerInfoTabButton(self, "channels", get_string("serverinfo.buttons.channels", lang), EMOJI_CHANNEL, is_active=(self.current_tab == "channels")),
            ServerInfoTabButton(self, "roles", get_string("serverinfo.buttons.roles", lang), EMOJI_ROLE, is_active=(self.current_tab == "roles")),
        )

        # Row 2: Security, Boost, Emojis, More Info, Refresh (emoji: guild)
        row2 = ui.ActionRow(
            ServerInfoTabButton(self, "security", get_string("serverinfo.buttons.security", lang), EMOJI_SECURITY, is_active=(self.current_tab == "security")),
            ServerInfoTabButton(self, "boost", get_string("serverinfo.buttons.boost", lang), EMOJI_BOOST, is_active=(self.current_tab == "boost")),
            ServerInfoTabButton(self, "emojis", get_string("serverinfo.buttons.emojis", lang), EMOJI_EMOJI, is_active=(self.current_tab == "emojis")),
            ServerInfoTabButton(self, "more", get_string("serverinfo.buttons.more", lang), EMOJI_INTEGRATION, is_active=(self.current_tab == "more")),
            ServerInfoRefreshButton(self, get_string("serverinfo.buttons.refresh", lang)),
        )

        buttons_container = ui.Container(row1, row2, accent_colour=discord.Colour.blurple())
        self.add_item(buttons_container)


class ServerInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="View comprehensive information and statistics about this server")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        if not interaction.guild:
            return

        # Defer immediately to prevent Discord interaction timeout errors
        await interaction.response.defer()

        lang = await resolve_locale(interaction)
        author_member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        view = ServerInfoView(self.bot, interaction.guild, lang, author_member=author_member)
        await view.fetch_data()
        await view.build()
        await interaction.followup.send(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerInfo(bot))
