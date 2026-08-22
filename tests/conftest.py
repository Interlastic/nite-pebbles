# nite-pebbles/tests/conftest.py
"""
Pytest configuration and shared fixtures for nite-pebbles test suite.
Completely standalone with zero private imports from parent repository.
"""

import sys
import os
from pathlib import Path
import pytest
import pytest_asyncio
import discord

# Configure sys.path strictly within nite-pebbles
PEBBLES_ROOT = Path(__file__).parent.parent.resolve()
MOCKS_PATH = PEBBLES_ROOT / "testing" / "mocks"

# Prepend mocks and pebbles_root to sys.path
for p in [str(MOCKS_PATH), str(PEBBLES_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Remove any accidental parent repository paths from sys.path
PARENT_PATH = str(PEBBLES_ROOT.parent.resolve())
while PARENT_PATH in sys.path:
    sys.path.remove(PARENT_PATH)

from core.db_manager import db as mock_db_instance
from core.server_settings import server_settings as mock_settings_instance
from locales import clear_cache as clear_locales_cache
from discord_mocks import (
    MockBot,
    MockGuild,
    MockUser,
    MockMember,
    MockRole,
    MockTextChannel,
    MockVoiceChannel,
    MockCategoryChannel,
    MockMessage,
    MockInteraction,
    MockAttachment,
    MockPoll,
    MockAuditLogEntry,
)


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mock DB and server settings before and after every test."""
    mock_db_instance.reset()
    mock_settings_instance.reset()
    clear_locales_cache()
    yield
    mock_db_instance.reset()
    mock_settings_instance.reset()
    clear_locales_cache()


@pytest.fixture
def mock_db():
    return mock_db_instance


@pytest.fixture
def mock_server_settings():
    return mock_settings_instance


@pytest.fixture
def mock_bot():
    bot = MockBot()
    bot.server_settings = mock_settings_instance
    return bot



@pytest.fixture
def mock_guild(mock_bot):
    guild = MockGuild(id=101, name="Test Guild")
    mock_bot.add_mock_guild(guild)
    return guild


@pytest.fixture
def mock_user():
    return MockUser(id=1001, name="TestUser", display_name="Test User")


@pytest.fixture
def mock_member(mock_guild):
    member = MockMember(
        id=2001,
        name="TargetMember",
        display_name="Target Member",
        guild=mock_guild,
        roles=[mock_guild.default_role]
    )
    mock_guild.members.append(member)
    return member


@pytest.fixture
def mock_interaction(mock_guild):
    interaction = MockInteraction(
        user=mock_guild.owner,
        guild=mock_guild,
        channel=mock_guild.general_channel
    )
    return interaction
