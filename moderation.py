import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import re
import traceback
from pathlib import Path
from datetime import timedelta
from discord.utils import utcnow
from locales import get_string, resolve_locale, get_localized
from rapidfuzz import process, fuzz

class FuzzyUserSelect(ui.LayoutView):
    def __init__(self, cog, results, action_func, reason, duration=None, delete_messages="0", lang="en", orig_message=None):
        super().__init__(timeout=60)
        self.cog = cog
        self.results = results
        self.action_func = action_func
        self.reason = reason
        self.duration = duration
        self.delete_messages = delete_messages
        self.lang = lang
        self.orig_message = orig_message

        options = []
        for user, score, _ in results[:25]:
            label = f"{user.display_name} (@{user.name})"
            if len(label) > 100: label = label[:97] + "..."
            options.append(discord.SelectOption(
                label=label,
                description=f"ID: {user.id} | Match: {int(score)}%",
                value=str(user.id)
            ))

        select = ui.Select(placeholder=get_string("moderation.fuzzy_select.placeholder", lang), options=options)
        select.callback = self.select_callback
        
        container = ui.Container(
            ui.TextDisplay(content=f"# {get_string('moderation.fuzzy_select.title', lang)}"),
            ui.ActionRow(select),
            accent_colour=discord.Colour.orange()
        )
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        initiator = self.orig_message.author if self.orig_message else None
        if initiator and interaction.user.id != initiator.id:
            await interaction.response.send_message(get_string("errors.not_button_owner", self.lang), ephemeral=True)
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        user_id = int(interaction.data["values"][0])
        user = interaction.guild.get_member(user_id) or await self.cog.bot.fetch_user(user_id)
        
        # Attach context to interaction for the action function
        if self.orig_message and self.orig_message.reference:
            interaction.message_ref = self.orig_message.reference.resolved
            
        if self.duration:
            await self.action_func(interaction, user, self.duration, self.reason, edit=True)
        elif self.delete_messages != "0":
            await self.action_func(interaction, user, self.reason, self.delete_messages, edit=True)
        else:
            await self.action_func(interaction, user, self.reason, edit=True)

