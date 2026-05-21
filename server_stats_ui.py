import discord
from discord import ui
import re
import traceback
import math
from pebble_utils import render_template, format_number

from locales import get_string, resolve_locale

def render_template_simulated(template, members=999999, channels=500, boost_level=3, boost_count=99):
    if not template:
        return None
    stats = {
        "members": members,
        "channels": channels,
        "boost_level": boost_level,
        "boost_count": boost_count
    }
    def replacer(match):
        var = match.group(1)
        precision = match.group(3)
        if var in stats:
            val = stats[var]
            return format_number(val, precision)
        return match.group(0)
    return re.sub(r"\{(\w+)(,(\w+))?\}", replacer, template)

def validate_template(template, guild):
    """Returns (warnings: list, errors: list)"""
    current = render_template(template, guild)
    worst_case = render_template_simulated(template)
    warnings, errors = [], []
    if not current or not current.strip():
        errors.append("template_empty")
    elif worst_case and len(worst_case) > 100:
        warnings.append(("template_too_long", len(worst_case)))
    return warnings, errors

class ServerStatsButton(ui.Button):
    def __init__(self, bot_instance, server_settings, lang="en"):
        super().__init__(
            label=get_string("server_stats.buttons.main_dash", lang),
            style=discord.ButtonStyle.secondary,
            custom_id="server_stats_main"
        )
        self.bot = bot_instance
        self.server_settings = server_settings
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
                
            await interaction.response.defer()
            view = ServerStatsView(self.bot, self.server_settings, interaction.guild, interaction.user)
            await view.build()
            await interaction.followup.send(view=view, ephemeral=True)
        except Exception as e:
            print(f"[ServerStats] Button Error: {e}")
            traceback.print_exc()

