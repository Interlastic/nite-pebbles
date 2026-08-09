import discord
from discord import ui
from locales import get_string, resolve_locale
from enum import IntFlag
import traceback

class LoggingFlags(IntFlag):
    MESSAGE_CREATE = 1 << 0
    MESSAGE_EDIT = 1 << 1
    MESSAGE_DELETE = 1 << 2
    BULK_DELETE = 1 << 3
    MESSAGE_PIN = 1 << 4
    REACTION_ADD = 1 << 5
    REACTION_REMOVE = 1 << 6
    POLL_VOTE = 1 << 7
    
    MEMBER_JOIN = 1 << 8
    MEMBER_LEAVE_KICK = 1 << 9
    MEMBER_BAN_UNBAN = 1 << 10
    MEMBER_UPDATE = 1 << 11
    MEMBER_JOIN_REQ = 1 << 12
    INVITE_ALL = 1 << 13
    
    CHANNEL_CREATE = 1 << 14
    CHANNEL_UPDATE = 1 << 15
    CHANNEL_DELETE = 1 << 16
    ROLE_CREATE = 1 << 17
    ROLE_UPDATE = 1 << 18
    ROLE_DELETE = 1 << 19
    THREAD_CREATE = 1 << 20
    THREAD_UPDATE = 1 << 21
    THREAD_DELETE = 1 << 22
    
    GUILD_UPDATE = 1 << 23
    WEBHOOK_UPDATE = 1 << 24
    INTEGRATION_ALL = 1 << 25
    
    EMOJI_ADD = 1 << 26
    EMOJI_UPDATE = 1 << 27
    EMOJI_REMOVE = 1 << 28
    STICKER_ADD = 1 << 29
    STICKER_UPDATE = 1 << 30
    STICKER_REMOVE = 1 << 31
    SOUND_ADD = 1 << 32
    SOUND_UPDATE = 1 << 33
    SOUND_REMOVE = 1 << 34
    
    SCHEDULED_EVENT_ALL = 1 << 35
    STAGE_INSTANCE_ALL = 1 << 36
    AUTOMOD_RULE_ALL = 1 << 37
    AUTO_MOD = 1 << 38
    
    VOICE_JOIN = 1 << 39
    VOICE_MOVE = 1 << 40
    VOICE_LEAVE = 1 << 41
    VOICE_STATE_ALL = 1 << 42
    VOICE_EFFECT = 1 << 43
    
    AUDIT_LOG = 1 << 44
    PRESENCE = 1 << 46
    TYPING = 1 << 47
    ENTITLEMENTS = 1 << 48
    SUBSCRIPTIONS = 1 << 49

PRESETS = {
    "essential": (LoggingFlags.MEMBER_JOIN | LoggingFlags.MEMBER_LEAVE_KICK | LoggingFlags.MEMBER_BAN_UNBAN | 
                  LoggingFlags.ROLE_CREATE | LoggingFlags.ROLE_UPDATE | LoggingFlags.ROLE_DELETE |
                  LoggingFlags.CHANNEL_CREATE | LoggingFlags.CHANNEL_UPDATE | LoggingFlags.CHANNEL_DELETE |
                  LoggingFlags.GUILD_UPDATE),
    "moderate": (LoggingFlags.MEMBER_JOIN | LoggingFlags.MEMBER_LEAVE_KICK | LoggingFlags.MEMBER_BAN_UNBAN | 
                 LoggingFlags.ROLE_CREATE | LoggingFlags.ROLE_UPDATE | LoggingFlags.ROLE_DELETE |
                 LoggingFlags.CHANNEL_CREATE | LoggingFlags.CHANNEL_UPDATE | LoggingFlags.CHANNEL_DELETE |
                 LoggingFlags.GUILD_UPDATE | LoggingFlags.MESSAGE_EDIT | LoggingFlags.MESSAGE_DELETE | 
                 LoggingFlags.BULK_DELETE | LoggingFlags.MESSAGE_PIN | LoggingFlags.THREAD_CREATE |
                 LoggingFlags.THREAD_UPDATE | LoggingFlags.THREAD_DELETE),
    "complete": (1 << 39) - 1,
    "everything": (1 << 50) - 1,
    "clear": 0
}

