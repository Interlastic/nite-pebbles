import discord
from discord import app_commands, ui
from discord.ext import commands
from ui_templates import template
from locales import get_localized, get_string, resolve_locale

async def more_info_callback(interaction: discord.Interaction, guild, lang, cog, original_user):
    await interaction.response.defer(ephemeral=False)

    channels_text = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
    channels_voice = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
    channels_category = len([c for c in guild.categories])
    channels_stage = len([c for c in guild.channels if isinstance(c, (discord.StageChannel, discord.ForumChannel))])

    emojis_static = len([e for e in guild.emojis if not e.animated])
    emojis_animated = len([e for e in guild.emojis if e.animated])

    description = guild.description
    vanity = getattr(guild, 'vanity_url_code', None)

    created_f = f"<t:{int(guild.created_at.timestamp())}:F>"
    created_r = f"<t:{int(guild.created_at.timestamp())}:R>"

    owner = guild.owner.mention if guild.owner else ""
    owner_id = guild.owner_id or ""

    desc_part = get_string("serverinfo.description_part", lang, description=description) if description else ""
    vanity_part = get_string("serverinfo.vanity_part", lang, vanity=f"discord.gg/{vanity}") if vanity else ""
    community_section = get_string("serverinfo.community_section", lang, description_part=desc_part, vanity_part=vanity_part) if (description or vanity) else ""

    msg = get_string("serverinfo.more_info_message", lang,
        owner=owner,
        owner_id=owner_id,
        created_f=created_f,
        created_r=created_r,
        channels_text=channels_text,
        channels_voice=channels_voice,
        channels_category=channels_category,
        channels_stage=channels_stage,
        roles=len(guild.roles),
        emojis_static=emojis_static,
        emojis_animated=emojis_animated,
        stickers=len(guild.stickers),
        verification=str(guild.verification_level).capitalize(),
        explicit=str(guild.explicit_content_filter).replace('_', ' ').capitalize(),
        community_section=community_section
    )
    title = get_string("serverinfo.more_info_title", lang, server_name=guild.name)

    template_view = template.message(title=title, message=msg, footer=get_string("serverinfo.basic_info_footer", lang, user=original_user.display_name))

    back_btn = ui.Button(label=get_string("serverinfo.buttons.back", lang), style=discord.ButtonStyle.danger)
    async def back_callback(inter):
        await inter.response.defer()
        await inter.message.delete()
    back_btn.callback = back_callback
    template_view.add_item(back_btn)

    await interaction.followup.send(view=template_view)


async def images_callback(interaction: discord.Interaction, guild, lang, cog, original_user):
    await interaction.response.defer(ephemeral=False)

    icon = guild.icon.url if guild.icon else None
    banner = guild.banner.url if guild.banner else None
    splash = guild.splash.url if guild.splash else None
    discovery = guild.discovery_splash.url if guild.discovery_splash else None

    icon_part = get_string("serverinfo.image_icon", lang, icon=icon) if icon else ""
    banner_part = get_string("serverinfo.image_banner", lang, banner=banner) if banner else ""
    splash_part = get_string("serverinfo.image_splash", lang, splash=splash) if splash else ""
    discovery_part = get_string("serverinfo.image_discovery", lang, discovery=discovery) if discovery else ""

    msg = get_string("serverinfo.images_message", lang,
        icon_part=icon_part,
        banner_part=banner_part,
        splash_part=splash_part,
        discovery_part=discovery_part
    )
    title = get_string("serverinfo.images_title", lang, server_name=guild.name)

    image_url = icon if icon else None

    template_view = template.message(title=title, message=msg, footer=get_string("serverinfo.basic_info_footer", lang, user=original_user.display_name), image_url=image_url)

    back_btn = ui.Button(label=get_string("serverinfo.buttons.back", lang), style=discord.ButtonStyle.danger)
    async def back_callback(inter):
        await inter.response.defer()
        await inter.message.delete()
    back_btn.callback = back_callback
    template_view.add_item(back_btn)

    await interaction.followup.send(view=template_view)


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

        template_view = template.message(title=title, message=msg, footer=footer, image_url=image_url)

        more_info_btn = ui.Button(label=get_string("serverinfo.buttons.more_info", lang), style=discord.ButtonStyle.primary)
        async def wrap_more_info(inter):
            await more_info_callback(inter, guild, lang, self, interaction.user)
        more_info_btn.callback = wrap_more_info

        images_btn = ui.Button(label=get_string("serverinfo.buttons.images", lang), style=discord.ButtonStyle.secondary)
        async def wrap_images(inter):
            await images_callback(inter, guild, lang, self, interaction.user)
        images_btn.callback = wrap_images

        template_view.add_item(more_info_btn)
        template_view.add_item(images_btn)

        await interaction.followup.send(view=template_view)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
