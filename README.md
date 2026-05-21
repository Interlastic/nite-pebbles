# Nite Pebbles

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