class PresetModal(ui.Modal):
    def __init__(self, parent_view, lang):
        super().__init__(title=get_string("moderation.logging.preset_modal_title", lang))
        self.parent_view = parent_view
        self.lang = lang
        
        try:
            self.add_item(ui.TextDisplay(content=get_string("moderation.logging.preset_modal_desc", lang)))
            
            self.select = ui.Select(
                placeholder=get_string("moderation.logging.preset_select_placeholder", lang),
                options=[
                    discord.SelectOption(label=get_string("moderation.logging.preset_essential", lang), value="essential"),
                    discord.SelectOption(label=get_string("moderation.logging.preset_moderate", lang), value="moderate"),
                    discord.SelectOption(label=get_string("moderation.logging.preset_complete", lang), value="complete"),
                    discord.SelectOption(label=get_string("moderation.logging.preset_everything", lang), value="everything"),
                    discord.SelectOption(label=get_string("moderation.logging.preset_clear", lang), value="clear"),
                ]
            )
            self.add_item(ui.Label(text=get_string("moderation.logging.preset_modal_title", lang), component=self.select))
        except Exception as e:
            print(f"[Moderation Logs] Preset Modal Init Error: {e}")
            traceback.print_exc()

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("You do not have the required permissions to perform this action (Manage Server).", ephemeral=True)

            if not self.select.values:
                return await interaction.response.defer()

            preset_key = self.select.values[0]
            self.parent_view.flags = PRESETS.get(preset_key, 0)
            settings = await self.parent_view.cog.bot.server_settings.get_settings(self.parent_view.guild.id)
            settings["logging_flags_bitfield"] = int(self.parent_view.flags)
            await self.parent_view.cog.bot.server_settings.update_settings(self.parent_view.guild.id, settings)
            await self.parent_view.build()
            try:
                await interaction.response.edit_message(view=self.parent_view)
            except discord.InteractionResponded:
                await interaction.followup.edit_message(message_id="@original", view=self.parent_view)
        except Exception as e:
            print(f"[Moderation Logs] Preset Submission Error: {e}")
            traceback.print_exc()
            try:
                msg = get_string("moderation.logging.preset_error", self.lang)
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
            except:
                pass

