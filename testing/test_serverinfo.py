import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'mocks')))

import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from serverinfo import ServerInfo

class MockInteraction:
    def __init__(self, guild):
        self.guild = guild
        self.response = AsyncMock()
        self.followup = AsyncMock()
        self.client = AsyncMock()
        self.user = MagicMock(id=123, locale=discord.Locale.american_english)

class MockGuild:
    def __init__(self, **kwargs):
        self.id = 123456789
        self.name = "Test Server"
        self.owner_id = 987654321
        self.created_at = datetime.now()
        self.member_count = 100
        self.approximate_member_count = 100
        self.approximate_presence_count = 50
        self.roles = [MagicMock()] * 5
        self.text_channels = [MagicMock()] * 10
        self.voice_channels = [MagicMock()] * 5
        self.categories = [MagicMock()] * 3
        self.stage_channels = [MagicMock()]
        self.forums = [MagicMock()]
        self.premium_tier = 1
        self.premium_subscription_count = 5

        self.emojis = [MagicMock(animated=False), MagicMock(animated=True)]
        self.stickers = [MagicMock()] * 2

        self.icon = MagicMock(url="http://icon.url")
        self.banner = MagicMock(url="http://banner.url")
        self.splash = None
        self.discovery_splash = None

        self.verification_level = MagicMock(name="HIGH")
        self.explicit_content_filter = MagicMock(name="ALL_MEMBERS")

        self.description = "A cool test server"
        self.vanity_url_code = "testserver"
        self.features = ["COMMUNITY"]

        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.mark.asyncio
async def test_serverinfo_command():
    bot = AsyncMock()
    bot.fetch_guild = AsyncMock(return_value=MockGuild())

    cog = ServerInfo(bot)

    guild = MockGuild()
    interaction = MockInteraction(guild)

    await cog.serverinfo.callback(cog, interaction)

    interaction.response.defer.assert_called_once()
    bot.fetch_guild.assert_called_once_with(guild.id, with_counts=True)
    interaction.followup.send.assert_called_once()

    args, kwargs = interaction.followup.send.call_args
    view = kwargs.get('view')
    assert view is not None