class ServerStatsView(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user, page=1):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.page = page
        self.ITEMS_PER_PAGE = 4

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this menu (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        settings = await self.server_settings.get_settings(self.guild.id)
        stats_config = settings.get("server_stats", {})
        enabled = stats_config.get("enabled", False)
        lang = settings.get("language", "en")

        status_str = get_string(f"server_stats.status.{'enabled' if enabled else 'disabled'}", lang)
        
        # Header Container
        header_children = []
        if self.guild.icon:
            header_children.append(
                ui.Section(
                    ui.TextDisplay(content=f"# {get_string('server_stats.menu.title', lang)}"),
                    accessory=ui.Thumbnail(self.guild.icon.url)
                )
            )
        else:
            header_children.append(
                ui.TextDisplay(content=f"# {get_string('server_stats.menu.title', lang)}")
            )
        header_children.append(ui.Separator(visible=True))
        header_children.append(
            ui.TextDisplay(content=get_string("server_stats.menu.how_it_works", lang) + "\n\n" + get_string("server_stats.menu.status", lang, status=status_str))
        )
        self.add_item(ui.Container(
            *header_children,
            accent_colour=discord.Color.green() if enabled else discord.Color.red()
        ))

        # Main Actions Row
        toggle_btn = ui.Button(
            label=get_string(f"server_stats.buttons.toggle_{'off' if enabled else 'on'}", lang),
            style=discord.ButtonStyle.danger if enabled else discord.ButtonStyle.success
        )
        async def toggle_callback(interaction):
            stats_config["enabled"] = not enabled
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild.id, settings)
            await self.build()
            await interaction.response.edit_message(view=self)
        toggle_btn.callback = toggle_callback
        
        preview_btn = ui.Button(label=get_string("server_stats.buttons.preview", lang), style=discord.ButtonStyle.secondary)
        async def preview_callback(interaction):
            await self.show_preview(interaction, stats_config, lang)
        preview_btn.callback = preview_callback

        self.add_item(ui.ActionRow(toggle_btn, preview_btn))

        # Server Name Template Section
        server_template = stats_config.get("server_name_template")
        server_name_display = f"`{server_template}`" if server_template else get_string("server_stats.status.not_set", lang)
        
        edit_server_btn = ui.Button(label=get_string("server_stats.buttons.edit_server_name", lang), style=discord.ButtonStyle.blurple)
        async def edit_server_callback(interaction):
            try:
                modal = ServerNameModal(self.server_settings, self.guild.id, server_template, lang, self)
                await interaction.response.send_modal(modal)
            except Exception as e:
                print(f"[ServerStats] edit_server_callback error: {e}", flush=True)
                traceback.print_exc()
        edit_server_btn.callback = edit_server_callback

        clear_server_btn = ui.Button(
            label=get_string("server_stats.buttons.clear_server_name", lang), 
            style=discord.ButtonStyle.secondary if not enabled else discord.ButtonStyle.gray, 
            disabled=not server_template or not enabled
        )
        async def clear_server_callback(interaction):
            stats_config["server_name_template"] = None
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild.id, settings)
            await self.build()
            await interaction.response.edit_message(view=self)
        clear_server_btn.callback = clear_server_callback

        self.add_item(ui.Container(
            ui.TextDisplay(content=get_string("server_stats.menu.server_name", lang)),
            ui.TextDisplay(content=server_name_display),
            ui.ActionRow(edit_server_btn, clear_server_btn)
        ))

        # Category Settings
        category_name = stats_config.get("stats_category_name", "SERVER STATS")
        edit_cat_btn = ui.Button(
            label=get_string("server_stats.buttons.edit_category_name", lang), 
            style=discord.ButtonStyle.secondary if not enabled else discord.ButtonStyle.blurple,
            disabled=not enabled
        )
        async def edit_cat_callback(interaction):
            modal = CategoryNameModal(self.server_settings, self.guild.id, category_name, lang, self)
            await interaction.response.send_modal(modal)
        edit_cat_btn.callback = edit_cat_callback

        self.add_item(ui.Container(
            ui.TextDisplay(content=get_string("server_stats.menu.category_settings", lang)),
            ui.TextDisplay(content=f"**{category_name}**"),
            ui.ActionRow(edit_cat_btn)
        ))

        # Managed Channels Pagination
        overrides = stats_config.get("channel_overrides", {})
        stat_channels = stats_config.get("stat_channels", {})
        
        all_channels = []
        for ch_id, tmpl in overrides.items():
            all_channels.append({"id": str(ch_id), "template": tmpl, "type": "override"})
        for ch_id, tmpl in stat_channels.items():
            all_channels.append({"id": str(ch_id), "template": tmpl, "type": "stat_channel"})
            
        total_items = len(all_channels)
        total_pages = max(1, math.ceil(total_items / self.ITEMS_PER_PAGE))
        if self.page > total_pages:
            self.page = total_pages
            
        start_idx = (self.page - 1) * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        page_items = all_channels[start_idx:end_idx]

        # Add Channel Button
        add_channel_btn = ui.Button(label=get_string("server_stats.buttons.add_channel", lang), style=discord.ButtonStyle.success)
        async def add_channel_callback(interaction):
            view = ChannelCreationWizard(self.bot, self.server_settings, self.guild, self.user, lang, self)
            await view.build()
            await interaction.response.edit_message(view=view)
        add_channel_btn.callback = add_channel_callback

        managed_children = [
            ui.TextDisplay(content=get_string("server_stats.menu.managed_channels", lang) + f" ({total_items})")
        ]
        
        if not all_channels:
            managed_children.append(ui.TextDisplay(content=get_string("server_stats.menu.no_channels", lang)))
            managed_children.append(ui.ActionRow(add_channel_btn))
            self.add_item(ui.Container(*managed_children))
        else:
            missing_count = 0
            
            managed_container_children = [
                ui.TextDisplay(content=get_string("server_stats.menu.managed_channels", lang) + f" ({total_items})"),
            ]
            
            for item in page_items:
                channel = self.guild.get_channel(int(item["id"]))
                
                badge = get_string(f"server_stats.badges.{item['type'] if item['type'] == 'override' else 'voice'}", lang)
                if channel:
                    if isinstance(channel, discord.TextChannel):
                        badge = get_string("server_stats.badges.text", lang)
                    elif isinstance(channel, discord.CategoryChannel):
                        badge = get_string("server_stats.badges.category", lang)
                    name_display = f"{channel.mention}" if not isinstance(channel, discord.CategoryChannel) else f"**{channel.name}**"
                else:
                    badge = get_string("server_stats.badges.missing", lang)
                    name_display = f"Unknown ({item['id']})"
                    missing_count += 1
                    
                edit_btn = ui.Button(label=get_string("server_stats.buttons.edit", lang), style=discord.ButtonStyle.blurple)
                async def make_edit_cb(ch_item):
                    async def cb(interaction):
                        view = ChannelEditWizard(self.bot, self.server_settings, self.guild, self.user, lang, self, ch_item)
                        await view.build()
                        await interaction.response.edit_message(view=view)
                    return cb
                edit_btn.callback = await make_edit_cb(item)
                
                rm_btn = ui.Button(
                    label=get_string("server_stats.buttons.remove", lang), 
                    style=discord.ButtonStyle.secondary if not enabled else discord.ButtonStyle.danger,
                    disabled=not enabled
                )
                async def make_rm_cb(ch_item):
                    async def cb(interaction):
                        view = RemoveConfirmView(self.bot, self.server_settings, self.guild, self.user, lang, self, ch_item)
                        await view.build()
                        await interaction.response.edit_message(view=view)
                    return cb
                rm_btn.callback = await make_rm_cb(item)

                managed_container_children.append(ui.TextDisplay(content=f"**{name_display}** | `{badge}`\n`{item['template']}`"))
                managed_container_children.append(ui.ActionRow(edit_btn, rm_btn))
            
            if missing_count > 0:
                managed_container_children.append(ui.TextDisplay(content=get_string("server_stats.menu.missing_channels", lang, count=missing_count)))
                
            managed_container_children.append(ui.ActionRow(add_channel_btn))
            
            self.add_item(ui.Container(*managed_container_children))
            
            if total_pages > 1:
                prev_btn = ui.Button(label=get_string("server_stats.buttons.prev_page", lang), style=discord.ButtonStyle.secondary, disabled=(self.page <= 1))
                async def prev_cb(interaction):
                    self.page -= 1
                    await self.build()
                    await interaction.response.edit_message(view=self)
                prev_btn.callback = prev_cb
                
                page_indicator = ui.Button(label=get_string("server_stats.menu.page_indicator", lang, current=self.page, total=total_pages), style=discord.ButtonStyle.gray, disabled=True)
                
                next_btn = ui.Button(label=get_string("server_stats.buttons.next_page", lang), style=discord.ButtonStyle.secondary, disabled=(self.page >= total_pages))
                async def next_cb(interaction):
                    self.page += 1
                    await self.build()
                    await interaction.response.edit_message(view=self)
                next_btn.callback = next_cb
                
                self.add_item(ui.ActionRow(prev_btn, page_indicator, next_btn))

        # Back Row
        try:
            from extraDashboards import BackToMainDashButton
            back_btn = BackToMainDashButton()
        except ImportError:
            back_btn = ui.Button(label=get_string("server_stats.buttons.back", lang), style=discord.ButtonStyle.secondary)
            
        async def back_callback(interaction):
            from dashboard import updateDashboard
            await interaction.response.defer()
            await updateDashboard(interaction.message, self.server_settings, self.bot)
        back_btn.callback = back_callback

        self.add_item(ui.ActionRow(back_btn))

    async def show_preview(self, interaction, stats_config, lang):
        embed = discord.Embed(title=get_string("server_stats.menu.preview_title", lang), color=discord.Color.blue())
        
        server_template = stats_config.get("server_name_template")
        if server_template:
            rendered = render_template(server_template, self.guild)
            embed.add_field(name=get_string("server_stats.menu.server_name", lang), value=get_string("server_stats.preview.server_name", lang, name=rendered), inline=False)
        
        overrides = stats_config.get("channel_overrides", {})
        if overrides:
            lines = []
            for ch_id, template in overrides.items():
                rendered = render_template(template, self.guild)
                lines.append(get_string("server_stats.preview.channel", lang, mention=f"<#{ch_id}>", name=rendered))
            embed.add_field(name=get_string("server_stats.menu.channel_overrides", lang), value="\n".join(lines), inline=False)
            
        stat_channels = stats_config.get("stat_channels", {})
        if stat_channels:
            lines = []
            for ch_id, template in stat_channels.items():
                rendered = render_template(template, self.guild)
                lines.append(get_string("server_stats.preview.channel", lang, mention=f"<#{ch_id}>", name=rendered))
            embed.add_field(name=get_string("server_stats.menu.stat_channels", lang), value="\n".join(lines), inline=False)
            
        if not embed.fields:
            embed.description = get_string("server_stats.preview.empty", lang)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ChannelCreationWizard(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user, lang, parent_view):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.lang = lang
        self.parent_view = parent_view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        
        self.add_item(ui.Container(
            ui.TextDisplay(content=f"# {get_string('server_stats.wizard.choose_mode_title', self.lang)}"),
            ui.TextDisplay(content=get_string("server_stats.wizard.choose_mode_desc", self.lang))
        ))
        
        track_existing_btn = ui.Button(label=get_string("server_stats.buttons.track_existing", self.lang), style=discord.ButtonStyle.blurple)
        async def track_existing_cb(interaction):
            view = ExistingChannelPicker(self.bot, self.server_settings, self.guild, self.user, self.lang, self.parent_view)
            await view.build()
            await interaction.response.edit_message(view=view)
        track_existing_btn.callback = track_existing_cb

        create_new_btn = ui.Button(label=get_string("server_stats.buttons.create_new", self.lang), style=discord.ButtonStyle.success)
        async def create_new_cb(interaction):
            view = ChannelTypeCategoryWizard(self.bot, self.server_settings, self.guild, self.user, self.lang, self.parent_view)
            await view.build()
            await interaction.response.edit_message(view=view)
        create_new_btn.callback = create_new_cb
        
        self.add_item(ui.Container(
            ui.TextDisplay(content=get_string("server_stats.wizard.track_existing_desc", self.lang)),
            ui.ActionRow(track_existing_btn)
        ))
        
        self.add_item(ui.Container(
            ui.TextDisplay(content=get_string("server_stats.wizard.create_new_desc", self.lang)),
            ui.ActionRow(create_new_btn)
        ))

        back_btn = ui.Button(label=get_string("server_stats.buttons.back", self.lang), style=discord.ButtonStyle.secondary)
        async def back_cb(interaction):
            await self.parent_view.build()
            await interaction.response.edit_message(view=self.parent_view)
        back_btn.callback = back_cb
        self.add_item(ui.ActionRow(back_btn))

