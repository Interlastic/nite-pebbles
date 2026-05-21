import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Literal, Optional
import random
import os
import aiohttp
import asyncio
import io
import json
import math
import pyfiglet
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from locales import get_string, get_list, resolve_locale, get_localized

# Local Pebble Utilities
from pebble_utils import make_loading_bar
from image_renderer import html_to_png

try:
    from PIL import Image, ImageOps, ImageEnhance
except ImportError:
    Image = None

# --- Persistence Helpers ---
DATA_DIR = Path(__file__).parent.parent 
PEBBLE_DIR = Path(__file__).parent
JOKE_STATS_FILE = DATA_DIR / "joke_stats.json"
RPS_STATS_FILE = DATA_DIR / "rps_stats.json"
FONTS_INDEX_FILE = PEBBLE_DIR / "ASCII" / "taag-fonts-indexed.json"


def load_joke_stats() -> dict:
    if JOKE_STATS_FILE.exists():
        try:
            with open(JOKE_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_joke_stats(data: dict):
    with open(JOKE_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_rps_stats() -> dict:
    if RPS_STATS_FILE.exists():
        try:
            with open(RPS_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_rps_stats(data: dict):
    with open(RPS_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# --- RPS Challenge Views ---
class RPSChallengeView(discord.ui.View):
    """View for accepting/declining RPS challenges."""

    def __init__(
        self, cog, challenger: discord.User, opponent: discord.User, lang: str = "en"
    ):
        super().__init__(timeout=60)
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_choice = None
        self.opponent_choice = None
        self.accepted = False
        self.lang = lang
        self._localize_buttons()

    def _localize_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "rps_accept":
                    item.label = get_string("ui.buttons.accept_challenge", self.lang)
                elif item.custom_id == "rps_decline":
                    item.label = get_string("ui.buttons.decline", self.lang)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only challenger and opponent can interact
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message(
                get_string("errors.not_in_game", self.lang), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Accept Challenge",
        style=discord.ButtonStyle.green,
        custom_id="rps_accept",
    )
    async def accept_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                get_string("errors.not_challenger", self.lang), ephemeral=True
            )
            return

        self.accepted = True
        # Replace with choice view
        choice_view = RPSChoiceView(self, self.lang)
        await interaction.response.edit_message(
            content=get_string("games.rps.battle_title", self.lang)
            + "\n"
            + get_string(
                "games.rps.battle_message",
                self.lang,
                challenger=self.challenger.mention,
                opponent=self.opponent.mention,
            ),
            view=choice_view,
        )

    @discord.ui.button(
        label="Decline", style=discord.ButtonStyle.red, custom_id="rps_decline"
    )
    async def decline_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                get_string("errors.not_challenger_decline", self.lang), ephemeral=True
            )
            return

        self.stop()
        await interaction.response.edit_message(
            content=get_string(
                "ui.status.challenge_declined",
                self.lang,
                user=self.opponent.display_name,
            ),
            view=None,
        )

    async def on_timeout(self):
        pass


class RPSChoiceView(discord.ui.View):
    """View for selecting RPS choice in multiplayer."""

    def __init__(self, parent_view: RPSChallengeView, lang: str = "en"):
        super().__init__(timeout=60)
        self.parent = parent_view
        self.choices = {}
        self.lang = lang
        self._localize_buttons()

    def _localize_buttons(self):
        label_map = {
            "rps_rock": "ui.buttons.rock",
            "rps_paper": "ui.buttons.paper",
            "rps_scissors": "ui.buttons.scissors",
        }
        for item in self.children:
            if hasattr(item, "custom_id") and item.custom_id in label_map:
                item.label = get_string(label_map[item.custom_id], self.lang)

    async def check_and_resolve(self, interaction: discord.Interaction):
        """Check if both players have chosen and resolve the game."""
        if len(self.choices) == 2:
            c1 = self.choices[self.parent.challenger.id]
            c2 = self.choices[self.parent.opponent.id]

            # Determine winner
            if c1 == c2:
                result = get_string("games.rps.tie", self.lang)
                winner = None
            elif (
                (c1 == "Rock" and c2 == "Scissors")
                or (c1 == "Paper" and c2 == "Rock")
                or (c1 == "Scissors" and c2 == "Paper")
            ):
                result = get_string(
                    "games.rps.winner",
                    self.lang,
                    user=self.parent.challenger.display_name,
                )
                winner = self.parent.challenger
                loser = self.parent.opponent
            else:
                result = get_string(
                    "games.rps.winner",
                    self.lang,
                    user=self.parent.opponent.display_name,
                )
                winner = self.parent.opponent
                loser = self.parent.challenger

            # Update stats if in a guild
            if interaction.guild and winner:
                self.parent.cog.update_rps_stats(
                    str(interaction.guild.id), str(winner.id), won=True
                )
                self.parent.cog.update_rps_stats(
                    str(interaction.guild.id), str(loser.id), won=False
                )

            view = RPSPlayAgainView(
                self.parent.cog, self.parent.challenger, self.parent.opponent, self.lang
            )
            await interaction.message.edit(
                content=get_string("games.rps.results_title", self.lang)
                + "\n"
                + get_string(
                    "games.rps.chose",
                    self.lang,
                    user=self.parent.challenger.mention,
                    choice=c1,
                )
                + "\n"
                + get_string(
                    "games.rps.chose",
                    self.lang,
                    user=self.parent.opponent.mention,
                    choice=c2,
                )
                + "\n\n"
                + result,
                view=view,
            )
            self.stop()

    @discord.ui.button(
        label="🪨 Rock", style=discord.ButtonStyle.secondary, custom_id="rps_rock"
    )
    async def rock_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, "Rock")

    @discord.ui.button(
        label="📄 Paper", style=discord.ButtonStyle.secondary, custom_id="rps_paper"
    )
    async def paper_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, "Paper")

    @discord.ui.button(
        label="✂️ Scissors",
        style=discord.ButtonStyle.secondary,
        custom_id="rps_scissors",
    )
    async def scissors_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, "Scissors")

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = interaction.user.id

        if user_id not in [self.parent.challenger.id, self.parent.opponent.id]:
            await interaction.response.send_message(
                get_string("errors.not_in_game", self.lang), ephemeral=True
            )
            return

        if user_id in self.choices:
            await interaction.response.send_message(
                get_string(
                    "errors.already_chose", self.lang, choice=self.choices[user_id]
                ),
                ephemeral=True,
            )
            return

        self.choices[user_id] = choice
        await interaction.response.send_message(
            get_string("ui.status.waiting_opponent", self.lang, choice=choice),
            ephemeral=True,
        )

        await self.check_and_resolve(interaction)


