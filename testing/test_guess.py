import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

import sys
from pathlib import Path
mocks_path = Path(__file__).parent / "mocks"
sys.path.append(str(mocks_path))
pebbles_root = Path(__file__).parent.parent
sys.path.append(str(pebbles_root))

from fun_commands import GuessGameState, GuessModal

@pytest.mark.asyncio
async def test_guess_modal_initialization():
    state = GuessGameState(None, MagicMock(id=123), 50, "en-US", 100, 7)
    modal = GuessModal(state, "en-US")
    assert modal.state.max_num == 100
    assert modal.guess_input.placeholder == "1-100"
    assert modal.guess_input.max_length == 3

@pytest.mark.asyncio
async def test_guess_modal_custom_max():
    state = GuessGameState(None, MagicMock(id=123), 500, "en-US", 1000, 10)
    modal = GuessModal(state, "en-US")
    assert modal.state.max_num == 1000
    assert modal.guess_input.placeholder == "1-1000"
    assert modal.guess_input.max_length == 4

@pytest.mark.asyncio
async def test_guess_modal_invalid_input_max():
    state = GuessGameState(None, MagicMock(id=123), 50, "en-US", 100, 7)
    modal = GuessModal(state, "en-US")

    # We must mock the property value as discord.ui.TextInput doesn't let us just set it
    type(modal.guess_input).value = discord.utils.cached_property(lambda self: "101")

    interaction = MagicMock()
    interaction.response = AsyncMock()

    await modal.on_submit(interaction)

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args

    # It passes through get_string mock
    assert "Invalid input!" in args[0] or "Invalid input!" in kwargs.get("content", "")

@pytest.mark.asyncio
async def test_guess_modal_win_attempts_math():
    state = GuessGameState(None, MagicMock(id=123), 50, "en-US", 100, 7)
    modal = GuessModal(state, "en-US")

    # We must mock the property value as discord.ui.TextInput doesn't let us just set it
    type(modal.guess_input).value = discord.utils.cached_property(lambda self: "50")

    # Simulate a few failed attempts first
    state.attempts_left = 5  # This means it took 3 attempts (7, 6, 5 left BEFORE decrement in on_submit)

    interaction = MagicMock(user=MagicMock(id=123))
    interaction.response = AsyncMock()

    await modal.on_submit(interaction)

    interaction.response.edit_message.assert_called_once()

    # State attempts should be decremented to 4 inside on_submit
    assert state.attempts_left == 4

    args, kwargs = interaction.response.edit_message.call_args
    assert "view" in kwargs
