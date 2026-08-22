# nite-pebbles/tests/test_fun_commands_logic.py
import pytest
import json
from pathlib import Path
import fun_commands
from fun_commands import (
    FunCommands,
    load_joke_stats,
    save_joke_stats,
    load_rps_stats,
    save_rps_stats,
)
from discord_mocks import MockBot


class TestFunCommandsLogic:
    @pytest.fixture
    def fun_cog(self, mock_bot, tmp_path, monkeypatch):
        # Isolate persistence files to tmp_path
        joke_file = tmp_path / "joke_stats.json"
        rps_file = tmp_path / "rps_stats.json"
        monkeypatch.setattr(fun_commands, "JOKE_STATS_FILE", joke_file)
        monkeypatch.setattr(fun_commands, "RPS_STATS_FILE", rps_file)

        cog = FunCommands(mock_bot)
        return cog

    def test_save_and_load_joke_stats(self, tmp_path, monkeypatch):
        test_file = tmp_path / "test_joke_stats.json"
        monkeypatch.setattr(fun_commands, "JOKE_STATS_FILE", test_file)

        assert load_joke_stats() == {}

        sample_data = {"joke_1": {"text": "Funny joke", "upvotes": 5, "downvotes": 1}}
        save_joke_stats(sample_data)

        loaded = load_joke_stats()
        assert loaded == sample_data

    def test_save_and_load_rps_stats(self, tmp_path, monkeypatch):
        test_file = tmp_path / "test_rps_stats.json"
        monkeypatch.setattr(fun_commands, "RPS_STATS_FILE", test_file)

        assert load_rps_stats() == {}

        sample_data = {"guild_1": {"user_1": {"wins": 3, "losses": 1, "current_streak": 2, "best_streak": 2}}}
        save_rps_stats(sample_data)

        loaded = load_rps_stats()
        assert loaded == sample_data

    def test_track_joke_vote_upvote(self, fun_cog):
        fun_cog.track_joke_vote("joke_100", "Why did the chicken cross the road?", upvote=True)
        stats = fun_cog.joke_stats.get("joke_100")
        assert stats is not None
        assert stats["upvotes"] == 1
        assert stats["downvotes"] == 0

        # Additional upvote
        fun_cog.track_joke_vote("joke_100", "Why did the chicken cross the road?", upvote=True)
        assert fun_cog.joke_stats["joke_100"]["upvotes"] == 2

    def test_track_joke_vote_downvote(self, fun_cog):
        fun_cog.track_joke_vote("joke_200", "A bad joke", upvote=False)
        stats = fun_cog.joke_stats.get("joke_200")
        assert stats is not None
        assert stats["upvotes"] == 0
        assert stats["downvotes"] == 1

    def test_update_rps_stats_win_and_streak(self, fun_cog):
        server_id = "101"
        user_id = "1001"

        # Win 1
        fun_cog.update_rps_stats(server_id, user_id, won=True)
        user_stats = fun_cog.rps_stats[server_id][user_id]
        assert user_stats["wins"] == 1
        assert user_stats["losses"] == 0
        assert user_stats["current_streak"] == 1
        assert user_stats["best_streak"] == 1

        # Win 2
        fun_cog.update_rps_stats(server_id, user_id, won=True)
        assert user_stats["wins"] == 2
        assert user_stats["current_streak"] == 2
        assert user_stats["best_streak"] == 2

    def test_update_rps_stats_loss_resets_current_streak(self, fun_cog):
        server_id = "101"
        user_id = "1001"

        # Win 2 in a row
        fun_cog.update_rps_stats(server_id, user_id, won=True)
        fun_cog.update_rps_stats(server_id, user_id, won=True)
        assert fun_cog.rps_stats[server_id][user_id]["current_streak"] == 2
        assert fun_cog.rps_stats[server_id][user_id]["best_streak"] == 2

        # Loss resets current streak to 0 but keeps best streak
        fun_cog.update_rps_stats(server_id, user_id, won=False)
        user_stats = fun_cog.rps_stats[server_id][user_id]
        assert user_stats["wins"] == 2
        assert user_stats["losses"] == 1
        assert user_stats["current_streak"] == 0
        assert user_stats["best_streak"] == 2

    def test_load_all_fonts(self, fun_cog):
        assert isinstance(fun_cog.all_fonts, list)
        assert len(fun_cog.all_fonts) > 0
        assert "Standard" in fun_cog.all_fonts or "standard" in [f.lower() for f in fun_cog.all_fonts]