class ChannelTypeCategoryWizard(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user, lang, root_view):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.lang = lang
        self.root_view = root_view
        self.selected_type = discord.ChannelType.voice
        self.selected_category_id = None
        self.category_name = "SERVER STATS"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        settings = await self.server_settings.get_settings(self.guild.id)
        stats_config = settings.get("server_stats", {})
        self.category_name = stats_config.get("stats_category_name", "SERVER STATS")

        self.add_item(ui.Container(
            ui.TextDisplay(content=f"# {get_string('server_stats.wizard.choose_mode_title', self.lang)}"),
            ui.TextDisplay(content=get_string("server_stats.wizard.category_info", self.lang, category=self.category_name)),
            ui.TextDisplay(content=get_string("server_stats.wizard.category_warning", self.lang))
        ))

        type_select = ui.Select(
            placeholder=get_string("server_stats.wizard.channel_type_label", self.lang),
            options=[
                discord.SelectOption(label=get_string("server_stats.badges.voice", self.lang), value="voice", default=(self.selected_type == discord.ChannelType.voice)),
                discord.SelectOption(label=get_string("server_stats.badges.text", self.lang), value="text", default=(self.selected_type == discord.ChannelType.text)),
                discord.SelectOption(label=get_string("server_stats.badges.category", self.lang), value="category", default=(self.selected_type == discord.ChannelType.category))
            ]
        )
        async def type_cb(interaction):
            val = type_select.values[0]
            if val == "voice": self.selected_type = discord.ChannelType.voice
            elif val == "text": self.selected_type = discord.ChannelType.text
            elif val == "category": self.selected_type = discord.ChannelType.category
            await self.build()
            await interaction.response.edit_message(view=self)
        type_select.callback = type_cb

        # Category Select (only valid existing categories)
        existing_category = discord.utils.get(self.guild.categories, name=self.category_name)
        
        cat_options = []
        if existing_category:
            # If it exists, offer to use it
            cat_options.append(discord.SelectOption(
                label=get_string("server_stats.wizard.use_existing_category", self.lang, name=self.category_name), 
                value=str(existing_category.id), 
                default=(self.selected_category_id is None or str(self.selected_category_id) == str(existing_category.id))
            ))
            if self.selected_category_id is None:
                self.selected_category_id = str(existing_category.id)
        else:
            # If it doesn't exist, offer to create it
            cat_options.append(discord.SelectOption(
                label=get_string("server_stats.wizard.create_new_category", self.lang, name=self.category_name), 
                value="new", 
                default=(self.selected_category_id is None)
            ))

        # Add other categories
        for cat in self.guild.categories[:24]:
            if existing_category and cat.id == existing_category.id:
                continue
            cat_options.append(discord.SelectOption(
                label=cat.name, 
                value=str(cat.id), 
                default=(str(self.selected_category_id) == str(cat.id))
            ))
            if len(cat_options) >= 25: break
        
        cat_select = ui.Select(placeholder=get_string("server_stats.wizard.category_name_label", self.lang), options=cat_options)
        async def cat_cb(interaction):
            val = cat_select.values[0]
            self.selected_category_id = None if val == "new" else val
            await self.build()
            await interaction.response.edit_message(view=self)
        cat_select.callback = cat_cb

        self.add_item(ui.ActionRow(type_select))
        if self.selected_type != discord.ChannelType.category:
            self.add_item(ui.ActionRow(cat_select))

        next_btn = ui.Button(label=get_string("server_stats.buttons.next_page", self.lang), style=discord.ButtonStyle.success)
        async def next_cb(interaction):
            try:
                modal = NewChannelTemplateModal(self.server_settings, self.guild.id, self.lang, self.root_view, self.selected_type, self.selected_category_id, self.category_name)
                await interaction.response.send_modal(modal)
            except Exception as e:
                print(f"[ServerStats] ChannelTypeCategoryWizard next_cb error: {e}", flush=True)
                traceback.print_exc()
        next_btn.callback = next_cb

        back_btn = ui.Button(label=get_string("server_stats.buttons.back", self.lang), style=discord.ButtonStyle.secondary)
        async def back_cb(interaction):
            view = ChannelCreationWizard(self.bot, self.server_settings, self.guild, self.user, self.lang, self.root_view)
            await view.build()
            await interaction.response.edit_message(view=view)
        back_btn.callback = back_cb

        self.add_item(ui.ActionRow(back_btn, next_btn))