class RPSSingleChoiceView(discord.ui.View):
    """View for selecting RPS choice in single player (after 'Play Again')."""

    def __init__(self, cog, lang: str = "en"):
        super().__init__(timeout=60)
        self.cog = cog
        self.lang = lang
        self._localize_buttons()

    def _localize_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "rps_single_rock":
                    item.label = get_string("ui.buttons.rock", self.lang)
                elif item.custom_id == "rps_single_paper":
                    item.label = get_string("ui.buttons.paper", self.lang)
                elif item.custom_id == "rps_single_scissors":
                    item.label = get_string("ui.buttons.scissors", self.lang)

    @discord.ui.button(
        label="🪨 Rock",
        style=discord.ButtonStyle.secondary,
        custom_id="rps_single_rock",
    )
    async def rock_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.cog.resolve_single_rps(interaction, "Rock", self.lang)

    @discord.ui.button(
        label="📄 Paper",
        style=discord.ButtonStyle.secondary,
        custom_id="rps_single_paper",
    )
    async def paper_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.cog.resolve_single_rps(interaction, "Paper", self.lang)

    @discord.ui.button(
        label="✂️ Scissors",
        style=discord.ButtonStyle.secondary,
        custom_id="rps_single_scissors",
    )
    async def scissors_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.cog.resolve_single_rps(interaction, "Scissors", self.lang)