class DMMessageEditModal(ui.Modal):
    def __init__(self, cog, guild_id, lang):
        super().__init__(title=get_string("moderation.dm_modal.title", lang))
        self.cog = cog
        self.guild_id = guild_id
        self.lang = lang
        self.msg_input = ui.TextInput(
            label=get_string("moderation.dm_modal.label", lang),
            placeholder=get_string("moderation.dm_modal.placeholder", lang),
            style=discord.TextStyle.paragraph,
            min_length=0,
            max_length=500,
            required=False
        )
        self.add_item(self.msg_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(get_string("errors.missing_permission", self.lang, permission="Manage Server"), ephemeral=True)

        settings = await self.cog.bot.server_settings.get_settings(self.guild_id)
        settings["moderation_dm_message"] = self.msg_input.value
        await self.cog.bot.server_settings.update_settings(self.guild_id, settings)
        await interaction.response.send_message(get_string("moderation.dm_modal.success", self.lang), ephemeral=True)

class ModerationSettingsView(ui.LayoutView):
    def __init__(self, cog, guild, user, page=0):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild = guild
        self.user = user
        self.page = page
        self.files = []
        self.features = [
            {
                "id": "logging",
                "title_key": "moderation.features.logging.title",
                "desc_key": "moderation.features.logging.description",
                "btn_key": "moderation.features.logging.button",
                "emoji_key": "logging_clipboard"
            },
            {
                "id": "dm_message",
                "title_key": "moderation.features.dm_message.title",
                "desc_key": "moderation.features.dm_message.description",
                "btn_key": "moderation.features.dm_message.button",
                "emoji_key": "verification"
            }
        ]
        self.items_per_page = 5
        self.total_pages = (len(self.features) + self.items_per_page - 1) // self.items_per_page if self.features else 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        lang = await resolve_locale(interaction)
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(get_string("errors.not_button_owner", lang), ephemeral=True)
            return False
        return True

    async def build(self):
        try:
            self.clear_items()
            self.files = []
            lang = await resolve_locale(self.user)
            
            is_community = "COMMUNITY" in self.guild.features
            is_boosted = self.guild.premium_tier > 0
            
            if is_community:
                if is_boosted:
                    title_emoji = self.cog.emojis.get("community_boosted", "")
                    title_key = "moderation.menu.title_community_boosted"
                else:
                    title_emoji = self.cog.emojis.get("community", "")
                    title_key = "moderation.menu.title_community"
            else:
                title_emoji = self.cog.emojis.get("discord_logo", "")
                title_key = "moderation.menu.title_standard"
                
            verif_emoji = self.cog.emojis.get("verification", "")
            
            guild_name = self.guild.name
            if len(guild_name) > 30:
                guild_name = guild_name[:27] + "..."
                
            header_text = get_string(title_key, lang, emoji=title_emoji, name=guild_name, verif=verif_emoji)
            
            container_children = [
                ui.TextDisplay(content=f"# {header_text}")
            ]
            
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            page_features = self.features[start:end]
            
            for feat in page_features:
                btn = ui.Button(label=get_string(feat["btn_key"], lang), style=discord.ButtonStyle.blurple)
                
                async def btn_callback(interaction, fid=feat["id"]):
                    try:
                        lang_inner = await resolve_locale(interaction)
                        if not interaction.user.guild_permissions.manage_guild:
                            return await interaction.response.send_message(
                                get_string("errors.missing_permission", lang_inner, permission="Manage Server"),
                                ephemeral=True
                            )
                        
                        if fid == "logging":
                            from moderation_logs.ui import LoggingConfigView
                            view = LoggingConfigView(self.cog, self.guild, self.user)
                            await view.build()
                            return await interaction.response.send_message(view=view, ephemeral=True)
                        elif fid == "dm_message":
                            modal = DMMessageEditModal(self.cog, self.guild.id, lang_inner)
                            return await interaction.response.send_modal(modal)

                        await interaction.response.send_message(
                            get_string("moderation.features.config_coming_soon", lang_inner, feature=fid), 
                            ephemeral=True
                        )
                    except Exception as e:
                        lang_inner = await resolve_locale(interaction)
                        await interaction.response.send_message(
                            get_string("moderation.errors.generic", lang_inner, error=str(e)),
                            ephemeral=True
                        )

                btn.callback = btn_callback
                
                container_children.append(ui.Section(
                    ui.TextDisplay(content=get_string(feat["title_key"], lang)),
                    accessory=btn
                ))
                
                img_val = self.cog.emojis.get(feat["emoji_key"], "")
                if img_val.endswith(".png"):
                    base_path = Path(__file__).parent.parent
                    img_path = base_path / "moderation-icons" / img_val
                    if img_path.exists():
                        filename = f"thumb_{feat['id']}.png"
                        self.files.append(discord.File(str(img_path), filename=filename))
                        accessory = ui.Thumbnail(f"attachment://{filename}")
                    else:
                        accessory = ui.Button(label="?", style=discord.ButtonStyle.gray, disabled=True)
                elif img_val.startswith("<"):
                    accessory = ui.Button(emoji=img_val, style=discord.ButtonStyle.gray, disabled=True)
                else:
                    accessory = ui.Thumbnail(img_val) if img_val.startswith("http") else ui.Button(label="?", style=discord.ButtonStyle.gray, disabled=True)
                    
                container_children.append(ui.Section(
                    ui.TextDisplay(content=get_string(feat["desc_key"], lang)),
                    accessory=accessory
                ))

            container_children.append(ui.Separator(visible=True))
            
            prev_btn = ui.Button(label=get_string("moderation.menu.previous", lang), style=discord.ButtonStyle.gray, disabled=(self.page <= 0))
            next_btn = ui.Button(label=get_string("moderation.menu.next", lang), style=discord.ButtonStyle.gray, disabled=(self.page >= self.total_pages - 1))
            
            async def prev_callback(interaction):
                try:
                    self.page -= 1
                    await self.build()
                    await interaction.response.edit_message(view=self, attachments=self.files)
                except Exception as e:
                    lang_inner = await resolve_locale(interaction)
                    await interaction.response.send_message(
                        get_string("moderation.errors.generic", lang_inner, error=str(e)),
                        ephemeral=True
                    )
                
            async def next_callback(interaction):
                try:
                    self.page += 1
                    await self.build()
                    await interaction.response.edit_message(view=self, attachments=self.files)
                except Exception as e:
                    lang_inner = await resolve_locale(interaction)
                    await interaction.response.send_message(
                        get_string("moderation.errors.generic", lang_inner, error=str(e)),
                        ephemeral=True
                    )
                
            prev_btn.callback = prev_callback
            next_btn.callback = next_callback
            
            container_children.append(ui.ActionRow(prev_btn, next_btn))
            
            container = ui.Container(*container_children, accent_colour=discord.Colour.blue())
            self.add_item(container)
        except Exception as e:
            traceback.print_exc()

class ModerationSuccessView(ui.LayoutView):
    def __init__(self, cog, emoji, action_text_key, user, clean_reason, initiator, attempt=1, button_label=None, button_emoji=None, lang="en"):
        super().__init__(timeout=None)
        self.initiator = initiator
        
        action_text = get_string(f"moderation.actions.{action_text_key}", lang)
        title = get_string("moderation.success.title", lang, emoji=emoji, action_text=action_text)
        if attempt > 1:
            title += f" (Attempt {attempt})"

        container_items = [
            ui.TextDisplay(content=title),
            ui.Section(
                ui.TextDisplay(content=get_string("moderation.success.description", lang, user_name=user.display_name, action_text=action_text, reason=clean_reason, initiator_name=initiator.display_name)),
                accessory=ui.Thumbnail(user.display_avatar.url)
            )
        ]

        if button_label:
            container_items.append(ui.Separator(visible=True))
            
            btn = ui.Button(label=button_label, style=discord.ButtonStyle.gray, emoji=button_emoji)
            async def btn_callback(interaction):
                if button_label == "Unban":
                    await cog.perform_unban(interaction, user, "Action reversed via button", edit=True)
                elif button_label == "Remove Timeout":
                    await cog.perform_untimeout(interaction, user, "Action reversed via button", edit=True)
            btn.callback = btn_callback

            container_items.append(ui.Section(
                ui.TextDisplay(content=get_string("moderation.success.reverse_tip", lang)),
                accessory=btn
            ))

        container = ui.Container(*container_items, accent_colour=discord.Colour.red() if "ban" in action_text_key or "kick" in action_text_key else discord.Colour.orange())
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        return True

class ModerationErrorView(ui.LayoutView):
    def __init__(self, cog, emoji, action_type, user, error_msg, initiator, attempt=1, reason=None, extra_data=None, lang="en"):
        super().__init__(timeout=None)
        self.initiator = initiator
        
        title = get_string("moderation.error.title", lang, emoji=emoji)
        if attempt > 1:
            title += f" (Attempt {attempt})"

        action_type_text = get_string(f"moderation.actions.{action_type}", lang)
        container = ui.Container(
            ui.TextDisplay(content=title),
            ui.TextDisplay(content=get_string("moderation.error.description", lang, action_type=action_type_text, user_name=user.display_name, error_msg=error_msg)),
            accent_colour=discord.Colour.orange()
        )
        self.add_item(container)
        
        row = ui.ActionRow()
        
        retry_btn = ui.Button(label=get_string("moderation.error.retry", lang), style=discord.ButtonStyle.gray, emoji=cog.emojis.get(action_type))
        async def retry_callback(interaction):
            if action_type == "ban":
                await cog.perform_ban(interaction, user, reason, extra_data, attempt + 1, edit=True)
            elif action_type == "softban":
                await cog.perform_softban(interaction, user, reason, extra_data, attempt + 1, edit=True)
            elif action_type == "kick":
                await cog.perform_kick(interaction, user, reason, attempt + 1, edit=True)
            elif action_type == "timeout":
                await cog.perform_timeout(interaction, user, extra_data, reason, attempt + 1, edit=True)
            elif action_type == "unban":
                await cog.perform_unban(interaction, user, reason, attempt + 1, edit=True)
        retry_btn.callback = retry_callback
        row.add_item(retry_btn)

        if action_type != "ban":
            ban_btn = ui.Button(label=get_string("moderation.error.ban_instead", lang), style=discord.ButtonStyle.gray, emoji=cog.emojis.get("ban"))
            async def ban_callback(interaction):
                await cog.perform_ban(interaction, user, reason, "0", 1, edit=True)
            ban_btn.callback = ban_callback
            row.add_item(ban_btn)

        if action_type != "kick":
            kick_btn = ui.Button(label=get_string("moderation.error.kick_instead", lang), style=discord.ButtonStyle.gray, emoji=cog.emojis.get("kick"))
            async def kick_callback(interaction):
                await cog.perform_kick(interaction, user, reason, 1, edit=True)
            kick_btn.callback = kick_callback
            row.add_item(kick_btn)

        if action_type != "timeout":
            timeout_btn = ui.Button(label=get_string("moderation.error.timeout_instead", lang), style=discord.ButtonStyle.gray, emoji=cog.emojis.get("timeout"))
            async def timeout_callback(interaction):
                await cog.perform_timeout(interaction, user, 3600, reason, 1, edit=True)
            timeout_btn.callback = timeout_callback
            row.add_item(timeout_btn)

        self.add_item(row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        return True

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emojis = self._load_emojis()

    class MockInteraction:
        def __init__(self, message, bot):
            self.guild = message.guild
            self.user = message.author
            self.channel = message.channel
            self.bot = bot
            self.message = None
            self.response = self.MockResponse(self)
            self.followup = self.MockFollowup(self)
            self.type = discord.InteractionType.application_command
            
        async def edit_original_response(self, **kwargs):
            if "ephemeral" in kwargs: del kwargs["ephemeral"]
            if self.message:
                await self.message.edit(**kwargs)
            else:
                self.message = await self.channel.send(**kwargs)

        class MockResponse:
            def __init__(self, parent):
                self.parent = parent
            def is_done(self): return self.parent.message is not None
            async def defer(self, **kwargs): pass
            async def send_message(self, **kwargs):
                if "ephemeral" in kwargs: del kwargs["ephemeral"]
                self.parent.message = await self.parent.channel.send(**kwargs)
            async def edit_message(self, **kwargs):
                if self.parent.message:
                    await self.parent.message.edit(**kwargs)
                else:
                    self.parent.message = await self.parent.channel.send(**kwargs)

        class MockFollowup:
            def __init__(self, parent):
                self.parent = parent
            async def send(self, **kwargs):
                if "ephemeral" in kwargs: del kwargs["ephemeral"]
                self.parent.message = await self.parent.channel.send(**kwargs)

    async def do_mod_response(self, interaction, view, edit=False):
        kwargs = {"view": view, "allowed_mentions": discord.AllowedMentions.none()}
        if edit:
            if isinstance(interaction, discord.Interaction) and interaction.type == discord.InteractionType.component:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(**kwargs)
                else:
                    await interaction.edit_original_response(**kwargs)
            else:
                await interaction.edit_original_response(**kwargs)
        else:
            if isinstance(interaction, discord.Interaction) and not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            await interaction.followup.send(**kwargs)

    async def notify_user_moderation(self, interaction, user, action_type_key, reason, context_message=None):
        try:
            settings = await self.bot.server_settings.get_settings(interaction.guild.id)
            lang = settings.get("language", "en")
            custom_msg = settings.get("moderation_dm_message")

            action_type = get_string(f"moderation.actions.{action_type_key}", lang)
            server_name = interaction.guild.name
            moderator_name = interaction.user.display_name
            
            container_items = []
            
            if action_type_key == "unbanned":
                title = get_string("moderation.dm.unban_title", lang, server_name=server_name)
            else:
                title = get_string("moderation.dm.title", lang, action_type=action_type, server_name=server_name)
                
            container_items.append(ui.TextDisplay(content=title))

            if action_type_key != "unbanned":
                # Fetch last 10 messages from user in this channel
                last_messages = []
                try:
                    async for msg in interaction.channel.history(limit=100):
                        if msg.author.id == user.id:
                            content = msg.clean_content
                            if len(content) > 100: content = content[:97] + "..."
                            last_messages.append(f"[`{msg.created_at.strftime('%H:%M')}`] {content}")
                        if len(last_messages) >= 10:
                            break
                except:
                    pass

                if context_message:
                    ctx_content = context_message.clean_content
                    if len(ctx_content) > 100: ctx_content = ctx_content[:97] + "..."
                    container_items.append(ui.TextDisplay(content=get_string("moderation.dm.context_title", lang, action_type=action_type) + f"\n> {ctx_content}"))

                if last_messages:
                    history_text = get_string("moderation.dm.history_title", lang) + "\n" + "\n".join(reversed(last_messages))
                    container_items.append(ui.TextDisplay(content=history_text))

            container_items.append(ui.Separator(visible=True))
            
            details_text = get_string("moderation.dm.details", lang, reason=(reason or "No reason provided"), moderator_name=moderator_name)
            if custom_msg:
                details_text += f"\n\n{custom_msg}"

            container_items.append(ui.Section(
                ui.TextDisplay(content=details_text),
                accessory=ui.Thumbnail(interaction.guild.icon.url if interaction.guild.icon else interaction.user.display_avatar.url)
            ))

            view = ui.LayoutView()
            accent = discord.Colour.red() if action_type_key in ["kicked", "banned", "softbanned"] else discord.Colour.green()
            container = ui.Container(*container_items, accent_colour=accent)
            view.add_item(container)

            await user.send(view=view)
        except Exception as e:
            # We don't care if DM fails
            pass

    def _load_emojis(self):
        base_path = Path(__file__).parent.parent
        emoji_path = base_path / "moderation-icons" / "emojis.json"
        try:
            with open(emoji_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Moderation Log] Error loading emojis: {e}")
            return {}

    def sanitize(self, text):
        if not text:
            return "No reason provided"
        text = text.replace("\n", " ").replace("\r", "")
        return re.sub(r"([_*~\\`|])", r"\\\1", text)

    moderation_group = app_commands.Group(name="moderation", description="Moderation related commands")

    @moderation_group.command(name="settings", description="Open the moderation settings menu")
    async def moderation_settings(self, interaction: discord.Interaction):
        try:
            settings = await self.bot.server_settings.get_settings(interaction.guild.id)
            lang = settings.get("language", "en")
            
            is_enabled = True
            perms_obj = settings.get("permissions", {})
            if "moderation.settings_permissions" in perms_obj:
                is_enabled = perms_obj["moderation.settings_permissions"].get("enabled", True)
            elif "moderation.settings_enabled" in settings:
                is_enabled = settings["moderation.settings_enabled"]
                
            if not is_enabled:
                return await interaction.response.send_message(
                    get_string("errors.command_disabled", lang), 
                    ephemeral=True
                )

            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    get_string("errors.missing_permission", lang, permission="Manage Server"),
                    ephemeral=True
                )

            view = ModerationSettingsView(self, interaction.guild, interaction.user)
            await view.build()
            await interaction.response.send_message(view=view, ephemeral=True, files=view.files)
        except Exception as e:
            lang_inner = await resolve_locale(interaction)
            await interaction.response.send_message(
                get_string("moderation.errors.generic", lang_inner, error=str(e)),
                ephemeral=True
            )

    async def check_hierarchy(self, interaction, user, action_name):
        if not interaction.guild: return False, "This command can only be used in a server."
        
        # Fallback resolution if PrefixBridge failed to resolve a string
        if isinstance(user, str):
            try:
                import re
                uid_match = re.search(r'(\d{17,20})', user)
                if uid_match:
                    uid = int(uid_match.group(1))
                    resolved = interaction.guild.get_member(uid) or self.bot.get_user(uid)
                    if resolved:
                        user = resolved
            except: pass

        if isinstance(user, str):
            return False, f"Could not find user '{user}'. Please mention them or use their ID."

        if user.id == interaction.user.id: return False, f"You cannot {action_name} yourself."
        if user.id == self.bot.user.id: return False, f"I can't {action_name} myself!"
        if user.id == interaction.guild.owner_id: return False, f"You cannot {action_name} the server owner."
        
        if hasattr(user, "top_role"):
            if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
                return False, "Your highest role is not above the target user's, so you cannot moderate them."
            if user.top_role >= interaction.guild.me.top_role:
                return False, "The target user's highest role is equal to or higher than mine, so I cannot moderate them."
        
        return True, None

    @moderation_group.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="The user to ban", reason="Reason for the ban", delete_messages="How much of their message history to delete")
    @app_commands.choices(delete_messages=[
        app_commands.Choice(name="Don't delete any", value="0"),
        app_commands.Choice(name="Previous Hour", value="3600"),
        app_commands.Choice(name="Previous 6 hours", value="21600"),
        app_commands.Choice(name="Previous 12 hours", value="43200"),
        app_commands.Choice(name="Previous 24 hours", value="86400"),
        app_commands.Choice(name="Previous 3 days", value="259200"),
        app_commands.Choice(name="Previous 7 days", value="604800"),
    ])
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = None, delete_messages: str = "0"):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("ban_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        await self.perform_ban(interaction, user, reason, delete_messages)

    def _get_audit_reason(self, interaction, reason):
        suffix = f" | By {interaction.user.name}"
        max_reason_len = 512 - len(suffix)
        
        clean_reason = (reason or "No reason provided").replace("\n", " ").replace("\r", "")
        if len(clean_reason) > max_reason_len:
            clean_reason = clean_reason[:max_reason_len - 3] + "..."
            
        return f"{clean_reason}{suffix}"

    async def perform_ban(self, interaction, user, reason, delete_messages="0", attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)
        
        lang = await resolve_locale(interaction)
        allowed, error = await self.check_hierarchy(interaction, user, "ban")
        if not allowed: return await self.send_mod_error(interaction, "ban", user, error, attempt, reason, delete_messages, edit, lang=lang)
        
        if not interaction.user.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "ban", user, "You do not have the required permissions to execute this command (Ban Members).", attempt, reason, delete_messages, edit, lang=lang)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "ban", user, "I do not have the required permissions to execute this.", attempt, reason, delete_messages, edit, lang=lang)

        try:
            # Try to notify user first
            ctx_msg = None
            if hasattr(interaction, "message_ref"):
                ctx_msg = interaction.message_ref
            elif isinstance(interaction, self.MockInteraction) and hasattr(interaction, "orig_message") and interaction.orig_message.reference:
                ctx_msg = interaction.orig_message.reference.resolved

            await self.notify_user_moderation(interaction, user, "banned", reason, context_message=ctx_msg)

            audit_reason = self._get_audit_reason(interaction, reason)
            await interaction.guild.ban(user, reason=audit_reason, delete_message_seconds=int(delete_messages))
            view = ModerationSuccessView(self, self.emojis.get('ban', ''), "banned", user, self.sanitize(reason), interaction.user, attempt, "Unban", self.emojis.get('unban'), lang=lang)
            await self.do_mod_response(interaction, view, edit)
        except Exception as e:
            await self.send_mod_error(interaction, "ban", user, str(e), attempt, reason, delete_messages, edit, lang=lang)

    @moderation_group.command(name="softban", description="Ban and instantly unban a user to clear their messages")
    @app_commands.describe(user="The user to softban", reason="Reason for the softban", delete_messages="How much of their message history to delete")
    @app_commands.choices(delete_messages=[
        app_commands.Choice(name="Previous 24 hours", value="86400"),
        app_commands.Choice(name="Previous 7 days", value="604800"),
    ])
    async def softban(self, interaction: discord.Interaction, user: discord.Member, reason: str = None, delete_messages: str = "86400"):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("softban_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        await self.perform_softban(interaction, user, reason, delete_messages)

    async def perform_softban(self, interaction, user, reason, delete_messages="86400", attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)
        
        lang = await resolve_locale(interaction)
        allowed, error = await self.check_hierarchy(interaction, user, "softban")
        if not allowed: return await self.send_mod_error(interaction, "softban", user, error, attempt, reason, delete_messages, edit, lang=lang)
        
        if not interaction.user.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "softban", user, "You do not have the required permissions to execute this command (Ban Members).", attempt, reason, delete_messages, edit, lang=lang)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "softban", user, "I do not have the required permissions to execute this.", attempt, reason, delete_messages, edit, lang=lang)

        try:
            # Try to notify user first
            ctx_msg = None
            if hasattr(interaction, "message_ref"):
                ctx_msg = interaction.message_ref
            elif isinstance(interaction, self.MockInteraction) and hasattr(interaction, "orig_message") and interaction.orig_message.reference:
                ctx_msg = interaction.orig_message.reference.resolved

            await self.notify_user_moderation(interaction, user, "softbanned", reason, context_message=ctx_msg)

            audit_reason = self._get_audit_reason(interaction, reason)
            # Ban
            await interaction.guild.ban(user, reason=f"[SOFTBAN] {audit_reason}", delete_message_seconds=int(delete_messages))
            # Unban
            await interaction.guild.unban(user, reason=f"[SOFTBAN] Completed")
            
            view = ModerationSuccessView(self, self.emojis.get('ban', ''), "softbanned", user, self.sanitize(reason), interaction.user, attempt, lang=lang)
            await self.do_mod_response(interaction, view, edit)
            
            # Log softban specifically
            try:
                from moderation_logs.handlers.base import send_log_message
                await send_log_message(self.bot, interaction.guild.id, "softban", f"Member softbanned: {user.mention} (`{user.id}`)\nReason: **{reason or 'No reason provided'}**", accessory_img=user.display_avatar.url, action_by=interaction.user)
            except Exception as log_err:
                print(f"[Moderation] Error logging softban: {log_err}")
        except Exception as e:
            await self.send_mod_error(interaction, "softban", user, str(e), attempt, reason, delete_messages, edit, lang=lang)

    @moderation_group.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(username="The user to unban (autocomplete)", reason="Reason for the unban")
    async def unban(self, interaction: discord.Interaction, username: str, reason: str = None):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("unban_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        try:
            user_id = int(username)
            user = await self.bot.fetch_user(user_id)
        except ValueError:
            # Not an ID, try to find in bans
            bans = [entry async for entry in interaction.guild.bans()]
            choices = [(entry.user, fuzz.WRatio(username, entry.user.name)) for entry in bans]
            choices += [(entry.user, fuzz.WRatio(username, str(entry.user.id))) for entry in bans]
            
            if not choices:
                return await interaction.response.send_message("No banned users found.", ephemeral=True)
            
            best_match, score = max(choices, key=lambda x: x[1])
            if score < 50:
                return await interaction.response.send_message("Could not find a banned user with that name.", ephemeral=True)
            user = best_match

        await self.perform_unban(interaction, user, reason)

    @unban.autocomplete("username")
    async def unban_autocomplete(self, interaction: discord.Interaction, current: str):
        bans = [entry async for entry in interaction.guild.bans()]
        choices = []
        for entry in bans:
            choices.append((entry.user, fuzz.WRatio(current, entry.user.name)))
            choices.append((entry.user, fuzz.WRatio(current, str(entry.user.id))))
        
        # Sort and take top 25
        choices.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        final_choices = []
        for user, score in choices:
            if user.id not in seen:
                final_choices.append(app_commands.Choice(name=f"{user.name} ({user.id})", value=str(user.id)))
                seen.add(user.id)
            if len(final_choices) >= 25: break
            
        return final_choices

    async def perform_unban(self, interaction, user, reason, attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)

        lang = await resolve_locale(interaction)
        if not interaction.guild: return await self.send_mod_error(interaction, "unban", user, "This command can only be used in a server.", attempt, reason, edit=edit, lang=lang)
        
        if not interaction.user.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "unban", user, "You do not have the required permissions to execute this command (Ban Members).", attempt, reason, edit=edit, lang=lang)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await self.send_mod_error(interaction, "unban", user, "I do not have the required permissions to execute this.", attempt, reason, edit=edit, lang=lang)

        try:
            # Try to notify user first
            ctx_msg = None
            if hasattr(interaction, "message_ref"):
                ctx_msg = interaction.message_ref
            elif isinstance(interaction, self.MockInteraction) and hasattr(interaction, "orig_message") and interaction.orig_message.reference:
                ctx_msg = interaction.orig_message.reference.resolved

            await self.notify_user_moderation(interaction, user, "unbanned", reason, context_message=ctx_msg)

            audit_reason = self._get_audit_reason(interaction, reason)
            await interaction.guild.unban(user, reason=audit_reason)
            view = ModerationSuccessView(self, self.emojis.get('unban', ''), "unbanned", user, self.sanitize(reason), interaction.user, attempt, lang=lang)
            await self.do_mod_response(interaction, view, edit)
        except discord.NotFound:
            await self.send_mod_error(interaction, "unban", user, "That user is not banned.", attempt, reason, edit=edit, lang=lang)
        except Exception as e:
            await self.send_mod_error(interaction, "unban", user, str(e), attempt, reason, edit=edit, lang=lang)

    @moderation_group.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(user="The user to kick", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("kick_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        await self.perform_kick(interaction, user, reason)

    async def perform_kick(self, interaction, user, reason, attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)
        
        lang = await resolve_locale(interaction)
        allowed, error = await self.check_hierarchy(interaction, user, "kick")
        if not allowed: return await self.send_mod_error(interaction, "kick", user, error, attempt, reason, edit=edit, lang=lang)
        
        if not interaction.user.guild_permissions.kick_members:
            return await self.send_mod_error(interaction, "kick", user, "You do not have the required permissions to execute this command (Kick Members).", attempt, reason, edit=edit, lang=lang)

        if not interaction.guild.me.guild_permissions.kick_members:
            return await self.send_mod_error(interaction, "kick", user, "I do not have the required permissions to execute this.", attempt, reason, edit=edit, lang=lang)

        try:
            # Try to notify user first
            ctx_msg = None
            if hasattr(interaction, "message_ref"):
                ctx_msg = interaction.message_ref
            elif isinstance(interaction, self.MockInteraction) and hasattr(interaction, "orig_message") and interaction.orig_message.reference:
                ctx_msg = interaction.orig_message.reference.resolved

            await self.notify_user_moderation(interaction, user, "kicked", reason, context_message=ctx_msg)

            audit_reason = self._get_audit_reason(interaction, reason)
            await interaction.guild.kick(user, reason=audit_reason)
            view = ModerationSuccessView(self, self.emojis.get('kick', ''), "kicked", user, self.sanitize(reason), interaction.user, attempt, lang=lang)
            await self.do_mod_response(interaction, view, edit)
        except Exception as e:
            await self.send_mod_error(interaction, "kick", user, str(e), attempt, reason, edit=edit, lang=lang)

    @moderation_group.command(name="timeout", description="Timeout a user in the server")
    @app_commands.describe(user="The user to timeout", duration="Duration of the timeout", reason="Reason for the timeout")
    @app_commands.choices(duration=[
        app_commands.Choice(name="60 seconds", value=60),
        app_commands.Choice(name="5 minutes", value=300),
        app_commands.Choice(name="10 minutes", value=600),
        app_commands.Choice(name="1 hour", value=3600),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="1 week", value=604800),
    ])
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = None):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("timeout_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        await self.perform_timeout(interaction, user, duration, reason)

    async def perform_timeout(self, interaction, user, duration=3600, reason=None, attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)
        
        lang = await resolve_locale(interaction)
        allowed, error = await self.check_hierarchy(interaction, user, "timeout")
        if not allowed: return await self.send_mod_error(interaction, "timeout", user, error, attempt, reason, duration, edit, lang=lang)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await self.send_mod_error(interaction, "timeout", user, "You do not have the required permissions to execute this command (Moderate Members).", attempt, reason, duration, edit, lang=lang)

        if not interaction.guild.me.guild_permissions.moderate_members:
            return await self.send_mod_error(interaction, "timeout", user, "I do not have the required permissions to execute this.", attempt, reason, duration, edit, lang=lang)

        try:
            audit_reason = self._get_audit_reason(interaction, reason)
            until = utcnow() + timedelta(seconds=duration)
            await user.timeout(until, reason=audit_reason)
            view = ModerationSuccessView(self, self.emojis.get('timeout', ''), "timed_out", user, self.sanitize(reason), interaction.user, attempt, "Remove Timeout", self.emojis.get('timeout'), lang=lang)
            await self.do_mod_response(interaction, view, edit)
        except Exception as e:
            await self.send_mod_error(interaction, "timeout", user, str(e), attempt, reason, duration, edit, lang=lang)

    @moderation_group.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(user="The user to untimeout", reason="Reason for removing timeout")
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        settings = await self.bot.server_settings.get_settings(interaction.guild.id)
        if not settings.get("untimeout_enabled", True):
            return await interaction.response.send_message(get_string("errors.command_disabled", settings.get("language", "en")), ephemeral=True)
        await self.perform_untimeout(interaction, user, reason)

    async def perform_untimeout(self, interaction, user, reason, attempt=1, edit=False):
        if not edit: await interaction.response.defer(ephemeral=False)

        lang = await resolve_locale(interaction)
        if not interaction.guild: return await self.send_mod_error(interaction, "untimeout", user, "This command can only be used in a server.", attempt, reason, edit=edit, lang=lang)
        
        allowed, error = await self.check_hierarchy(interaction, user, "untimeout")
        if not allowed: return await self.send_mod_error(interaction, "untimeout", user, error, attempt, reason, edit=edit, lang=lang)

        if not interaction.user.guild_permissions.moderate_members:
            return await self.send_mod_error(interaction, "untimeout", user, "You do not have the required permissions to execute this command (Moderate Members).", attempt, reason, edit=edit, lang=lang)

        if not interaction.guild.me.guild_permissions.moderate_members:
            return await self.send_mod_error(interaction, "untimeout", user, "I do not have the required permissions to execute this.", attempt, reason, edit=edit, lang=lang)

        try:
            audit_reason = self._get_audit_reason(interaction, reason)
            await user.timeout(None, reason=audit_reason)
            view = ModerationSuccessView(self, self.emojis.get('timeout', ''), "un_timed_out", user, self.sanitize(reason), interaction.user, attempt, lang=lang)
            await self.do_mod_response(interaction, view, edit)
        except Exception as e:
            await self.send_mod_error(interaction, "untimeout", user, str(e), attempt, reason, edit=edit, lang=lang)

    async def send_mod_error(self, interaction, action_type, user, error_msg, attempt, reason, extra_data=None, edit=False, lang="en"):
        view = ModerationErrorView(self, self.emojis.get('error', ''), action_type, user, error_msg, interaction.user, attempt, reason, extra_data, lang=lang)
        await self.do_mod_response(interaction, view, edit)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.bot.intents.message_content: return
        if message.author.bot or not message.guild: return
        
        try:
            settings = await self.bot.server_settings.get_settings(message.guild.id)
            if not settings.get("bot_enabled", True): return
            
            lang = settings.get("language", "en")
            prefix = settings.get("prefix", ",")
            
            if message.content.startswith(prefix):
                content = message.content[len(prefix):].strip()
                parts = content.split(" ", 1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # Shortcuts
                shortcuts = {
                    "to": "timeout",
                    "kk": "kick",
                    "uban": "unban",
                    "uto": "untimeout",
                    "sb": "softban"
                }
                if cmd in shortcuts:
                    cmd = shortcuts[cmd]

                # Check if cmd is a moderation command
                mod_cmds = ["ban", "unban", "kick", "timeout", "untimeout", "softban"]
                if cmd not in mod_cmds: return
                
                if not settings.get(f"{cmd}_enabled", True): return
                
                # Check permissions
                perms = message.author.guild_permissions
                if cmd == "ban" and not perms.ban_members: return
                if cmd == "softban" and not perms.ban_members: return
                if cmd == "unban" and not perms.ban_members: return
                if cmd == "kick" and not perms.kick_members: return
                if cmd in ["timeout", "untimeout"] and not perms.moderate_members: return
                
                target_user = None
                reason = ""
                duration = 3600 # Default for timeout
                
                # Reply support
                if message.reference:
                    ref = message.reference.resolved
                    if isinstance(ref, discord.Message):
                        target_user = ref.author
                        reason = args
                        
                        if cmd == "timeout" and args:
                            rem_parts = args.split()
                            for i, part in enumerate(rem_parts):
                                dur_seconds = self.parse_duration(part)
                                if dur_seconds:
                                    duration = dur_seconds
                                    reason = " ".join(rem_parts[:i] + rem_parts[i+1:])
                                    break
                
                if not target_user and args:
                    # Try to find user in args
                    arg_parts = args.split()
                    if not arg_parts: return
                    
                    user_str = arg_parts[0]
                    
                    # Check for mention
                    mention_match = re.match(r"<@!?(\d+)>", user_str)
                    if mention_match:
                        user_id = int(mention_match.group(1))
                        target_user = message.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                        remaining_args = " ".join(arg_parts[1:])
                    # Check for ID
                    elif user_str.isdigit() and len(user_str) >= 17:
                        user_id = int(user_str)
                        target_user = message.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                        remaining_args = " ".join(arg_parts[1:])
                    else:
                        # Fuzzy search needed
                        search_query = user_str
                        remaining_args = " ".join(arg_parts[1:])
                        
                        if cmd == "unban":
                            bans = [entry async for entry in message.guild.bans()]
                            choices = [entry.user for entry in bans]
                            results = process.extract(search_query, choices, processor=lambda x: f"{x.display_name} {x.name} {x.id}" if not isinstance(x, str) else x, scorer=fuzz.WRatio, limit=25)
                            results = [r for r in results if r[1] > 50]
                        else:
                            # HTTP search
                            data = await message.guild._state.http.request(
                                discord.http.Route("GET", "/guilds/{guild_id}/members/search", guild_id=message.guild.id),
                                params={"query": search_query, "limit": 25}
                            )
                            members = [discord.Member(data=d, guild=message.guild, state=message.guild._state) for d in data]
                            results = [(m, 100.0, 0) for m in members]
                        
                        if not results:
                            return await message.channel.send("No user found.")
                        
                        # Show dropdown
                        action_func = {
                            "ban": self.perform_ban,
                            "softban": self.perform_softban,
                            "unban": self.perform_unban,
                            "kick": self.perform_kick,
                            "timeout": self.perform_timeout,
                            "untimeout": self.perform_untimeout
                        }[cmd]
                        
                        # Parse duration for timeout if present in remaining_args
                        current_reason = remaining_args
                        current_duration = 3600
                        if cmd == "timeout" and remaining_args:
                            rem_parts = remaining_args.split()
                            for i, part in enumerate(rem_parts):
                                dur_seconds = self.parse_duration(part)
                                if dur_seconds:
                                    current_duration = dur_seconds
                                    current_reason = " ".join(rem_parts[:i] + rem_parts[i+1:])
                                    break
                        
                        view = FuzzyUserSelect(self, results, action_func, current_reason, current_duration if cmd == "timeout" else None, lang=lang, orig_message=message)
                        await message.channel.send(view=view)
                        return
                    
                    # If we have target_user, parse duration and reason from remaining_args
                    reason = remaining_args
                    if cmd == "timeout" and remaining_args:
                        rem_parts = remaining_args.split()
                        for i, part in enumerate(rem_parts):
                            dur_seconds = self.parse_duration(part)
                            if dur_seconds:
                                duration = dur_seconds
                                reason = " ".join(rem_parts[:i] + rem_parts[i+1:])
                                break

                if target_user:
                    mock_inter = self.MockInteraction(message, self.bot)
                    mock_inter.orig_message = message # Pass for context
                    if cmd == "ban": await self.perform_ban(mock_inter, target_user, reason, "0")
                    elif cmd == "softban": await self.perform_softban(mock_inter, target_user, reason, "86400")
                    elif cmd == "unban": await self.perform_unban(mock_inter, target_user, reason)
                    elif cmd == "kick": await self.perform_kick(mock_inter, target_user, reason)
                    elif cmd == "timeout": await self.perform_timeout(mock_inter, target_user, duration, reason)
                    elif cmd == "untimeout": await self.perform_untimeout(mock_inter, target_user, reason)

        except Exception as e:
            traceback.print_exc()

    def parse_duration(self, duration_str):
        if not duration_str: return None
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        match = re.match(r"^(\d+)([smhdw]?)$", duration_str.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2) or "s"
            return value * units[unit]
        return None

async def setup(bot):
    await bot.add_cog(Moderation(bot))