class ExistingChannelPicker(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user, lang, root_view):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.lang = lang
        self.root_view = root_view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        self.add_item(ui.Container(
            ui.TextDisplay(content=f"# {get_string('server_stats.wizard.choose_mode_title', self.lang)}"),
            ui.TextDisplay(content=get_string("server_stats.wizard.track_existing_desc", self.lang))
        ))

        select = ui.ChannelSelect(
            placeholder="Select a channel to track",
            channel_types=[discord.ChannelType.text, discord.ChannelType.voice, discord.ChannelType.news, discord.ChannelType.stage_voice, discord.ChannelType.category]
        )
        async def select_cb(interaction):
            try:
                ch = select.values[0]
                modal = ChannelTemplateModal(self.server_settings, self.guild.id, ch.id, "", self.lang, self.root_view, channel_type="override")
                await interaction.response.send_modal(modal)
            except Exception as e:
                print(f"[ServerStats] ExistingChannelPicker select_cb error: {e}", flush=True)
                traceback.print_exc()
        select.callback = select_cb
        
        self.add_item(ui.ActionRow(select))

        back_btn = ui.Button(label=get_string("server_stats.buttons.back", self.lang), style=discord.ButtonStyle.secondary)
        async def back_cb(interaction):
            view = ChannelCreationWizard(self.bot, self.server_settings, self.guild, self.user, self.lang, self.root_view)
            await view.build()
            await interaction.response.edit_message(view=view)
        back_btn.callback = back_cb
        self.add_item(ui.ActionRow(back_btn))

