# Nite Pebbles

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Nite Pebbles is the open-source extension library for NiteBot. It’s essentially the playground where we keep the fun commands, modular components, and those extra utilities that give the bot its personality.

---

## Developer Guide

If you're looking to build your own Pebble modules, here is the lowdown on how to hook into the core NiteBot systems.

### Persistence

NiteBot relies on a centralized `DBManager` (`core.db_manager`). It’s built to handle PostgreSQL connections, but it has a transparent JSON fallback just in case. 

#### 1. Global Data
Use `db.get_global_data` and `db.save_global_data` for data that applies to the whole bot, like a shared community goal or bot-wide settings.

```python
from core.db_manager import db

# Example: Tracking a community-wide snack fund
count = await db.get_global_data("total_cookies_donated") or 0

# You can also grab multiple values at once
data = await db.get_global_data(["total_cookies_donated", "is_event_active"])
total = data.get("total_cookies_donated", 0)
active = data.get("is_event_active", False)

# Save a single update
await db.save_global_data("total_cookies_donated", total + 1)

# Or update a batch of settings
await db.save_global_data({
    "total_cookies_donated": 500,
    "is_event_active": True
})
```

#### 2. User Info
Use `db.get_user_info` and `db.save_user_info` for tracking data tied to a specific Discord User ID. These methods merge data into a user's JSON blob so you don't accidentally wipe out their other stats.

```python
from core.db_manager import db
user_id = interaction.user.id

# Example: Pulling a user's mini-game stats
stats = await db.get_user_info(user_id, ["xp", "level"])
current_xp = stats.get("xp", 0)
current_lvl = stats.get("level", 1)

# Update a single field, like a custom title
await db.save_user_info(user_id, "title", "Pebble Master")

# Update multiple fields at once
await db.save_user_info(user_id, {
    "xp": current_xp + 50,
    "level": current_lvl
})
```

### Server Settings

Handling guild-specific preferences is pretty straightforward. Any value submitted is saved in cache and disk. Note that the **language** setting is now primarily handled per-user via `/language`, but the server setting still acts as a fallback.

```python
guild_id = interaction.guild.id

# Pull all settings for the server
settings = await self.bot.server_settings.get_settings(guild_id)
is_enabled = settings.get("my_feature_enabled", True)

# Update and save a setting
settings["my_feature_enabled"] = False
await self.bot.server_settings.update_settings(guild_id, settings)
```

### Localization (i18n)

Don't hardcode your strings. We want Nite to 'feel local' everywhere, so use the `locales` system. It supports English, German, and Polish, and automatically respects the user's personal language preference or their Discord client language.

#### The DRY Way (Recommended)
Use `get_localized` to automatically resolve the best language for the user and fetch the string in one go.

```python
from locales import get_localized

# Resolve and send localized message
message = await get_localized(interaction, "fun.choose.response", choice="Pizza")
await interaction.response.send_message(message)
```

#### Manual Way
If you need the language code for something else (like an AI prompt), use `resolve_locale`.

```python
from locales import resolve_locale, get_string

lang = await resolve_locale(interaction)
prompt = get_string("ai.system_prompt", lang)
```

> **Note**: Make sure your Pebble-specific keys are added to `nite-pebbles/locales/*.json`.
>
>  You might not know another used language. In that case, you are allowed to use AI. 

### UI Templates (Components V2)

To keep NiteBot looking clean, consistent, and native, we enforce strict usage of Discord Components V2 (`discord.ui.LayoutView`). **Do not use `discord.Embed`**! Instead, use the centralized `ui_templates` module.

The templates provide standardized `LayoutView` objects for various states, complete with consistent colors and emojis. They also support an optional `image_url` parameter and native subtext footers.

```python
from ui_templates import template

# 1. Success Message
view = template.success(
    title="Operation Successful",
    message="Your data was saved.",
    footer="Saved just now"
)

# 2. Error Message (with optional try_again callback)
async def on_retry(interaction):
    await interaction.response.send_message("Retrying...")

view = template.error(
    title="Failed to Save",
    message="Database connection lost.",
    try_again_callback=on_retry
)

# 3. Warning Message
view = template.warning("Storage Low", "You have used 95% of your quota.")

# 4. Standard Message (supports an image_url which displays natively as an accessory)
view = template.message(
    title="Daily Report",
    message="Here is your stats summary.",
    image_url="https://mingalabs.com/assets/Nite%20bot/banner2.png"
)

# 5. Loading State
view = template.loading(estimated_time="~5s", footer="Fetching data")

# Need to add your own custom buttons? 
# Since templates return a standard LayoutView, you can append items directly!
view.add_item(my_custom_action_row)

await interaction.response.send_message(view=view)
```

### Image Rendering

If you need to render a specific image using HTML and CSS, you can convert your code into a PNG using the built-in browser renderer. Rendering can take a while, like ~1-2 seconds for small templates.

```python
from image_renderer import html_to_png
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import io
import discord

# Load your HTML template
env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))
template = env.get_template("card_template.html")

# Render and convert to PNG
html_content = template.render(user_name="PebbleDev", score=100)
img_bytes = await html_to_png(html_content, width=800, height=400, selector=".profile-card")

await interaction.followup.send(
    file=discord.File(io.BytesIO(img_bytes), filename="profile.png")
)
```

### Dashboard Integration

If your pebble offers server configurations or interactive management menus, you can hook your sub-menu directly into Nite's main `/dashboard`.

#### 1. Create your Sub-Dashboard View (`LayoutView`)
Use Discord Components V2 with a dynamic `build()` lifecycle:

