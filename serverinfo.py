import discord
from discord.ext import commands
from discord import app_commands
from locales import resolve_locale, get_string, get_localized
from ui_templates import template

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_submenu_view(self, title, message, lang, image_url=None):
        view = template.message(title=title, message=message, image_url=image_url)

        back_btn = discord.ui.Button(label=get_string("serverinfo.buttons.back", lang), style=discord.ButtonStyle.danger)
        async def back_callback(inter):
            await inter.message.delete()
        back_btn.callback = back_callback

        if hasattr(discord.ui, "ActionRow"):
            view.add_item(discord.ui.ActionRow(back_btn))
        else:
            view.add_item(back_btn)

        return view

    @app_commands.command(name="serverinfo", description="Displays detailed information about the server")
    @app_commands.allowed_installs(users=False, guilds=True)
    @app_commands.allowed_contexts(dms=False, private_channels=False, guilds=True)
    async def serverinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        lang = resolve_locale(interaction) if not __import__("inspect").iscoroutinefunction(resolve_locale) else await resolve_locale(interaction)

        try:
            guild = await self.bot.fetch_guild(interaction.guild.id, with_counts=True)
        except discord.HTTPException:
            guild = interaction.guild

        # Basic Info
        server_name = guild.name
        server_id = guild.id
        owner_id = guild.owner_id
        created_at = guild.created_at

        # Counts
        member_count = getattr(guild, 'approximate_member_count', guild.member_count)
        online_count = getattr(guild, 'approximate_presence_count', 0)
        role_count = len(guild.roles)

        # Channels
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        stage_channels = len(guild.stage_channels)
        forum_channels = len(guild.forums)

        # Boost Status
        boost_tier = guild.premium_tier
        boost_count = guild.premium_subscription_count

        # Emojis and Stickers
        emojis = guild.emojis
        static_emojis = len([e for e in emojis if not e.animated])
        animated_emojis = len([e for e in emojis if e.animated])
        sticker_count = len(guild.stickers)

        # Visual Assets URLs
        icon_url = guild.icon.url if guild.icon else None
        banner_url = guild.banner.url if guild.banner else None
        splash_url = guild.splash.url if guild.splash else None
        discovery_splash_url = guild.discovery_splash.url if guild.discovery_splash else None

        # Moderation
        verification_level = guild.verification_level.name if hasattr(guild, 'verification_level') else "Unknown"
        explicit_content_filter = guild.explicit_content_filter.name if hasattr(guild, 'explicit_content_filter') else "Unknown"

        # Community Features
        description = guild.description
        vanity_url = guild.vanity_url_code

        # Emojis logic
        is_community = "COMMUNITY" in guild.features
        is_boosted = boost_tier > 0 or boost_count > 0

        if is_community and is_boosted:
            name_emoji = "<:cobo:1493663694289371360>"
        elif is_community and not is_boosted:
            name_emoji = "<:cono:1493663579700989972>"
        else:
            name_emoji = "<:dc:1493663575548362842>"

        # Build Main String
        main_message = f"{name_emoji} **{server_name}**\n"
        main_message += f"<:ID:1493663589246963812> {server_id}\n"
        main_message += f"<:uad:1493663591239254046> {online_count}/{member_count}\n"

        tier_label = get_string("serverinfo.labels.tier", lang)
        boosts_label = get_string("serverinfo.labels.boosts", lang)
        main_message += f"<:cobo:1493663694289371360> {tier_label} {boost_tier} ({boost_count} {boosts_label})"

        view = template.message(message=main_message, image_url=icon_url)

        # Details Button
        details_btn = discord.ui.Button(label=get_string("serverinfo.buttons.details", lang), style=discord.ButtonStyle.primary)
        async def details_callback(inter):
            created_timestamp = int(created_at.timestamp())
            owner_mention = f"<@{owner_id}>" if owner_id else "Unknown"

            content = f"**{get_string('serverinfo.labels.owner', lang)}**: {owner_mention} (`{owner_id}`)\n"
            content += f"**{get_string('serverinfo.labels.created', lang)}**: <t:{created_timestamp}:F> (<t:{created_timestamp}:R>)\n\n"

            content += f"**{get_string('serverinfo.labels.channels', lang)}**:\n"
            content += f"• {get_string('serverinfo.labels.text', lang)}: {text_channels}\n"
            content += f"• {get_string('serverinfo.labels.voice', lang)}: {voice_channels}\n"
            content += f"• {get_string('serverinfo.labels.category', lang)}: {categories}\n"
            content += f"• {get_string('serverinfo.labels.stage_forum', lang)}: {stage_channels + forum_channels}\n\n"

            content += f"**{get_string('serverinfo.labels.roles', lang)}**: {role_count}\n"

            static_lbl = get_string("serverinfo.labels.static", lang)
            anim_lbl = get_string("serverinfo.labels.animated", lang)
            content += f"**{get_string('serverinfo.labels.emojis', lang)}**: {static_emojis} {static_lbl}, {animated_emojis} {anim_lbl}\n"

            content += f"**{get_string('serverinfo.labels.stickers', lang)}**: {sticker_count}\n\n"

            content += f"**{get_string('serverinfo.labels.moderation', lang)}**:\n"
            content += f"• {get_string('serverinfo.labels.verification', lang)}: {verification_level}\n"
            content += f"• {get_string('serverinfo.labels.content_filter', lang)}: {explicit_content_filter}\n"

            if description:
                content += f"\n**{get_string('serverinfo.labels.description', lang)}**: {description}"
            if vanity_url:
                content += f"\n**{get_string('serverinfo.labels.vanity', lang)}**: {vanity_url}"

            sub_view = self.create_submenu_view(get_string("serverinfo.titles.details", lang), content, lang)
            await inter.response.send_message(view=sub_view, ephemeral=False)

        details_btn.callback = details_callback

        # Images Button
        images_btn = discord.ui.Button(label=get_string("serverinfo.buttons.images", lang), style=discord.ButtonStyle.primary)
        async def images_callback(inter):
            content = ""
            if icon_url:
                content += f"**{get_string('serverinfo.labels.icon', lang)}**: [Link]({icon_url})\n"
            if banner_url:
                content += f"**{get_string('serverinfo.labels.banner', lang)}**: [Link]({banner_url})\n"
            if splash_url:
                content += f"**{get_string('serverinfo.labels.splash', lang)}**: [Link]({splash_url})\n"
            if discovery_splash_url:
                content += f"**{get_string('serverinfo.labels.discovery_splash', lang)}**: [Link]({discovery_splash_url})\n"

            if not content:
                content = get_string('serverinfo.labels.no_images', lang)

            sub_view = self.create_submenu_view(get_string("serverinfo.titles.images", lang), content, lang)
            await inter.response.send_message(view=sub_view, ephemeral=False)

        images_btn.callback = images_callback

        if hasattr(discord.ui, "Separator"):
            view.add_item(discord.ui.Separator(visible=True))

        if hasattr(discord.ui, "ActionRow"):
            view.add_item(discord.ui.ActionRow(details_btn, images_btn))
        else:
            view.add_item(details_btn)
            view.add_item(images_btn)

        await interaction.followup.send(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerInfo(bot))
