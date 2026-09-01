import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

import sys
from pathlib import Path
mocks_path = Path(__file__).parent / "mocks"
sys.path.append(str(mocks_path))
pebbles_root = Path(__file__).parent.parent
sys.path.append(str(pebbles_root))

from serverinfo import ServerInfo, ServerInfoView, SubmenuView

@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.name = "Test Server"
    guild.id = 123456789
    guild.premium_tier = 2
    guild.premium_subscription_count = 7
    guild.features = ["COMMUNITY"]
    guild.approximate_member_count = 100
    guild.approximate_presence_count = 50
    guild.icon = MagicMock()
    guild.icon.url = "http://icon.url"

    # Defaults for other stats
    guild.channels = []
    guild.categories = []
    guild.emojis = []
    guild.roles = []
    guild.stickers = []
    guild.owner = MagicMock()
    guild.owner.mention = "<@1>"
    guild.owner_id = 1
    guild.created_at = MagicMock()
    guild.created_at.timestamp.return_value = 1600000000
    guild.verification_level = "high"
    guild.explicit_content_filter = "all_members"
    guild.description = "Test Desc"
    guild.vanity_url_code = "test"

    return guild

@pytest.fixture
def mock_bot(mock_guild):
    bot = MagicMock()
    bot.fetch_guild = AsyncMock(return_value=mock_guild)
    return bot

@pytest.mark.asyncio
async def test_serverinfo_main_command(mock_bot, mock_guild):
    cog = ServerInfo(mock_bot)

    interaction = MagicMock()
    interaction.guild.id = 123456789
    interaction.user.display_name = "User"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    await cog.serverinfo.callback(cog, interaction)

    mock_bot.fetch_guild.assert_called_once_with(123456789, with_counts=True)
    interaction.response.defer.assert_called_once_with(ephemeral=False)
    interaction.followup.send.assert_called_once()

    args, kwargs = interaction.followup.send.call_args
    assert "view" in kwargs
    # The view should be a template.message returned MagicMock/View equivalent in the mock

@pytest.mark.asyncio
async def test_serverinfo_more_info_callback(mock_bot, mock_guild):
    cog = ServerInfo(mock_bot)

    interaction = MagicMock()
    interaction.user.display_name = "User"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    view = ServerInfoView(mock_guild, interaction, "en", cog)

    # Trigger the callback
    await view.more_info_btn.callback(interaction)

    interaction.response.defer.assert_called_once_with(ephemeral=False)
    interaction.followup.send.assert_called_once()

    args, kwargs = interaction.followup.send.call_args
    assert "view" in kwargs

@pytest.mark.asyncio
async def test_serverinfo_images_callback(mock_bot, mock_guild):
    cog = ServerInfo(mock_bot)

    interaction = MagicMock()
    interaction.user.display_name = "User"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    view = ServerInfoView(mock_guild, interaction, "en", cog)

    # Trigger the callback
    await view.images_btn.callback(interaction)

    interaction.response.defer.assert_called_once_with(ephemeral=False)
    interaction.followup.send.assert_called_once()

    args, kwargs = interaction.followup.send.call_args
    assert "view" in kwargs

@pytest.mark.asyncio
async def test_serverinfo_back_callback():
    interaction = MagicMock()
    interaction.message.delete = AsyncMock()
    interaction.response.defer = AsyncMock()

    view = SubmenuView(None, "en", None, None)
    await view.back_btn.callback(interaction)

    interaction.message.delete.assert_called_once()