class RPSPlayAgainView(discord.ui.View):
    """View with a 'Play Again' button for RPS."""

    def __init__(self, cog, challenger, opponent=None, lang: str = "en"):
        super().__init__(timeout=60)
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent
        self.lang = lang
        self._localize_buttons()

    def _localize_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id") and item.custom_id == "rps_play_again":
                item.label = get_string("ui.buttons.play_again", self.lang)

    @discord.ui.button(
        label="🔄 Play Again",
        style=discord.ButtonStyle.blurple,
        custom_id="rps_play_again",
    )
    async def play_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Check if the user was part of the game
        if interaction.user.id != self.challenger.id and (
            self.opponent and interaction.user.id != self.opponent.id
        ):
            await interaction.response.send_message(
                get_string("errors.not_in_game_play_again", self.lang), ephemeral=True
            )
            return

        if self.opponent is None:
            # Single player - show selection view
            view = RPSSingleChoiceView(self.cog, self.lang)
            await interaction.response.send_message(
                get_string("ui.status.choose_move", self.lang),
                view=view,
                ephemeral=False,
            )
        else:
            # Multiplayer - start a new challenge
            new_challenger = interaction.user
            new_opponent = (
                self.opponent
                if interaction.user.id == self.challenger.id
                else self.challenger
            )

            view = RPSChallengeView(self.cog, new_challenger, new_opponent, self.lang)
            await interaction.response.send_message(
                get_string("games.rps.challenge_title", self.lang)
                + "\n"
                + get_string(
                    "games.rps.challenge_message",
                    self.lang,
                    challenger=new_challenger.mention,
                    opponent=new_opponent.mention,
                    opponent_name=new_opponent.display_name,
                ),
                view=view,
            )