class NewChannelTemplateModal(ui.Modal):
    def __init__(self, server_settings, guild_id, lang, root_view, ctype, category_id, new_cat_name):
        super().__init__(title=get_string("server_stats.modals.stat_channel_title", lang))
        self.server_settings = server_settings
        self.guild_id = guild_id
        self.lang = lang
        self.root_view = root_view
        self.ctype = ctype
        self.category_id = category_id
        self.new_cat_name = new_cat_name
        
        self.add_item(ui.TextDisplay(content=get_string("server_stats.wizard.template_help", lang)))
        
        self.template_input = ui.TextInput(
            label=get_string("server_stats.modals.template_label", lang),
            placeholder="{members} Members",
            min_length=1,
            max_length=100,
            required=True
        )
        self.add_item(self.template_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("You do not have the required permissions to perform this action (Manage Server).", ephemeral=True)

            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            template = self.template_input.value.strip()
            warnings, errors = validate_template(template, guild)
        except Exception as e:
            print(f"[ServerStats] NewChannelTemplateModal on_submit early error: {e}", flush=True)
            traceback.print_exc()
            return
        
        try:
            category = None
            if self.ctype != discord.ChannelType.category:
                if self.category_id:
                    category = guild.get_channel(int(self.category_id))
                else:
                    category = discord.utils.get(guild.categories, name=self.new_cat_name)
                    if not category:
                        category = await guild.create_category(self.new_cat_name)
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False, send_messages=False)
            }
            
            name = render_template(template, guild) or "Stat Channel"
            
            if self.ctype == discord.ChannelType.voice:
                channel = await guild.create_voice_channel(name, category=category, overwrites=overwrites)
            elif self.ctype == discord.ChannelType.text:
                channel = await guild.create_text_channel(name, category=category, overwrites=overwrites)
            else:
                channel = await guild.create_category(name, overwrites=overwrites)
                
            settings = await self.server_settings.get_settings(self.guild_id)
            stats_config = settings.get("server_stats", {})
            stat_channels = stats_config.get("stat_channels", {})
            stat_channels[str(channel.id)] = template
            stats_config["stat_channels"] = stat_channels
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild_id, settings)
            
            await self.root_view.build()
            
            # Post validation results
            if warnings or errors:
                await self.show_validation_warnings(interaction, warnings, errors)
            else:
                await interaction.edit_original_response(view=self.root_view)
        except Exception as e:
            await interaction.followup.send(f"Error creating channel: {e}", ephemeral=True)

    async def show_validation_warnings(self, interaction, warnings, errors):
        container = ui.Container(
            ui.TextDisplay(content="## Template Validation"),
            accent_colour=discord.Color.red()
        )
        for w in warnings:
            if w[0] == "template_too_long":
                container.add_item(ui.TextDisplay(content=get_string("server_stats.warnings.template_too_long", self.lang, length=w[1])))
        for e in errors:
            if e == "template_empty":
                container.add_item(ui.TextDisplay(content=get_string("server_stats.warnings.template_empty", self.lang)))
                
        ok_btn = ui.Button(label="OK", style=discord.ButtonStyle.secondary)
        async def ok_cb(i):
            await self.root_view.build()
            await i.response.edit_message(view=self.root_view)
        ok_btn.callback = ok_cb
        container.add_item(ui.ActionRow(ok_btn))
        
        warn_view = ui.LayoutView(timeout=None)
        warn_view.add_item(container)
        await interaction.edit_original_response(view=warn_view)

