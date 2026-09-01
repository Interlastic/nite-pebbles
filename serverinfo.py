import discord
from discord import app_commands, ui
from discord.ext import commands
from ui_templates import template
from locales import get_localized, get_string, resolve_locale

class ServerInfoView(ui.View):
    def __init__(self, guild: discord.Guild, interaction: discord.Interaction, lang: str, cog):
        super().__init__(timeout=180)
        self.guild = guild
        self.original_interaction = interaction
        self.lang = lang
        self.cog = cog

        self.more_info_btn = ui.Button(label=get_string("serverinfo.buttons.more_info", self.lang), style=discord.ButtonStyle.primary)
        self.more_info_btn.callback = self.more_info_callback
        self.add_item(self.more_info_btn)

        self.images_btn = ui.Button(label=get_string("serverinfo.buttons.images", self.lang), style=discord.ButtonStyle.secondary)
        self.images_btn.callback = self.images_callback
        self.add_item(self.images_btn)

    async def more_info_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        view = SubmenuView(self.guild, self.lang, self.cog, self.original_interaction.user)

        channels_text = len([c for c in self.guild.channels if isinstance(c, discord.TextChannel)])
        channels_voice = len([c for c in self.guild.channels if isinstance(c, discord.VoiceChannel)])
        channels_category = len([c for c in self.guild.categories])
        channels_stage = len([c for c in self.guild.channels if isinstance(c, (discord.StageChannel, discord.ForumChannel))])

        emojis_static = len([e for e in self.guild.emojis if not e.animated])
        emojis_animated = len([e for e in self.guild.emojis if e.animated])

        description = self.guild.description
        vanity = getattr(self.guild, 'vanity_url_code', None)

        created_f = f"<t:{int(self.guild.created_at.timestamp())}:F>"
        created_r = f"<t:{int(self.guild.created_at.timestamp())}:R>"

        owner = self.guild.owner.mention if self.guild.owner else ""
        owner_id = self.guild.owner_id or ""

        desc_part = get_string("serverinfo.description_part", self.lang, description=description) if description else ""
        vanity_part = get_string("serverinfo.vanity_part", self.lang, vanity=f"discord.gg/{vanity}") if vanity else ""
        community_section = get_string("serverinfo.community_section", self.lang, description_part=desc_part, vanity_part=vanity_part) if (description or vanity) else ""

        msg = get_string("serverinfo.more_info_message", self.lang,
            owner=owner,
            owner_id=owner_id,
            created_f=created_f,
            created_r=created_r,
            channels_text=channels_text,
            channels_voice=channels_voice,
            channels_category=channels_category,
            channels_stage=channels_stage,
            roles=len(self.guild.roles),
            emojis_static=emojis_static,
            emojis_animated=emojis_animated,
            stickers=len(self.guild.stickers),
            verification=str(self.guild.verification_level).capitalize(),
            explicit=str(self.guild.explicit_content_filter).replace('_', ' ').capitalize(),
            community_section=community_section
        )
        title = get_string("serverinfo.more_info_title", self.lang, server_name=self.guild.name)

        template_view = template.message(title=title, message=msg, footer=get_string("serverinfo.basic_info_footer", self.lang, user=self.original_interaction.user.display_name))
        for item in list(view.children):
            view.remove_item(item)
            template_view.add_item(item)

        await interaction.followup.send(view=template_view)

    async def images_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        view = SubmenuView(self.guild, self.lang, self.cog, self.original_interaction.user)

        icon = self.guild.icon.url if self.guild.icon else None
        banner = self.guild.banner.url if self.guild.banner else None
        splash = self.guild.splash.url if self.guild.splash else None
        discovery = self.guild.discovery_splash.url if self.guild.discovery_splash else None

        icon_part = get_string("serverinfo.image_icon", self.lang, icon=icon) if icon else ""
        banner_part = get_string("serverinfo.image_banner", self.lang, banner=banner) if banner else ""
        splash_part = get_string("serverinfo.image_splash", self.lang, splash=splash) if splash else ""
        discovery_part = get_string("serverinfo.image_discovery", self.lang, discovery=discovery) if discovery else ""

        msg = get_string("serverinfo.images_message", self.lang,
            icon_part=icon_part,
            banner_part=banner_part,
            splash_part=splash_part,
            discovery_part=discovery_part
        )
        title = get_string("serverinfo.images_title", self.lang, server_name=self.guild.name)

        image_url = icon if icon else None

        template_view = template.message(title=title, message=msg, footer=get_string("serverinfo.basic_info_footer", self.lang, user=self.original_interaction.user.display_name), image_url=image_url)
        for item in list(view.children):
            view.remove_item(item)
            template_view.add_item(item)

        await interaction.followup.send(view=template_view)

class SubmenuView(ui.View):
    def __init__(self, guild, lang, cog, user):
        super().__init__(timeout=180)
        self.guild = guild
        self.lang = lang
        self.cog = cog
        self.user = user

        self.back_btn = ui.Button(label=get_string("serverinfo.buttons.back", self.lang), style=discord.ButtonStyle.danger)
        self.back_btn.callback = self.back_callback
        self.add_item(self.back_btn)

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.message.delete()


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_server_icon(self, guild):
        if "COMMUNITY" in guild.features:
            if guild.premium_tier >= 1:
                return "<:cobo:1493663694289371360>"
            return "<:cono:1493663579700989972>"
        return "<:dc:1493663575548362842>"

    def get_boost_icon(self):
        return "<:cobo:1493663694289371360>"

    @app_commands.command(name="serverinfo", description="View information about the current server.")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild = await self.bot.fetch_guild(interaction.guild.id, with_counts=True)

        lang = await resolve_locale(interaction)

        name_icon = self.get_server_icon(guild)
        boost_icon = self.get_boost_icon()

        total_members = getattr(guild, 'approximate_member_count', guild.member_count or 0)
        online_members = getattr(guild, 'approximate_presence_count', 0) or 0

        msg = get_string("serverinfo.basic_info", lang,
            name_icon=name_icon,
            server_name=guild.name,
            server_id=guild.id,
            total_members=total_members,
            online_members=online_members,
            boost_icon=boost_icon,
            boost_tier=guild.premium_tier,
            boost_count=guild.premium_subscription_count
        )

        title = get_string("serverinfo.title", lang)
        footer = get_string("serverinfo.basic_info_footer", lang, user=interaction.user.display_name)

        image_url = guild.icon.url if guild.icon else None

        view_logic = ServerInfoView(guild, interaction, lang, self)
        template_view = template.message(title=title, message=msg, footer=footer, image_url=image_url)
        for item in list(view_logic.children):
            view_logic.remove_item(item)
            template_view.add_item(item)

        await interaction.followup.send(view=template_view)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
