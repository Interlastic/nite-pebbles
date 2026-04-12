# nite-pebbles/testing/test_bot.py
import discord
from discord.ext import commands
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 1. Add 'mocks' directory to sys.path
# This makes 'from core import db_manager' import our mock version
mocks_path = Path(__file__).parent / "mocks"
sys.path.append(str(mocks_path))

# 2. Add nite-pebbles root to sys.path so 'fun_commands' can be imported
pebbles_root = Path(__file__).parent.parent
sys.path.append(str(pebbles_root))

load_dotenv()

# 3. Setup Bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 4. Inject Mock Server Settings so self.bot.server_settings works
from core.server_settings import server_settings
bot.server_settings = server_settings

@bot.event
async def on_ready():
    print("-" * 30)
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Mocks loaded from: {mocks_path}")
    print("-" * 30)
    
    # You can manually load your extension here for testing
    # await bot.load_extension("fun_commands")
    print("Use '!load <name>' in Discord to load your pebble (e.g., !load fun_commands)")

@bot.command()
@commands.is_owner()
async def load(ctx, extension: str):
    """Loads a pebble for testing."""
    try:
        await bot.load_extension(extension)
        await ctx.send(f"✅ Loaded {extension}, please reload Discord (CTRL+R on Desktop) if you've added any / commands")
        await bot.tree.sync()
    except Exception as e:
        await ctx.send(f"❌ Failed to load {extension}: {e}")
        import traceback
        traceback.print_exc()

@bot.command()
@commands.is_owner()
async def reload(ctx, extension: str):
    """Reloads a pebble."""
    try:
        await bot.reload_extension(extension)
        await ctx.send(f"✅ Reloaded {extension}")
        await bot.tree.sync()
    except Exception as e:
        await ctx.send(f"❌ Failed to reload {extension}: {e}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN not found in .env file!")
        sys.exit(1)
    
    async def main():
        async with bot:
            try:
                await bot.start(token)
            except discord.LoginFailure:
                print("-" * 30)
                print("ERROR: Improper token has been passed.")
                print("If you haven't created a bot application yet:")
                print("1. Go to https://discord.com/developers/applications")
                print("2. Create a 'New Application' and go to the 'Bot' tab.")
                print("3. Reset/Copy your 'Token' and paste it into your .env file.")
                print("-" * 30)
                sys.exit(1)
            except discord.PrivilegedIntentsRequired:
                print("-" * 30)
                print("ERROR: You have not turned on all the required Privileged Intents.")
                print("Please navigate to https://discord.com/developers/applications,")
                print("press on your bot, and turn on all Privileged Intents in the Bot Tab.")
                print("-" * 30)
                sys.exit(1)
            except Exception as e:
                print(f"ERROR: {e}")
                sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