class ChannelTemplateModal(ui.Modal):
    """Unified modal for editing a channel's template. Works for both overrides and stat channels."""
    def __init__(self, server_settings, guild_id, channel_id, current_val, lang, root_view, channel_type="override"):
        super().__init__(title=get_string("server_stats.modals.channel_template_title", lang))
        self.server_settings = server_settings
        self.guild_id = guild_id
        self.channel_id = str(channel_id)
        self.lang = lang
        self.root_view = root_view
        self.channel_type = channel_type
        
        self.add_item(ui.TextDisplay(content=get_string("server_stats.wizard.template_help", lang)))
        
        self.template_input = ui.TextInput(
            label=get_string("server_stats.modals.template_label", lang),
            placeholder="{members} Members",
            default=current_val if current_val else "",
            min_length=1,
            max_length=100,
            required=True
        )
        self.add_item(self.template_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("You do not have the required permissions to perform this action (Manage Server).", ephemeral=True)

            await interaction.response.defer(ephemeral=True)
            settings = await self.server_settings.get_settings(self.guild_id)
            stats_config = settings.get("server_stats", {})
            template = self.template_input.value.strip()
        except Exception as e:
            print(f"[ServerStats] ChannelTemplateModal on_submit early error: {e}", flush=True)
            traceback.print_exc()
            return
        
        try:
            if self.channel_type == "override":
                store = stats_config.get("channel_overrides", {})
                store[self.channel_id] = template
                stats_config["channel_overrides"] = store
            else:
                store = stats_config.get("stat_channels", {})
                store[self.channel_id] = template
                stats_config["stat_channels"] = store
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild_id, settings)
            warnings, errors = validate_template(template, interaction.guild)
            
            if not errors:
                ch = interaction.guild.get_channel(int(self.channel_id))
                if ch:
                    new_name = render_template(template, interaction.guild)
                    if new_name:
                        try:
                            await ch.edit(name=new_name, reason="Server Stats UI Template Preview")
                        except Exception as e:
                            print(f"[ServerStats] Failed to edit channel preview: {e}", flush=True)

            await self.root_view.build()
            if warnings or errors:
                modal_instance = NewChannelTemplateModal(self.server_settings, self.guild_id, self.lang, self.root_view, None, None, None)
                await modal_instance.show_validation_warnings(interaction, warnings, errors)
            else:
                await interaction.edit_original_response(view=self.root_view)
        except Exception as e:
            print(f"[ServerStats] ChannelTemplateModal on_submit save error: {e}", flush=True)
            traceback.print_exc()