```python
import discord
from discord import ui
from locales import get_string

class MyFeatureDashboardView(ui.LayoutView):
    def __init__(self, bot, server_settings, guild, user):
        super().__init__(timeout=None)
        self.bot = bot
        self.server_settings = server_settings
        self.guild = guild
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Enforce user matching and permission checks
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return False
        return True

    async def build(self):
        self.clear_items()
        
        # 1. Fetch current guild settings
        settings = await self.server_settings.get_settings(self.guild.id)
        config = settings.get("my_feature", {})
        enabled = config.get("enabled", False)
        lang = settings.get("language", "en")

        # 2. Header Container
        header_children = [
            ui.TextDisplay(content=f"# {get_string('my_feature.dashboard.title', lang)}"),
            ui.Separator(visible=True),
            ui.TextDisplay(content=f"Status: **{'Enabled' if enabled else 'Disabled'}**")
        ]
        self.add_item(ui.Container(
            *header_children,
            accent_colour=discord.Color.green() if enabled else discord.Color.red()
        ))

        # 3. Action Buttons
        toggle_btn = ui.Button(
            label="Disable" if enabled else "Enable",
            style=discord.ButtonStyle.danger if enabled else discord.ButtonStyle.success
        )
        async def toggle_callback(interaction: discord.Interaction):
            config["enabled"] = not enabled
            settings["my_feature"] = config
            await self.server_settings.update_settings(self.guild.id, settings)
            
            # Rebuild and edit
            await self.build()
            await interaction.response.edit_message(view=self)
            
        toggle_btn.callback = toggle_callback

        # 4. Back Button to return to main dashboard
        back_btn = ui.Button(label="Back", style=discord.ButtonStyle.secondary)
        async def back_callback(interaction: discord.Interaction):
            from dashboard import updateDashboard
            await interaction.response.defer()
            await updateDashboard(interaction.message, self.server_settings, self.bot)
            
        back_btn.callback = back_callback

        self.add_item(ui.ActionRow(toggle_btn, back_btn))
```

#### 2. Create and Register the Launcher Button
Create a `ui.Button` matching the `(bot_instance, server_settings, lang="en")` signature and call `register_dashboard_button`:

```python
from pebble_utils import register_dashboard_button
from discord import ui
import discord

class MyFeatureDashButton(ui.Button):
    def __init__(self, bot_instance, server_settings, lang="en"):
        super().__init__(
            label="My Feature",
            style=discord.ButtonStyle.secondary,
            custom_id="my_feature_dash_btn"
        )
        self.bot = bot_instance
        self.server_settings = server_settings
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Missing Manage Server permissions.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        view = MyFeatureDashboardView(self.bot, self.server_settings, interaction.guild, interaction.user)
        await view.build()
        await interaction.followup.send(view=view, ephemeral=True)

# Register into the main /dashboard view
register_dashboard_button(MyFeatureDashButton)
```

> **Note**: Importing the UI file in your extension's `setup` or main file ensures it is registered when Nite loads your pebble.

### Creating & Registering a Pebble

Pebbles are regular discord.py extensions. This means they should be structured as a standard Cog with a `setup` function.

#### 1. Create your Pebble File
Create a new file in `nite-pebbles/`, for example `my_extension.py`:

```python
from discord.ext import commands
from discord import app_commands

class MyExtension(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping_pebble", description="A simple pebble command")
    async def ping_pebble(self, interaction):
        await interaction.response.send_message("Pebble Pong!")

async def setup(bot):
    await bot.add_cog(MyExtension(bot))
```

#### 2. Register it in `pebbles.json`
To make NiteBot load your extension on startup, add it to the `entries` list in `nite-pebbles/pebbles.json`. You can also specify any pip dependencies your pebble needs; NiteBot will install them automatically if they are missing.

```json
{
  "entries": [
    {
      "extension_file": "my_extension",
      "name": "My Pebble Name",
      "description": "A short summary of what this pebble does.",
      "dependencies": ["some-pip-package"],
      "credits": {
        "Creators": [
          { 
            "name": "Your Name", 
            "contributions": "Initial creation",
            "github": "your_github_username",
            "discord": "your_discord_id",
            "custom": "Your custom status"
          }
        ],
        "Contributers": []
      }
    }
  ]
}
```

## Pebble Credits

Nite Pebbles tracks contributions at a modular level. Every contributor is recognized for their specific work, which is visible in Discord via the `/help -> Credits` menu.

To add or update credits, edit the `credits` object within `pebbles.json`. It supports:
- **Creators**: Those who designed the initial logic and architecture.
- **Contributers**: Those who added features, fixed bugs, or improved the UI.

Each entry must include a `name` and a short summary of the `contributions`.

---

## Testing Your Pebble

Since NiteBot's core is closed-source, there's a **Testing Shim** that lets you run your Pebbles locally with a mock environment.

### 1. Setup
1. Navigate to the `testing/` directory.
2. Create a `.env` file (copy `.env.example`).
3. Add your own Discord Bot Token to the `.env`.

### 2. Run the Test Bot
```bash
cd testing
python test_bot.py
```

### 3. Loading your Pebble
Once the bot is online, use the prefix command in Discord to load your extension:
`!load your_pebble_filename` (e.g., `!load fun_commands`)

The test bot will automatically:
- Use a local `test_db.json` for database calls.
- Use local settings files in `test_settings/`.
- Use the actual `locales/*.json` files for translation testing.

---

While Nite Pebbles are open-source, it does rely on some closed-source components. 

Anything unclear? Open an issue or DM me on Discord (DMs open): @interlastical

> If your pebble or edit needs a custom emoji, DM me on Discord, I'll add it and give you the ID.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)** — see the [LICENSE](LICENSE) file for details.