# --- Joke View with Voting ---
class JokeView(discord.ui.View):
    def __init__(self, cog, joke_id: str, joke_text: str, lang: str = "en"):
        super().__init__(timeout=None)
        self.cog = cog
        self.joke_id = joke_id
        self.joke_text = joke_text
        self.lang = lang
        self.voted_users = set()  # Track who has voted on this instance
        self._localize_buttons()

    def _localize_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "joke_image":
                    item.label = get_string("ui.buttons.joke_image", self.lang)
                elif item.custom_id == "joke_another":
                    item.label = get_string("ui.buttons.joke_another", self.lang)

    @discord.ui.button(
        label="👍", style=discord.ButtonStyle.gray, custom_id="joke_upvote"
    )
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voted_users:
            await interaction.response.send_message(
                "You already voted on this joke!", ephemeral=True
            )
            return
        self.voted_users.add(interaction.user.id)
        self.cog.track_joke_vote(self.joke_id, self.joke_text, upvote=True)
        stats = self.cog.joke_stats.get(self.joke_id, {})
        await interaction.response.send_message(
            f"👍 Upvoted! This joke: {stats.get('upvotes', 0)} 👍 / {stats.get('downvotes', 0)} 👎",
            ephemeral=True,
        )

    @discord.ui.button(
        label="👎", style=discord.ButtonStyle.gray, custom_id="joke_downvote"
    )
    async def downvote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id in self.voted_users:
            await interaction.response.send_message(
                "You already voted on this joke!", ephemeral=True
            )
            return
        self.voted_users.add(interaction.user.id)
        self.cog.track_joke_vote(self.joke_id, self.joke_text, upvote=False)
        stats = self.cog.joke_stats.get(self.joke_id, {})
        await interaction.response.send_message(
            f"👎 Downvoted! This joke: {stats.get('upvotes', 0)} 👍 / {stats.get('downvotes', 0)} 👎",
            ephemeral=True,
        )

    @discord.ui.button(
        label="🖼️ Image", style=discord.ButtonStyle.gray, custom_id="joke_image"
    )
    async def get_image(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        await self.cog.get_joke_as_image(
            interaction, self.joke_id, self.joke_text, font="Pacifico"
        )

    @discord.ui.button(
        label="🔄 Another", style=discord.ButtonStyle.blurple, custom_id="joke_another"
    )
    async def get_another(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.cog.send_random_joke(interaction, edit_original=True)


class JokeImageView(discord.ui.View):
    def __init__(
        self,
        cog,
        joke_id: str,
        joke_text: str,
        current_font: str = "Pacifico",
        lang: str = "en",
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.joke_id = joke_id
        self.joke_text = joke_text
        self.current_font = current_font
        self.lang = lang
        self._update_button()

    def _update_button(self):
        for item in self.children:
            if hasattr(item, "custom_id") and item.custom_id == "joke_toggle_font":
                item.label = (
                    "Readable" if self.current_font == "Pacifico" else "Stylized"
                )

    @discord.ui.button(
        label="Readable", style=discord.ButtonStyle.gray, custom_id="joke_toggle_font"
    )
    async def toggle_font(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        new_font = "Inter" if self.current_font == "Pacifico" else "Pacifico"
        await self.cog.get_joke_as_image(
            interaction, self.joke_id, self.joke_text, font=new_font, edit_original=True
        )


class ASCIIView(ui.LayoutView):
    """View for displaying ASCII art using Components V2 TextDisplay."""

    def __init__(self, ascii_text: str):
        super().__init__()
        # Discord Components V2 allows up to 4k chars in TextDisplay
        self.add_item(ui.TextDisplay(content=f"```\n{ascii_text}```"))


# --- Main Cog ---
class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.joke_stats = load_joke_stats()
        self.rps_stats = load_rps_stats()
        self.all_fonts = []
        self._load_all_fonts()

    def _load_all_fonts(self):
        """Loads all fonts from TAAG fonts index file."""
        if FONTS_INDEX_FILE.exists():
            try:
                with open(FONTS_INDEX_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for category in data.get("byCategory", {}).values():
                        self.all_fonts.extend(category)
                # Remove duplicates and sort
                self.all_fonts = sorted(list(set(self.all_fonts)))
            except Exception as e:
                print(f"[Error] Failed to load fonts: {e}")
        
        if not self.all_fonts:
            # Fallback to pyfiglet's own fonts if file fails
            self.all_fonts = sorted(pyfiglet.FigletFont.getFonts())

    # --- Joke Helpers ---
    def track_joke_vote(self, joke_id: str, joke_text: str, upvote: bool):
        """Track a joke vote globally."""
        if joke_id not in self.joke_stats:
            self.joke_stats[joke_id] = {"text": joke_text, "upvotes": 0, "downvotes": 0}
        if upvote:
            self.joke_stats[joke_id]["upvotes"] += 1
        else:
            self.joke_stats[joke_id]["downvotes"] += 1
        save_joke_stats(self.joke_stats)

    async def get_joke_as_image(
        self,
        interaction: discord.Interaction,
        joke_id: str,
        joke_text: str = "",
        font: str = "Pacifico",
        edit_original: bool = False,
    ):
        """Renders the joke as an image using our custom browser renderer."""
        # Clean joke text (remove code blocks if present)
        clean_joke = (
            joke_text.strip("`").strip() if joke_text else f"Joke ID: {joke_id}"
        )

        # Correct path for nite-pebbles location - use our own templates folder
        template_dir = PEBBLE_DIR / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("joke_template.html")

        html_content = template.render(joke_text=clean_joke, font_family=font)

        try:
            # Generate Image using our custom html_to_png (Playwright)
            img_bytes = await html_to_png(html_content, width=800, height=400, selector=".joke-card")

            # Use specific view for font toggling
            view = JokeImageView(self, joke_id, joke_text, current_font=font)

            if edit_original:
                await interaction.edit_original_response(
                    attachments=[
                        discord.File(io.BytesIO(img_bytes), filename="joke.png")
                    ],
                    view=view,
                )
            else:
                await interaction.followup.send(
                    file=discord.File(io.BytesIO(img_bytes), filename="joke.png"),
                    view=view,
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.followup.send(
                f"Error rendering image: {e}", ephemeral=True
            )

    async def send_random_joke(
        self, interaction: discord.Interaction, edit_original: bool = False
    ):
        url = "https://icanhazdadjoke.com/"
        headers = {
            "Accept": "application/json",
            "User-Agent": "NiteBot/1.0 (https://nitebot.dev)",
        }

        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        joke_text = data.get("joke", "I couldn't find a joke :(")
                        joke_text = f"```{joke_text}```"
                        joke_id = data.get("id")

                        # Get language using bot.server_settings
                        lang = "en"
                        if interaction.guild:
                            lang = await resolve_locale(interaction)
                        else:
                            lang = str(interaction.locale).split("-")[0]
                            if lang not in ["en", "de"]:
                                lang = "en"

                        view = JokeView(self, joke_id, joke_text, lang=lang)

                        if edit_original:
                            await interaction.edit_original_response(
                                content=joke_text, view=view
                            )
                        else:
                            await interaction.followup.send(
                                content=joke_text, view=view
                            )
                    else:
                        await interaction.followup.send(
                            f"Failed to fetch joke (Status: {response.status})",
                            ephemeral=True,
                        )
        except Exception as e:
            await interaction.followup.send(f"Error fetching joke: {e}", ephemeral=True)

    # --- RPS Helpers ---
    def update_rps_stats(self, server_id: str, user_id: str, won: bool):
        """Update RPS statistics for a user."""
        if server_id not in self.rps_stats:
            self.rps_stats[server_id] = {}

        if user_id not in self.rps_stats[server_id]:
            self.rps_stats[server_id][user_id] = {
                "wins": 0,
                "losses": 0,
                "current_streak": 0,
                "best_streak": 0,
            }

        stats = self.rps_stats[server_id][user_id]

        if won:
            stats["wins"] += 1
            stats["current_streak"] += 1
            if stats["current_streak"] > stats["best_streak"]:
                stats["best_streak"] = stats["current_streak"]
        else:
            stats["losses"] += 1
            stats["current_streak"] = 0

        save_rps_stats(self.rps_stats)

    async def resolve_single_rps(
        self, interaction: discord.Interaction, choice: str, lang: str = "en"
    ):
        """Logic for resolving RPS vs bot."""
        bot_choice = random.choice(["Rock", "Paper", "Scissors"])

        if choice == bot_choice:
            result = get_string("games.rps.tie", lang)
            won = None
        elif (
            (choice == "Rock" and bot_choice == "Scissors")
            or (choice == "Paper" and bot_choice == "Rock")
            or (choice == "Scissors" and bot_choice == "Paper")
        ):
            result = get_string("games.rps.you_win", lang)
            won = True
        else:
            result = get_string("games.rps.bot_wins", lang)
            won = False

        # Update stats if in a guild
        if interaction.guild and won is not None:
            self.update_rps_stats(
                str(interaction.guild.id), str(interaction.user.id), won=won
            )

        view = RPSPlayAgainView(self, interaction.user, lang=lang)
        await interaction.response.send_message(
            get_string(
                "games.rps.your_choice",
                lang,
                choice=choice,
                bot_choice=bot_choice,
                result=result,
            ),
            view=view,
            ephemeral=False,
        )

    # --- Commands ---

    # Joke command group
    joke_group = app_commands.Group(name="joke", description="Dad joke commands")

    @joke_group.command(name="random", description="Get a random dad joke")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def joke_random(self, interaction: discord.Interaction):
        await self.send_random_joke(interaction)

    @joke_group.command(
        name="leaderboard", description="See the best rated jokes worldwide"
    )
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def joke_leaderboard(self, interaction: discord.Interaction):
        lang = await resolve_locale(interaction)

        if not self.joke_stats:
            await interaction.response.send_message(
                get_string("games.joke.no_jokes_voted", lang), ephemeral=True
            )
            return

        # Sort by score (upvotes - downvotes)
        sorted_jokes = sorted(
            self.joke_stats.items(),
            key=lambda x: x[1].get("upvotes", 0) - x[1].get("downvotes", 0),
            reverse=True,
        )[:10]

        embed = discord.Embed(
            title=get_string("games.joke.leaderboard_title", lang),
            color=discord.Color.gold(),
        )

        for i, (joke_id, data) in enumerate(sorted_jokes, 1):
            joke_preview = data["text"][:400]
            upvotes = data.get("upvotes", 0)
            downvotes = data.get("downvotes", 0)
            total_joke_votes = upvotes + downvotes
            score = upvotes - downvotes

            value_text = joke_preview
            if interaction.guild:  # Emojis break in DMs
                percentage = (
                    (upvotes / total_joke_votes) * 100 if total_joke_votes > 0 else 0
                )
                bar = make_loading_bar(percentage)
                value_text += f"\n{bar}"

            embed.add_field(
                name=f"#{i} • {upvotes} 👍 {downvotes} 👎 (Score: {score:+d})",
                value=value_text,
                inline=False,
            )

        total_votes = sum(
            j.get("upvotes", 0) + j.get("downvotes", 0)
            for j in self.joke_stats.values()
        )
        embed.set_footer(
            text=get_string("games.joke.leaderboard_footer", lang, total=total_votes)
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flip one or more coins!")
    @app_commands.describe(count="Number of coins to flip (1-20)")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def coinflip(self, interaction: discord.Interaction, count: int = 1):
        lang = await resolve_locale(interaction)

        if count < 1:
            await interaction.response.send_message(
                get_string("errors.min_coins", lang), ephemeral=True
            )
            return
        if count > 20:
            await interaction.response.send_message(
                get_string("errors.max_coins", lang), ephemeral=True
            )
            return

        results = [random.choice(["H", "T"]) for _ in range(count)]
        heads = results.count("H")
        tails = results.count("T")

        if count == 1:
            result_text = (
                get_string("games.coinflip.heads", lang)
                if results[0] == "H"
                else get_string("games.coinflip.tails", lang)
            )
            await interaction.response.send_message(
                f"🪙 **{result_text}**!", ephemeral=False
            )
        else:
            results_str = ", ".join(results)
            await interaction.response.send_message(
                get_string(
                    "games.coinflip.results",
                    lang,
                    results=results_str,
                    heads=heads,
                    tails=tails,
                ),
                ephemeral=False,
            )

    # RPS command group
    rps_group = app_commands.Group(
        name="rps", description="Rock Paper Scissors commands"
    )

    # Message command group
    message_group = app_commands.Group(
        name="message", description="Message editing commands"
    )

    @rps_group.command(
        name="play", description="Play Rock, Paper, Scissors against the bot"
    )
    @app_commands.describe(choice="Your move")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def rps_play(
        self,
        interaction: discord.Interaction,
        choice: Literal["Rock", "Paper", "Scissors"],
    ):
        lang = await resolve_locale(interaction)
        await self.resolve_single_rps(interaction, choice, lang)

    @rps_group.command(
        name="challenge", description="Challenge another user to Rock Paper Scissors"
    )
    @app_commands.describe(opponent="The user to challenge")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def rps_challenge(
        self, interaction: discord.Interaction, opponent: discord.User
    ):
        lang = await resolve_locale(interaction)

        if opponent.id == interaction.user.id:
            await interaction.response.send_message(
                get_string("errors.cant_challenge_self", lang), ephemeral=True
            )
            return

        if opponent.bot:
            await interaction.response.send_message(
                get_string("errors.cant_challenge_bot", lang), ephemeral=True
            )
            return

        view = RPSChallengeView(self, interaction.user, opponent, lang)
        await interaction.response.send_message(
            get_string("games.rps.challenge_title", lang)
            + "\n"
            + get_string(
                "games.rps.challenge_message",
                lang,
                challenger=interaction.user.mention,
                opponent=opponent.mention,
                opponent_name=opponent.display_name,
            ),
            view=view,
        )

    @rps_group.command(
        name="leaderboard",
        description="See the RPS win streak leaderboard for this server",
    )
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=False, private_channels=False, guilds=True)
    async def rps_leaderboard(self, interaction: discord.Interaction):
        lang = await resolve_locale(interaction)

        if not interaction.guild:
            await interaction.response.send_message(
                get_string("games.rps_leaderboard.server_only", lang), ephemeral=True
            )
            return

        server_id = str(interaction.guild.id)

        if server_id not in self.rps_stats or not self.rps_stats[server_id]:
            await interaction.response.send_message(
                get_string("games.joke.no_rps_games", lang), ephemeral=True
            )
            return

        # Sort by best streak
        sorted_users = sorted(
            self.rps_stats[server_id].items(),
            key=lambda x: (x[1]["best_streak"], x[1]["wins"]),
            reverse=True,
        )[:10]

        embed = discord.Embed(
            title=get_string(
                "games.rps_leaderboard.title", lang, server=interaction.guild.name
            ),
            color=discord.Color.blue(),
        )

        for i, (user_id, stats) in enumerate(sorted_users, 1):
            mention = f"<@{user_id}>"

            value_text = (
                f"{mention}\n"
                f"🔥 Best Streak: **{stats['best_streak']}**\n"
                f"Current: {stats['current_streak']} | W: {stats['wins']} L: {stats['losses']}"
            )

            if (
                interaction.guild
            ):  # Emojis break in DMs, though RPS leaderboard is guild-only anyway
                win_pct = (
                    (stats["wins"] / (stats["wins"] + stats["losses"])) * 100
                    if (stats["wins"] + stats["losses"]) > 0
                    else 0
                )
                value_text += f"\n{make_loading_bar(win_pct)}"

            embed.add_field(name=f"Rank #{i}", value=value_text, inline=False)

        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="The question you want to ask")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def eightball(self, interaction: discord.Interaction, question: str):
        lang = await resolve_locale(interaction)

        responses = get_list("games.eightball.responses", lang)
        answer = random.choice(responses)
        await interaction.response.send_message(
            get_string(
                "games.eightball.format", lang, question=question, answer=answer
            ),
            ephemeral=False,
        )

    @app_commands.command(name="dice", description="Roll a die")
    @app_commands.describe(sides="Number of sides (default 6)")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def dice(self, interaction: discord.Interaction, sides: int = 6):
        lang = await resolve_locale(interaction)

        if sides < 2:
            await interaction.response.send_message(
                get_string("errors.dice_min_sides", lang), ephemeral=True
            )
            return
        result = random.randint(1, sides)
        await interaction.response.send_message(
            get_string("games.dice.result", lang, result=result, sides=sides),
            ephemeral=False,
        )

    @message_group.command(name="mock", description="CoNvErT tExT tO sPoNgEbOb CaSe")
    @app_commands.describe(text="The text to mock")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def mock(self, interaction: discord.Interaction, text: str):
        mocked_text = "".join(
            [c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)]
        )
        await interaction.response.send_message(mocked_text, ephemeral=False)

    @message_group.command(name="reverse", description="esreveR txet ruoY")
    @app_commands.describe(text="The text to reverse")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def reverse(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(text[::-1], ephemeral=False)

    @message_group.command(name="epstein", description="⬛almost⬛⬛⬛files⬛")
    @app_commands.describe(text="The ⬛⬛⬛ into ⬛⬛")
    @app_commands.describe(chance="Chance for a word to be replaced with ⬛")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def epstein(
        self, interaction: discord.Interaction, text: str, chance: int = 15
    ):
        chunks = text.split(" ")
        full_text = ""
        for chunk in chunks:
            if random.randint(1, 100) > chance:
                word = "⬛"
            else:
                word = chunk
            full_text += word + " "
        await interaction.response.send_message(full_text[:2000], ephemeral=False)

    @message_group.command(
        name="ascii", description="Convert text to ASCII art"
    )
    @app_commands.describe(
        text="The text to convert",
        search="Search for a font (default: Standard)",
    )
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def ascii(
        self,
        interaction: discord.Interaction,
        text: str,
        search: str = "Standard",
    ):
        try:
            # We use pyfiglet as requested
            # Normalize common names that might have spaces to what pyfiglet expects if needed
            font_name = search.lower().replace(" ", "_")
            try:
                f = pyfiglet.Figlet(font=font_name)
            except pyfiglet.FontNotFound:
                # Try the literal name too
                try:
                    f = pyfiglet.Figlet(font=search)
                except pyfiglet.FontNotFound:
                    # Fallback
                    f = pyfiglet.Figlet(font="standard")
            
            result = f.renderText(text)
        except Exception:
            await interaction.response.send_message("Error generating ASCII.", ephemeral=True)
            return

        # Discord TextDisplay in V2 allows for 4k chars.
        # If it exceeds, we truncate to keep it within limit.
        if len(result) > 3900:
            result = result[:3897] + "..."

        view = ASCIIView(result)
        await interaction.response.send_message(view=view)

    @ascii.autocomplete("search")
    async def ascii_autocomplete_handler(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for ASCII fonts."""
        choices = [
            app_commands.Choice(name=font, value=font)
            for font in self.all_fonts
            if current.lower() in font.lower()
        ]
        return choices[:25]

    @app_commands.command(
        name="ship", description="Calculate compatibility between two users"
    )
    @app_commands.describe(user1="First user", user2="Second user")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def ship(
        self, interaction: discord.Interaction, user1: discord.User, user2: discord.User
    ):
        percentage = random.randint(0, 100)
        emoji = "💔"
        if percentage > 20:
            emoji = "❤️‍🩹"
        if percentage > 50:
            emoji = "❤️"
        if percentage > 80:
            emoji = "💖"
        if percentage == 100:
            emoji = "🔥"
        lang = await resolve_locale(interaction)
        await interaction.response.send_message(
            f"{get_string('fun.ship.title', lang)}\n"
            f"{user1.mention} x {user2.mention}\n"
            f"{get_string('fun.ship.compatibility', lang, percentage=percentage, emoji=emoji)}",
            ephemeral=False,
        )

    @app_commands.command(name="choose", description="Pick a random option from a list")
    @app_commands.describe(options="Options using commas (e.g. Pizza, Burger, Sushi)")
    @app_commands.allowed_installs(users=True, guilds=True)
    @app_commands.allowed_contexts(dms=True, private_channels=True, guilds=True)
    async def choose(self, interaction: discord.Interaction, options: str):
        if "," in options:
            choices_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        else:
            choices_list = options.split()
        lang = await resolve_locale(interaction)
        if not choices_list:
            await interaction.response.send_message(
                get_string("fun.choose.no_options", lang), ephemeral=True
            )
            return

        choice = random.choice(choices_list)
        await interaction.response.send_message(
            get_string("fun.choose.response", lang, choice=choice),
            ephemeral=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))