class LoggingConfigView(ui.LayoutView):
    def __init__(self, cog, guild, user, page=0):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild = guild
        self.user = user
        self.page = page
        self.flags = 0
        self.enabled = False
        self.exclude_stats = False
        self.channel_id = None
        
        self.pages = [
            ("cat_core", [
                ("cat_messages", [
                    ("msg_create", LoggingFlags.MESSAGE_CREATE),
                    ("msg_edit", LoggingFlags.MESSAGE_EDIT),
                    ("msg_delete", LoggingFlags.MESSAGE_DELETE),
                    ("bulk_delete", LoggingFlags.BULK_DELETE),
                    ("msg_pins", LoggingFlags.MESSAGE_PIN)
                ]),
                ("cat_messages_adv", [
                    ("reaction_add", LoggingFlags.REACTION_ADD),
                    ("reaction_remove", LoggingFlags.REACTION_REMOVE),
                    ("poll_vote", LoggingFlags.POLL_VOTE)
                ])
            ]),
            ("cat_members", [
                ("cat_members", [
                    ("mem_join", LoggingFlags.MEMBER_JOIN),
                    ("mem_leave", LoggingFlags.MEMBER_LEAVE_KICK),
                    ("mem_ban", LoggingFlags.MEMBER_BAN_UNBAN),
                    ("mem_update", LoggingFlags.MEMBER_UPDATE)
                ]),
                ("cat_members_adv", [
                    ("mem_join_req", LoggingFlags.MEMBER_JOIN_REQ),
                    ("invites", LoggingFlags.INVITE_ALL)
                ])
            ]),
            ("cat_structure", [
                ("cat_server", [
                    ("guild_update", LoggingFlags.GUILD_UPDATE),
                    ("role_create", LoggingFlags.ROLE_CREATE),
                    ("role_update", LoggingFlags.ROLE_UPDATE),
                    ("role_delete", LoggingFlags.ROLE_DELETE)
                ]),
                ("cat_structure_adv", [
                    ("chan_create", LoggingFlags.CHANNEL_CREATE),
                    ("chan_update", LoggingFlags.CHANNEL_UPDATE),
                    ("chan_delete", LoggingFlags.CHANNEL_DELETE),
                    ("thread_create", LoggingFlags.THREAD_CREATE),
                    ("thread_update", LoggingFlags.THREAD_UPDATE),
                    ("thread_delete", LoggingFlags.THREAD_DELETE)
                ])
            ]),
            ("cat_content", [
                ("cat_visuals", [
                    ("emoji_add", LoggingFlags.EMOJI_ADD),
                    ("emoji_update", LoggingFlags.EMOJI_UPDATE),
                    ("emoji_remove", LoggingFlags.EMOJI_REMOVE),
                    ("sticker_add", LoggingFlags.STICKER_ADD),
                    ("sticker_update", LoggingFlags.STICKER_UPDATE),
                    ("sticker_remove", LoggingFlags.STICKER_REMOVE)
                ]),
                ("cat_audio", [
                    ("sound_add", LoggingFlags.SOUND_ADD),
                    ("sound_update", LoggingFlags.SOUND_UPDATE),
                    ("sound_remove", LoggingFlags.SOUND_REMOVE)
                ]),
                ("cat_voice_adv", [
                    ("webhooks", LoggingFlags.WEBHOOK_UPDATE),
                    ("integrations", LoggingFlags.INTEGRATION_ALL),
                    ("events", LoggingFlags.SCHEDULED_EVENT_ALL),
                    ("stages", LoggingFlags.STAGE_INSTANCE_ALL),
                    ("auto_mod", LoggingFlags.AUTO_MOD),
                    ("automod_rules", LoggingFlags.AUTOMOD_RULE_ALL)
                ])
            ]),
            ("cat_technical", [
                ("cat_voice_adv", [
                    ("v_join", LoggingFlags.VOICE_JOIN),
                    ("v_move", LoggingFlags.VOICE_MOVE),
                    ("v_leave", LoggingFlags.VOICE_LEAVE),
                    ("v_state", LoggingFlags.VOICE_STATE_ALL),
                    ("voice_effect", LoggingFlags.VOICE_EFFECT)
                ]),
                ("cat_technical", [
                    ("audit_log", LoggingFlags.AUDIT_LOG),
                    ("presence", LoggingFlags.PRESENCE),
                    ("typing", LoggingFlags.TYPING)
                ]),
                ("cat_monetization", [
                    ("entitlements", LoggingFlags.ENTITLEMENTS),
                    ("subscriptions", LoggingFlags.SUBSCRIPTIONS)
                ])
            ])
        ]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You do not have the required permissions to use this (Manage Server).", ephemeral=True)
            return False
        return True

    async def build(self):
        try:
            self.clear_items()
            lang = await resolve_locale(self.user)
            settings = await self.cog.bot.server_settings.get_settings(self.guild.id)
            self.flags = settings.get("logging_flags_bitfield", 0)
            self.enabled = settings.get("logging_enabled", False)
            self.exclude_stats = settings.get("logging_exclude_nite_stats", False)
            self.channel_id = settings.get("logging_channel")

            container_children = [
                ui.TextDisplay(content=f"## {get_string('moderation.logging.header', lang)}")
            ]

            en_btn = ui.Button(
                label="ON" if self.enabled else "OFF",
                style=discord.ButtonStyle.success if self.enabled else discord.ButtonStyle.secondary
            )
            async def en_callback(interaction):
                try:
                    self.enabled = not self.enabled
                    settings["logging_enabled"] = self.enabled
                    await self.cog.bot.server_settings.update_settings(self.guild.id, settings)
                    await self.build()
                    await interaction.response.edit_message(view=self)
                except Exception as e:
                    print(f"[Moderation Logs] Enable Toggle Error: {e}")
                    traceback.print_exc()
            en_btn.callback = en_callback

            container_children.append(ui.Section(
                ui.TextDisplay(content=f"### {get_string('moderation.logging.enabled_label', lang)}"),
                accessory=en_btn
            ))

            exclude_stats_btn = ui.Button(
                label="ON" if self.exclude_stats else "OFF",
                style=discord.ButtonStyle.success if self.exclude_stats else discord.ButtonStyle.secondary
            )
            async def exclude_stats_callback(interaction):
                try:
                    self.exclude_stats = not self.exclude_stats
                    settings["logging_exclude_nite_stats"] = self.exclude_stats
                    await self.cog.bot.server_settings.update_settings(self.guild.id, settings)
                    await self.build()
                    await interaction.response.edit_message(view=self)
                except Exception as e:
                    print(f"[Moderation Logs] Exclude Stats Toggle Error: {e}")
                    traceback.print_exc()
            exclude_stats_btn.callback = exclude_stats_callback

            container_children.append(ui.Section(
                ui.TextDisplay(content=f"### {get_string('moderation.logging.exclude_stats_label', lang)}"),
                accessory=exclude_stats_btn
            ))

            container_children.append(ui.TextDisplay(content=f"### {get_string('moderation.logging.channel_label', lang)}"))
            chan_select = ui.ChannelSelect(placeholder=get_string("moderation.logging.channel_label", lang))
            if self.channel_id:
                chan_select.default_values = [discord.Object(id=int(self.channel_id))]
            async def chan_callback(interaction):
                try:
                    self.channel_id = chan_select.values[0].id
                    settings["logging_channel"] = self.channel_id
                    await self.cog.bot.server_settings.update_settings(self.guild.id, settings)
                    await interaction.response.defer()
                except Exception as e:
                    print(f"[Moderation Logs] Channel Select Error: {e}")
                    traceback.print_exc()
            chan_select.callback = chan_callback
            container_children.append(ui.ActionRow(chan_select))

            page_data = self.pages[self.page]
            container_children.append(ui.TextDisplay(content=f"# {get_string('moderation.logging.' + page_data[0], lang)}"))

            for cat_key, items in page_data[1]:
                container_children.append(ui.TextDisplay(content=f"### {get_string('moderation.logging.' + cat_key, lang)}"))
                sel = ui.Select(placeholder=get_string(f"moderation.logging.{cat_key}", lang), min_values=0, max_values=len(items))
                for opt_key, flag in items:
                    sel.add_option(label=get_string(f"moderation.logging.options.{opt_key}", lang), value=str(flag.value), default=bool(self.flags & flag))
                
                async def sel_callback(interaction, its=items, s=sel):
                    try:
                        for _, f in its:
                            self.flags &= ~f
                        for val in s.values:
                            self.flags |= int(val)
                        settings["logging_flags_bitfield"] = int(self.flags)
                        await self.cog.bot.server_settings.update_settings(self.guild.id, settings)
                        await self.build()
                        await interaction.response.edit_message(view=self)
                    except Exception as e:
                        print(f"[Moderation Logs] Category Select Error: {e}")
                        traceback.print_exc()
                sel.callback = sel_callback
                container_children.append(ui.ActionRow(sel))

            container_children.append(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large))
            page_text = get_string("moderation.logging.page_label", lang, current=self.page + 1, total=len(self.pages))
            container_children.append(ui.TextDisplay(content=f"-# {page_text}"))

            prev_btn = ui.Button(label=get_string("moderation.menu.previous", lang), disabled=(self.page <= 0))
            next_btn = ui.Button(label=get_string("moderation.menu.next", lang), disabled=(self.page >= len(self.pages) - 1))
            preset_btn = ui.Button(label=get_string("moderation.logging.preset_btn", lang), style=discord.ButtonStyle.blurple)

            async def prev_page(interaction):
                try:
                    self.page -= 1
                    await self.build()
                    await interaction.response.edit_message(view=self)
                except Exception as e:
                    print(f"[Moderation Logs] Pagination Error: {e}")
                    traceback.print_exc()

            async def next_page(interaction):
                try:
                    self.page += 1
                    await self.build()
                    await interaction.response.edit_message(view=self)
                except Exception as e:
                    print(f"[Moderation Logs] Pagination Error: {e}")
                    traceback.print_exc()

            async def preset_callback(interaction):
                try:
                    await interaction.response.send_modal(PresetModal(self, lang))
                except Exception as e:
                    print(f"[Moderation Logs] Open Preset Modal Error: {e}")
                    traceback.print_exc()

            prev_btn.callback = prev_page
            next_btn.callback = next_page
            preset_btn.callback = preset_callback

            container_children.append(ui.ActionRow(prev_btn, next_btn, preset_btn))

            container = ui.Container(*container_children, accent_colour=discord.Colour.blue())
            self.add_item(container)
        except Exception as e:
            print(f"[Moderation Logs] Build View Error: {e}")
            traceback.print_exc()