class ChannelEditWizard(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user, lang, root_view, channel_item):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.lang = lang
        self.root_view = root_view
        self.channel_item = channel_item

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        channel = self.guild.get_channel(int(self.channel_item["id"]))
        name_display = channel.mention if channel else f"Unknown ({self.channel_item['id']})"
        
        self.add_item(ui.Container(
            ui.TextDisplay(content=f"# {get_string('server_stats.wizard.edit_title', self.lang)}"),
            ui.TextDisplay(content=f"{name_display}\n`{self.channel_item['template']}`")
        ))
        
        edit_btn = ui.Button(label=get_string("server_stats.buttons.edit", self.lang), style=discord.ButtonStyle.blurple)
        async def edit_cb(interaction):
            try:
                modal = ChannelTemplateModal(
                    self.server_settings, self.guild.id, self.channel_item["id"],
                    self.channel_item["template"], self.lang, self.root_view,
                    channel_type=self.channel_item["type"]
                )
                await interaction.response.send_modal(modal)
            except Exception as e:
                print(f"[ServerStats] ChannelEditWizard edit_cb error: {e}", flush=True)
                traceback.print_exc()
        edit_btn.callback = edit_cb
        
        self.add_item(ui.ActionRow(edit_btn))
        
        back_btn = ui.Button(label=get_string("server_stats.buttons.back", self.lang), style=discord.ButtonStyle.secondary)
        async def back_cb(interaction):
            await self.root_view.build()
            await interaction.response.edit_message(view=self.root_view)
        back_btn.callback = back_cb
        
        self.add_item(ui.ActionRow(back_btn))

class RemoveConfirmView(ui.LayoutView):
    """Confirmation view when removing a channel. Offers to delete the Discord channel too."""
    def __init__(self, bot, server_settings, guild, user, lang, root_view, channel_item):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user
        self.lang = lang
        self.root_view = root_view
        self.channel_item = channel_item

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        channel = self.guild.get_channel(int(self.channel_item["id"]))
        name_display = channel.mention if channel else f"Unknown ({self.channel_item['id']})"
        
        self.add_item(ui.Container(
            ui.TextDisplay(content=f"# {get_string('server_stats.wizard.remove_title', self.lang)}"),
            ui.TextDisplay(content=f"{name_display}\n`{self.channel_item['template']}`"),
            ui.Separator(visible=True),
            ui.TextDisplay(content=get_string("server_stats.wizard.remove_desc", self.lang))
        ))

        # Stop tracking only
        stop_btn = ui.Button(label=get_string("server_stats.buttons.stop_tracking", self.lang), style=discord.ButtonStyle.danger)
        async def stop_cb(interaction):
            await self._remove_from_settings()
            await self.root_view.build()
            await interaction.response.edit_message(view=self.root_view)
        stop_btn.callback = stop_cb

        # Stop tracking AND delete the Discord channel
        delete_btn = ui.Button(
            label=get_string("server_stats.buttons.stop_and_delete", self.lang),
            style=discord.ButtonStyle.danger,
            disabled=(channel is None)  # Can't delete a missing channel
        )
        async def delete_cb(interaction):
            await self._remove_from_settings()
            
            error_msg = None
            if channel:
                try:
                    await channel.delete(reason="Removed from Server Stats")
                except discord.Forbidden:
                    error_msg = "I do not have permission to delete this channel."
                except discord.HTTPException as e:
                    error_msg = f"Failed to delete the channel: {e}"
                    
            await self.root_view.build()
            await interaction.response.edit_message(view=self.root_view)
            
            if error_msg:
                await interaction.followup.send(error_msg, ephemeral=True)
        delete_btn.callback = delete_cb

        back_btn = ui.Button(label=get_string("server_stats.buttons.back", self.lang), style=discord.ButtonStyle.secondary)
        async def back_cb(interaction):
            await self.root_view.build()
            await interaction.response.edit_message(view=self.root_view)
        back_btn.callback = back_cb

        self.add_item(ui.ActionRow(stop_btn, delete_btn))
        self.add_item(ui.ActionRow(back_btn))

    async def _remove_from_settings(self):
        settings = await self.server_settings.get_settings(self.guild.id)
        conf = settings.get("server_stats", {})
        if self.channel_item["type"] == "override":
            store = conf.get("channel_overrides", {})
            store.pop(self.channel_item["id"], None)
            conf["channel_overrides"] = store
        else:
            store = conf.get("stat_channels", {})
            store.pop(self.channel_item["id"], None)
            conf["stat_channels"] = store
        settings["server_stats"] = conf
        await self.server_settings.update_settings(self.guild.id, settings)

