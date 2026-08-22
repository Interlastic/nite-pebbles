# nite-pebbles/tests/test_fun_commands_discord.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from fun_commands import (
    FunCommands,
    JokeView,
    JokeImageView,
    RPSChallengeView,
    RPSChoiceView,
    RPSSingleChoiceView,
    RPSPlayAgainView,
    ASCIIView,
)
from discord_mocks import (
    MockBot,
    MockGuild,
    MockUser,
    MockMember,
    MockInteraction,
    MockTextChannel,
    MockMessage,
)



class TestFunCommandsDiscord:
    @pytest.fixture
    def fun_cog(self, mock_bot, tmp_path, monkeypatch):
        import fun_commands as fc
        monkeypatch.setattr(fc, "JOKE_STATS_FILE", tmp_path / "joke_stats.json")
        monkeypatch.setattr(fc, "RPS_STATS_FILE", tmp_path / "rps_stats.json")
        cog = FunCommands(mock_bot)
        return cog

    @pytest.mark.asyncio
    async def test_joke_random_success(self, fun_cog, mock_interaction):
        mock_response_data = {"id": "joke_123", "joke": "Why don't skeletons fight? They don't have the guts."}
        
        mock_get = AsyncMock()
        mock_get.__aenter__.return_value = AsyncMock(status=200, json=AsyncMock(return_value=mock_response_data))

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await fun_cog.joke_random.callback(fun_cog, mock_interaction)

        assert len(mock_interaction.sent_followups) == 1
        resp = mock_interaction.sent_followups[0]
        assert "skeletons" in resp["content"]
        assert isinstance(resp["view"], JokeView)

    @pytest.mark.asyncio
    async def test_joke_random_api_failure(self, fun_cog, mock_interaction):
        mock_get = AsyncMock()
        mock_get.__aenter__.return_value = AsyncMock(status=500)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await fun_cog.joke_random.callback(fun_cog, mock_interaction)

        assert len(mock_interaction.sent_followups) == 1
        resp = mock_interaction.sent_followups[0]
        assert "Failed to fetch joke" in resp["content"]

    @pytest.mark.asyncio
    async def test_joke_leaderboard_empty(self, fun_cog, mock_interaction):
        fun_cog.joke_stats = {}
        await fun_cog.joke_leaderboard.callback(fun_cog, mock_interaction)
        assert len(mock_interaction.sent_responses) == 1
        assert "No jokes have been voted on yet" in mock_interaction.sent_responses[0]["content"]

    @pytest.mark.asyncio
    async def test_joke_leaderboard_populated(self, fun_cog, mock_interaction):
        fun_cog.joke_stats = {
            "j1": {"text": "Joke 1", "upvotes": 10, "downvotes": 2},
            "j2": {"text": "Joke 2", "upvotes": 5, "downvotes": 0}
        }
        await fun_cog.joke_leaderboard.callback(fun_cog, mock_interaction)
        assert len(mock_interaction.sent_responses) == 1
        embed = mock_interaction.sent_responses[0]["embed"]
        assert embed is not None
        assert len(embed.fields) == 2

    @pytest.mark.asyncio
    async def test_joke_view_upvote_and_downvote(self, fun_cog, mock_interaction):
        view = JokeView(fun_cog, "j_test", "Test Joke Content", lang="en")
        button = discord.ui.Button(label="👍")

        # First upvote
        await view.upvote.callback(mock_interaction)
        assert len(mock_interaction.sent_responses) == 1
        assert "Upvoted" in mock_interaction.sent_responses[0]["content"]
        assert fun_cog.joke_stats["j_test"]["upvotes"] == 1

        # Second upvote by same user -> rejected
        mock_interaction.sent_responses.clear()
        await view.upvote.callback(mock_interaction)
        assert len(mock_interaction.sent_responses) == 1
        assert "already voted" in mock_interaction.sent_responses[0]["content"]

        # Different user downvotes
        user2 = MockUser(id=98765)
        inter2 = MockInteraction(user=user2)
        await view.downvote.callback(inter2)
        assert "Downvoted" in inter2.sent_responses[0]["content"]
        assert fun_cog.joke_stats["j_test"]["downvotes"] == 1

    @pytest.mark.asyncio
    async def test_joke_image_view_toggle(self, fun_cog, mock_interaction):
        view = JokeImageView(fun_cog, "j_test", "Test Joke", current_font="Pacifico", lang="en")
        fun_cog.get_joke_as_image = AsyncMock()

        await view.toggle_font.callback(mock_interaction)
        fun_cog.get_joke_as_image.assert_called_once_with(
            mock_interaction, "j_test", "Test Joke", font="Inter", edit_original=True
        )

    @pytest.mark.asyncio
    async def test_coinflip_single_and_multi(self, fun_cog, mock_interaction):
        # Single coin
        await fun_cog.coinflip.callback(fun_cog, mock_interaction, count=1)
        assert len(mock_interaction.sent_responses) == 1
        assert "🪙" in mock_interaction.sent_responses[0]["content"]

        # Multi coins (count=5)
        mock_interaction.sent_responses.clear()
        await fun_cog.coinflip.callback(fun_cog, mock_interaction, count=5)
        assert len(mock_interaction.sent_responses) == 1
        assert "🪙" in mock_interaction.sent_responses[0]["content"]

        # Bounds: < 1
        mock_interaction.sent_responses.clear()
        await fun_cog.coinflip.callback(fun_cog, mock_interaction, count=0)
        assert "at least 1" in mock_interaction.sent_responses[0]["content"]

        # Bounds: > 20
        mock_interaction.sent_responses.clear()
        await fun_cog.coinflip.callback(fun_cog, mock_interaction, count=25)
        assert "Maximum 20 coins" in mock_interaction.sent_responses[0]["content"]

    @pytest.mark.asyncio
    async def test_rps_play_single(self, fun_cog, mock_interaction):
        await fun_cog.rps_play.callback(fun_cog, mock_interaction, choice="Rock")
        assert len(mock_interaction.sent_responses) == 1
        resp = mock_interaction.sent_responses[0]
        assert "Rock" in resp["content"]
        assert isinstance(resp["view"], RPSPlayAgainView)

    @pytest.mark.asyncio
    async def test_rps_challenge_self_and_bot(self, fun_cog, mock_interaction):
        # Challenge self
        await fun_cog.rps_challenge.callback(fun_cog, mock_interaction, opponent=mock_interaction.user)
        assert "can't challenge yourself" in mock_interaction.sent_responses[0]["content"]

        # Challenge bot
        bot_user = MockUser(id=999, bot=True)
        mock_interaction.sent_responses.clear()
        await fun_cog.rps_challenge.callback(fun_cog, mock_interaction, opponent=bot_user)
        assert "can't challenge a bot" in mock_interaction.sent_responses[0]["content"]

    @pytest.mark.asyncio
    async def test_rps_challenge_flow(self, fun_cog, mock_interaction):
        opponent = MockUser(id=2002, name="Opponent")
        await fun_cog.rps_challenge.callback(fun_cog, mock_interaction, opponent=opponent)
        assert len(mock_interaction.sent_responses) == 1
        view = mock_interaction.sent_responses[0]["view"]
        assert isinstance(view, RPSChallengeView)

        # Non-opponent accepts -> rejected
        non_opponent = MockUser(id=3003)
        bad_inter = MockInteraction(user=non_opponent)
        await view.accept_button.callback(bad_inter)
        assert "Only the challenged player" in bad_inter.sent_responses[0]["content"]

        # Opponent accepts -> switches to choice view
        opp_inter = MockInteraction(user=opponent)
        await view.accept_button.callback(opp_inter)
        assert opp_inter.last_response is not None
        choice_view = opp_inter.last_response["view"]
        assert isinstance(choice_view, RPSChoiceView)

        # Challenger chooses Rock
        chal_inter = MockInteraction(user=mock_interaction.user)
        msg_mock = MockMessage(guild=mock_interaction.guild)
        chal_inter.message = msg_mock
        await choice_view.handle_choice(chal_inter, "Rock")
        assert len(choice_view.choices) == 1

        # Opponent chooses Scissors -> Challenger wins
        opp_inter2 = MockInteraction(user=opponent)
        opp_inter2.message = msg_mock
        await choice_view.handle_choice(opp_inter2, "Scissors")
        assert len(choice_view.choices) == 2
        assert mock_interaction.guild.id is not None

    @pytest.mark.asyncio
    async def test_rps_leaderboard(self, fun_cog, mock_interaction):
        # In guild, empty stats
        await fun_cog.rps_leaderboard.callback(fun_cog, mock_interaction)
        assert len(mock_interaction.sent_responses) == 1

        # Populated stats
        fun_cog.rps_stats = {
            str(mock_interaction.guild.id): {
                str(mock_interaction.user.id): {"wins": 10, "losses": 2, "current_streak": 3, "best_streak": 5}
            }
        }
        mock_interaction.sent_responses.clear()
        await fun_cog.rps_leaderboard.callback(fun_cog, mock_interaction)
        embed = mock_interaction.sent_responses[0]["embed"]
        assert embed is not None
        assert len(embed.fields) == 1
        assert "Best Streak: **5**" in embed.fields[0].value

    @pytest.mark.asyncio
    async def test_eightball(self, fun_cog, mock_interaction):
        await fun_cog.eightball.callback(fun_cog, mock_interaction, question="Will tests pass?")
        assert len(mock_interaction.sent_responses) == 1
        content = mock_interaction.sent_responses[0]["content"]
        assert "Will tests pass?" in content

    @pytest.mark.asyncio
    async def test_dice(self, fun_cog, mock_interaction):
        # Normal 6 sides
        await fun_cog.dice.callback(fun_cog, mock_interaction, sides=6)
        assert len(mock_interaction.sent_responses) == 1
        assert "🎲" in mock_interaction.sent_responses[0]["content"]

        # Invalid < 2
        mock_interaction.sent_responses.clear()
        await fun_cog.dice.callback(fun_cog, mock_interaction, sides=1)
        assert "must have at least 2 sides" in mock_interaction.sent_responses[0]["content"]

    @pytest.mark.asyncio
    async def test_mock_reverse_epstein(self, fun_cog, mock_interaction):
        # mock
        await fun_cog.mock.callback(fun_cog, mock_interaction, text="hello world")
        assert mock_interaction.sent_responses[-1]["content"] == "HeLlO WoRlD"

        # reverse
        await fun_cog.reverse.callback(fun_cog, mock_interaction, text="hello")
        assert mock_interaction.sent_responses[-1]["content"] == "olleh"

        # epstein
        await fun_cog.epstein.callback(fun_cog, mock_interaction, text="hello world test", chance=0)
        assert "⬛" in mock_interaction.sent_responses[-1]["content"]

    @pytest.mark.asyncio
    async def test_ascii_and_autocomplete(self, fun_cog, mock_interaction):
        # Ascii command
        await fun_cog.ascii.callback(fun_cog, mock_interaction, text="Hi", search="Standard")
        assert len(mock_interaction.sent_responses) == 1
        view = mock_interaction.sent_responses[0]["view"]
        assert isinstance(view, ASCIIView)

        # Autocomplete handler
        choices = await fun_cog.ascii_autocomplete_handler(mock_interaction, current="stan")
        assert isinstance(choices, list)
        assert any("standard" in c.name.lower() for c in choices)

    @pytest.mark.asyncio
    async def test_ship(self, fun_cog, mock_interaction):
        u1 = MockUser(id=1, name="Alice")
        u2 = MockUser(id=2, name="Bob")
        await fun_cog.ship.callback(fun_cog, mock_interaction, user1=u1, user2=u2)
        assert len(mock_interaction.sent_responses) == 1
        assert u1.mention in mock_interaction.sent_responses[0]["content"]
        assert u2.mention in mock_interaction.sent_responses[0]["content"]


    @pytest.mark.asyncio
    async def test_choose(self, fun_cog, mock_interaction):
        # Comma-separated
        await fun_cog.choose.callback(fun_cog, mock_interaction, options="Pizza, Burger, Salad")
        assert len(mock_interaction.sent_responses) == 1
        chosen = mock_interaction.sent_responses[0]["content"]
        assert any(opt in chosen for opt in ["Pizza", "Burger", "Salad"])

        # Whitespace-separated
        mock_interaction.sent_responses.clear()
        await fun_cog.choose.callback(fun_cog, mock_interaction, options="Cat Dog Bird")
        chosen2 = mock_interaction.sent_responses[0]["content"]
        assert any(opt in chosen2 for opt in ["Cat", "Dog", "Bird"])

        # Empty options
        mock_interaction.sent_responses.clear()
        await fun_cog.choose.callback(fun_cog, mock_interaction, options="")
        assert "Please provide some options" in mock_interaction.sent_responses[0]["content"]