class ServerNameModal(ui.Modal):
    def __init__(self, server_settings, guild_id, current_val, lang, parent_view):
        super().__init__(title=get_string("server_stats.modals.server_name_title", lang))
        self.server_settings = server_settings
        self.guild_id = guild_id
        self.lang = lang
        self.parent_view = parent_view
        
        self.add_item(ui.TextDisplay(content=get_string("server_stats.wizard.template_help", lang)))
        
        self.template_input = ui.TextInput(
            label=get_string("server_stats.modals.template_label", lang),
            placeholder="{members} Members",
            default=current_val if current_val else "",
            min_length=0,
            max_length=100,
            required=False
        )
        self.add_item(self.template_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("You do not have the required permissions to perform this action (Manage Server).", ephemeral=True)

            await interaction.response.defer(ephemeral=True)
            settings = await self.server_settings.get_settings(self.guild_id)
            stats_config = settings.get("server_stats", {})
            template = self.template_input.value.strip() or None
            stats_config["server_name_template"] = template
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild_id, settings)
            warnings, errors = [], []
            if template:
                warnings, errors = validate_template(template, interaction.guild)
            await self.parent_view.build()
            if warnings or errors:
                modal_instance = NewChannelTemplateModal(self.server_settings, self.guild_id, self.lang, self.parent_view, None, None, None)
                await modal_instance.show_validation_warnings(interaction, warnings, errors)
            else:
                await interaction.edit_original_response(view=self.parent_view)
        except Exception as e:
            print(f"[ServerStats] ServerNameModal on_submit error: {e}", flush=True)
            traceback.print_exc()

class CategoryNameModal(ui.Modal):
    def __init__(self, server_settings, guild_id, current_val, lang, parent_view):
        super().__init__(title=get_string("server_stats.modals.category_name_title", lang))
        self.server_settings = server_settings
        self.guild_id = guild_id
        self.old_name = current_val
        self.lang = lang
        self.parent_view = parent_view
        
        self.name_input = ui.TextInput(
            label=get_string("server_stats.modals.category_name_label", lang),
            placeholder=get_string("server_stats.modals.category_name_placeholder", lang),
            default=current_val,
            min_length=1,
            max_length=100,
            required=True
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(get_string("errors.missing_permission", self.lang, permission="Manage Server"), ephemeral=True)

            await interaction.response.defer(ephemeral=True)
            
            new_name = self.name_input.value.strip()
            
            # Find and rename Discord category if it exists
            guild = interaction.guild
            existing_cat = discord.utils.get(guild.categories, name=self.old_name)
            if existing_cat:
                try:
                    audit_reason = get_string("server_stats.audit_reasons.category_rename", self.lang, user=interaction.user.name)
                    await existing_cat.edit(name=new_name, reason=audit_reason)
                except Exception as e:
                    print(f"[ServerStats] Failed to rename category in Discord: {e}")

            settings = await self.server_settings.get_settings(self.guild_id)
            stats_config = settings.get("server_stats", {})
            stats_config["stats_category_name"] = new_name
            settings["server_stats"] = stats_config
            await self.server_settings.update_settings(self.guild_id, settings)
            
            await self.parent_view.build()
            await interaction.edit_original_response(view=self.parent_view)
        except Exception as e:
            print(f"[ServerStats] CategoryNameModal on_submit error: {e}", flush=True)
            traceback.print_exc()
