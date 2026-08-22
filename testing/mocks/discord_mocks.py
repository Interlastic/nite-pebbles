# nite-pebbles/testing/mocks/discord_mocks.py
"""
High-fidelity standalone Discord mocks for Nite-Pebbles testing.
Provides mock implementations of discord.py objects (Users, Members, Guilds,
Channels, Messages, Interactions, Views, Audit Logs, Webhooks, etc.)
with zero dependencies on parent/private repositories.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, AsyncIterator
import discord
from discord.ext import commands
from core.server_settings import server_settings as default_server_settings


class MockAsset:
    def __init__(self, url: str = "https://cdn.discordapp.com/embed/avatars/0.png"):
        self.url = url

    async def read(self) -> bytes:
        return b"fake_asset_bytes"

    def __str__(self) -> str:
        return self.url


class MockUser:
    def __init__(self, id: int = 1001, name: str = "TestUser", display_name: Optional[str] = None, bot: bool = False):
        self.id = id
        self.name = name
        self.display_name = display_name or name
        self.bot = bot
        self.display_avatar = MockAsset(f"https://cdn.discordapp.com/avatars/{self.id}/avatar.png")
        self.avatar = self.display_avatar
        self.mutual_guilds: List[Any] = []
        self.sent_messages: List[Dict[str, Any]] = []

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    async def send(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                   embed: Optional[discord.Embed] = None, file: Optional[discord.File] = None, **kwargs) -> Any:
        msg = {
            "content": content,
            "view": view,
            "embed": embed,
            "file": file,
            "kwargs": kwargs
        }
        self.sent_messages.append(msg)
        return msg

    def __eq__(self, other: Any) -> bool:
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"<MockUser id={self.id} name='{self.name}'>"



class MockRole:
    def __init__(self, id: int = 5001, name: str = "TestRole", guild: Optional[Any] = None,
                 position: int = 1, color: Optional[discord.Color] = None,
                 hoist: bool = False, mentionable: bool = False,
                 permissions: Optional[discord.Permissions] = None):
        self.id = id
        self.name = name
        self.guild = guild
        self.position = position
        self.color = color or discord.Color.default()
        self.colour = self.color
        self.hoist = hoist
        self.mentionable = mentionable
        self.permissions = permissions or discord.Permissions.none()

    @property
    def mention(self) -> str:
        return f"<@&{self.id}>"

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, MockRole):
            return self.position >= other.position
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, MockRole):
            return self.position > other.position
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, MockRole):
            return self.position <= other.position
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, MockRole):
            return self.position < other.position
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MockRole):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __iter__(self):
        return iter(self.permissions)


    async def edit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            if k == "colour":
                self.color = v
            elif k == "color":
                self.colour = v

    async def delete(self, reason: Optional[str] = None) -> None:
        if self.guild and self in self.guild.roles:
            self.guild.roles.remove(self)


class MockMember(MockUser):
    def __init__(self, id: int = 1001, name: str = "TestMember", display_name: Optional[str] = None,
                 guild: Optional[Any] = None, roles: Optional[List[MockRole]] = None,
                 bot: bool = False, permissions: Optional[discord.Permissions] = None):
        super().__init__(id=id, name=name, display_name=display_name, bot=bot)
        self.guild = guild
        self.roles = roles or []
        self._guild_permissions = permissions or discord.Permissions.all()
        self.guild_avatar: Optional[MockAsset] = None
        self.timed_out_until: Optional[datetime] = None
        self.premium_since: Optional[datetime] = None
        self.nick: Optional[str] = None
        self.joined_at = datetime.now(timezone.utc)

    @property
    def top_role(self) -> MockRole:
        if not self.roles:
            default_r = MockRole(id=0, name="@everyone", guild=self.guild, position=0)
            return default_r
        return max(self.roles, key=lambda r: r.position)

    @property
    def guild_permissions(self) -> discord.Permissions:
        return self._guild_permissions

    @guild_permissions.setter
    def guild_permissions(self, val: discord.Permissions):
        self._guild_permissions = val

    async def timeout(self, until: Optional[datetime], reason: Optional[str] = None) -> None:
        self.timed_out_until = until

    async def kick(self, reason: Optional[str] = None) -> None:
        if self.guild and self in self.guild.members:
            self.guild.members.remove(self)

    async def ban(self, reason: Optional[str] = None, delete_message_seconds: int = 0) -> None:
        if self.guild:
            await self.guild.ban(self, reason=reason, delete_message_seconds=delete_message_seconds)

    async def add_roles(self, *roles: MockRole, reason: Optional[str] = None) -> None:
        for r in roles:
            if r not in self.roles:
                self.roles.append(r)

    async def remove_roles(self, *roles: MockRole, reason: Optional[str] = None) -> None:
        for r in roles:
            if r in self.roles:
                self.roles.remove(r)

    async def edit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockAttachment:
    def __init__(self, filename: str = "test.png", url: str = "https://cdn.discordapp.com/attachments/1/1/test.png", size: int = 1024):
        self.id = 7001
        self.filename = filename
        self.url = url
        self.size = size


class MockPollAnswer:
    def __init__(self, text: str, answer_id: int = 1):
        self.id = answer_id
        self.text = text
        self.vote_count = 0


class MockPoll:
    def __init__(self, question: str, options: List[str]):
        self.question = {"text": question}
        self.answers = [MockPollAnswer(text=opt, answer_id=i + 1) for i, opt in enumerate(options)]


class MockMessageReference:
    def __init__(self, message: Optional[Any] = None, message_id: int = 3001):
        self.message_id = message.id if message else message_id
        self.channel_id = message.channel.id if message else 2001
        self.guild_id = message.guild.id if message and message.guild else 101
        self.resolved = message


class MockMessage(discord.Message):
    def __init__(self, id: int = 3001, content: str = "", author: Optional[Union[MockUser, MockMember]] = None,
                 channel: Optional[Any] = None, guild: Optional[Any] = None,
                 attachments: Optional[List[MockAttachment]] = None,
                 poll: Optional[MockPoll] = None, reference: Optional[MockMessageReference] = None):
        self.id = id
        self.content = content
        self.clean_content = content
        self.author = author or MockUser()
        self.channel = channel
        self.guild = guild or (channel.guild if channel else None)
        self._created_at = datetime.now(timezone.utc)
        self.attachments = attachments or []
        self.poll = poll
        self.reference = reference
        self.edited = False
        self.deleted = False
        self.type = discord.MessageType.default


    @property
    def created_at(self) -> datetime:
        return self._created_at

    @created_at.setter
    def created_at(self, val: datetime):
        self._created_at = val

    async def edit(self, **kwargs) -> None:
        self.edited = True
        if "content" in kwargs and kwargs["content"] is not None:
            self.content = kwargs["content"]
            self.clean_content = kwargs["content"]

    async def delete(self) -> None:
        self.deleted = True

    async def reply(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None, **kwargs) -> "MockMessage":
        ref = MockMessageReference(message=self)
        msg = MockMessage(content=content or "", author=self.guild.me if self.guild else MockUser(),
                          channel=self.channel, guild=self.guild, reference=ref)
        if self.channel:
            self.channel.sent_messages.append({"content": content, "view": view, "reference": ref, "kwargs": kwargs})
        return msg


class MockWebhook:
    def __init__(self, id: int = 8001, name: str = "Mod-Logs", channel: Optional[Any] = None, user: Optional[MockUser] = None):
        self.id = id
        self.name = name
        self.channel = channel
        self.user = user
        self.sent_messages: List[Dict[str, Any]] = []

    async def send(self, **kwargs) -> None:
        self.sent_messages.append(kwargs)


class MockChannel:
    def __init__(self, id: int = 2001, name: str = "general", guild: Optional[Any] = None,
                 channel_type: discord.ChannelType = discord.ChannelType.text,
                 category: Optional[Any] = None, topic: Optional[str] = None):
        self.id = id
        self.name = name
        self.guild = guild
        self.type = channel_type
        self.category = category
        self.topic = topic
        self.nsfw = False
        self.slowmode_delay = 0
        self.sent_messages: List[Dict[str, Any]] = []
        self._webhooks: List[MockWebhook] = []
        self.history_messages: List[MockMessage] = []

    @property
    def mention(self) -> str:
        return f"<#{self.id}>"

    @property
    def jump_url(self) -> str:
        guild_id = getattr(self.guild, "id", "@me")
        return f"https://discord.com/channels/{guild_id}/{self.id}"


    async def send(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                   embed: Optional[discord.Embed] = None, file: Optional[discord.File] = None,
                   files: Optional[List[discord.File]] = None, **kwargs) -> MockMessage:
        msg_obj = MockMessage(content=content or "", channel=self, guild=self.guild)
        self.sent_messages.append({
            "content": content,
            "view": view,
            "embed": embed,
            "file": file,
            "files": files,
            "kwargs": kwargs
        })
        self.history_messages.append(msg_obj)
        return msg_obj

    async def edit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    async def delete(self, reason: Optional[str] = None) -> None:
        if self.guild and self in self.guild.channels:
            self.guild.channels.remove(self)

    def permissions_for(self, member: Any) -> discord.Permissions:
        return discord.Permissions.all()

    async def webhooks(self) -> List[MockWebhook]:
        return list(self._webhooks)

    async def create_webhook(self, name: str = "Mod-Logs", avatar: Optional[bytes] = None) -> MockWebhook:
        wh = MockWebhook(name=name, channel=self, user=self.guild.me if self.guild else None)
        self._webhooks.append(wh)
        return wh

    def __eq__(self, other: Any) -> bool:
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    async def history(self, limit: int = 100) -> AsyncIterator[MockMessage]:
        for msg in list(reversed(self.history_messages))[:limit]:
            yield msg



class MockTextChannel(MockChannel):
    def __init__(self, id: int = 2001, name: str = "general", guild: Optional[Any] = None, **kwargs):
        super().__init__(id=id, name=name, guild=guild, channel_type=discord.ChannelType.text, **kwargs)


class MockVoiceChannel(MockChannel):
    def __init__(self, id: int = 2002, name: str = "Voice Lounge", guild: Optional[Any] = None, **kwargs):
        super().__init__(id=id, name=name, guild=guild, channel_type=discord.ChannelType.voice, **kwargs)


class MockCategoryChannel(MockChannel):
    def __init__(self, id: int = 2003, name: str = "SERVER STATS", guild: Optional[Any] = None, **kwargs):
        super().__init__(id=id, name=name, guild=guild, channel_type=discord.ChannelType.category, **kwargs)


class MockBanEntry:
    def __init__(self, user: MockUser, reason: Optional[str] = "Rule violation"):
        self.user = user
        self.reason = reason


class MockAuditLogEntry:
    def __init__(self, action: discord.AuditLogAction, user: MockUser, target: Optional[Any] = None,
                 reason: Optional[str] = None, before: Optional[Any] = None, after: Optional[Any] = None):
        self.id = 9001
        self.action = action
        self.user = user
        self.target = target or MockUser(id=9999)
        self.reason = reason
        self.created_at = datetime.now(timezone.utc)
        self.before = before or type("AuditBefore", (), {"name": "old"})()
        self.after = after or type("AuditAfter", (), {"name": "new"})()


class MockGuild:
    def __init__(self, id: int = 101, name: str = "Test Server", owner_id: int = 1000):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.icon = MockAsset(f"https://cdn.discordapp.com/icons/{self.id}/icon.png")
        self.features: List[str] = ["COMMUNITY"]
        self.premium_tier = 1
        self.premium_subscription_count = 5
        self.member_count = 100
        self.approximate_member_count = 100
        self.approximate_presence_count = 25
        self.afk_timeout = 300

        # Roles
        self.default_role = MockRole(id=self.id, name="@everyone", guild=self, position=0)
        self.admin_role = MockRole(id=5002, name="Admin", guild=self, position=10,
                                   permissions=discord.Permissions.all())
        self.mod_role = MockRole(id=5003, name="Moderator", guild=self, position=5,
                                 permissions=discord.Permissions(manage_guild=True, ban_members=True, kick_members=True, moderate_members=True))
        self.roles: List[MockRole] = [self.default_role, self.mod_role, self.admin_role]

        # Members
        self.owner = MockMember(id=owner_id, name="ServerOwner", guild=self, roles=[self.admin_role])
        self.me = MockMember(id=9999, name="NiteBot", bot=True, guild=self, roles=[self.admin_role])
        self.members: List[MockMember] = [self.owner, self.me]

        # Channels
        self.general_channel = MockTextChannel(id=2001, name="general", guild=self)
        self.voice_channel = MockVoiceChannel(id=2002, name="General Voice", guild=self)
        self.stats_category = MockCategoryChannel(id=2003, name="SERVER STATS", guild=self)
        self.channels: List[MockChannel] = [self.general_channel, self.voice_channel, self.stats_category]

        # State storage
        self.banned_users: List[MockBanEntry] = []
        self.audit_log_entries: List[MockAuditLogEntry] = []
        self._state = type("State", (), {"http": type("HTTP", (), {"request": self._mock_http_request})()})()

    async def _mock_http_request(self, route, **kwargs):
        # Fallback member search simulation
        query = kwargs.get("params", {}).get("query", "").lower()
        results = []
        for m in self.members:
            if query in m.name.lower() or query in m.display_name.lower():
                results.append({"user": {"id": str(m.id), "username": m.name, "global_name": m.display_name, "bot": m.bot}, "roles": []})
        return results

    @property
    def text_channels(self) -> List[MockTextChannel]:
        return [c for c in self.channels if isinstance(c, MockTextChannel)]

    @property
    def voice_channels(self) -> List[MockVoiceChannel]:
        return [c for c in self.channels if isinstance(c, MockVoiceChannel)]

    @property
    def categories(self) -> List[MockCategoryChannel]:
        return [c for c in self.channels if isinstance(c, MockCategoryChannel)]

    def get_member(self, user_id: int) -> Optional[MockMember]:
        for m in self.members:
            if m.id == user_id:
                return m
        return None

    async def fetch_member(self, user_id: int) -> MockMember:
        member = self.get_member(user_id)
        if member:
            return member
        new_m = MockMember(id=user_id, name=f"FetchedUser_{user_id}", guild=self)
        self.members.append(new_m)
        return new_m

    def get_channel(self, channel_id: int) -> Optional[MockChannel]:
        for c in self.channels:
            if c.id == channel_id:
                return c
        return None

    def get_role(self, role_id: int) -> Optional[MockRole]:
        for r in self.roles:
            if r.id == role_id:
                return r
        return None

    async def bans(self) -> AsyncIterator[MockBanEntry]:
        for b in list(self.banned_users):
            yield b

    async def audit_logs(self, limit: int = 10, action: Optional[discord.AuditLogAction] = None) -> AsyncIterator[MockAuditLogEntry]:
        count = 0
        for entry in reversed(self.audit_log_entries):
            if action is None or entry.action == action:
                yield entry
                count += 1
                if count >= limit:
                    break

    async def ban(self, user: Union[MockUser, MockMember], reason: Optional[str] = None, delete_message_seconds: int = 0) -> None:
        self.banned_users.append(MockBanEntry(user=user, reason=reason))
        if isinstance(user, MockMember) and user in self.members:
            self.members.remove(user)
        self.audit_log_entries.append(MockAuditLogEntry(action=discord.AuditLogAction.ban, user=self.me, target=user, reason=reason))

    async def unban(self, user: Union[MockUser, MockMember], reason: Optional[str] = None) -> None:
        target_entry = None
        for b in self.banned_users:
            if b.user.id == user.id:
                target_entry = b
                break
        if not target_entry:
            raise discord.NotFound(type("MockResp", (), {"status": 404, "reason": "Not Found"})(), "Unknown Ban")
        self.banned_users.remove(target_entry)
        self.audit_log_entries.append(MockAuditLogEntry(action=discord.AuditLogAction.unban, user=self.me, target=user, reason=reason))

    async def kick(self, user: Union[MockUser, MockMember], reason: Optional[str] = None) -> None:
        if isinstance(user, MockMember) and user in self.members:
            self.members.remove(user)
        self.audit_log_entries.append(MockAuditLogEntry(action=discord.AuditLogAction.kick, user=self.me, target=user, reason=reason))

    async def create_text_channel(self, name: str, category: Optional[Any] = None, **kwargs) -> MockTextChannel:
        ch = MockTextChannel(id=len(self.channels) + 2000, name=name, guild=self, category=category)
        self.channels.append(ch)
        return ch

    async def create_voice_channel(self, name: str, category: Optional[Any] = None, **kwargs) -> MockVoiceChannel:
        ch = MockVoiceChannel(id=len(self.channels) + 2000, name=name, guild=self, category=category)
        self.channels.append(ch)
        return ch

    async def create_category(self, name: str, **kwargs) -> MockCategoryChannel:
        cat = MockCategoryChannel(id=len(self.channels) + 2000, name=name, guild=self)
        self.channels.append(cat)
        return cat

    async def create_role(self, name: str, color: Optional[discord.Color] = None,
                          hoist: bool = False, mentionable: bool = False, **kwargs) -> MockRole:
        role = MockRole(id=len(self.roles) + 5000, name=name, guild=self, position=len(self.roles),
                        color=color, hoist=hoist, mentionable=mentionable)
        self.roles.append(role)
        return role

    async def edit(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __eq__(self, other: Any) -> bool:
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    async def fetch_widget(self) -> Any:
        return type("Widget", (), {"presence_count": self.approximate_presence_count})()



class MockInteractionResponse:
    def __init__(self, interaction: Any):
        self.interaction = interaction
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def defer(self, ephemeral: bool = False, **kwargs) -> None:
        self._done = True
        self.interaction.deferred = True

    async def send_message(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                           embed: Optional[discord.Embed] = None, ephemeral: bool = False,
                           files: Optional[List[discord.File]] = None, **kwargs) -> None:
        self._done = True
        data = {
            "content": content,
            "view": view,
            "embed": embed,
            "ephemeral": ephemeral,
            "files": files,
            "kwargs": kwargs
        }
        self.interaction.sent_responses.append(data)
        self.interaction.last_response = data

    async def edit_message(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                           attachments: Optional[List[Any]] = None, **kwargs) -> None:
        self._done = True
        data = {
            "content": content,
            "view": view,
            "attachments": attachments,
            "kwargs": kwargs
        }
        self.interaction.edited_responses.append(data)
        self.interaction.last_response = data

    async def send_modal(self, modal: discord.ui.Modal) -> None:
        self._done = True
        self.interaction.sent_modals.append(modal)


class MockInteractionFollowup:
    def __init__(self, interaction: Any):
        self.interaction = interaction

    async def send(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                   embed: Optional[discord.Embed] = None, file: Optional[discord.File] = None,
                   files: Optional[List[discord.File]] = None, ephemeral: bool = False, **kwargs) -> MockMessage:
        data = {
            "content": content,
            "view": view,
            "embed": embed,
            "file": file,
            "files": files,
            "ephemeral": ephemeral,
            "kwargs": kwargs
        }
        self.interaction.sent_followups.append(data)
        self.interaction.last_response = data
        return MockMessage(content=content or "", author=self.interaction.user, guild=self.interaction.guild)

    async def edit_message(self, message_id: Any, content: Optional[str] = None,
                           view: Optional[discord.ui.View] = None, **kwargs) -> None:
        data = {
            "message_id": message_id,
            "content": content,
            "view": view,
            "kwargs": kwargs
        }
        self.interaction.edited_responses.append(data)
        self.interaction.last_response = data


class MockInteraction:
    def __init__(self, user: Optional[Union[MockUser, MockMember]] = None,
                 guild: Optional[MockGuild] = None,
                 channel: Optional[MockChannel] = None,
                 interaction_type: discord.InteractionType = discord.InteractionType.application_command,
                 locale: Union[discord.Locale, str] = discord.Locale.american_english,
                 guild_locale: Optional[Union[discord.Locale, str]] = None):
        self.id = 6001
        self.guild = guild
        self.guild_id = guild.id if guild else None
        self.user = user or (guild.owner if guild else MockUser())
        self.channel = channel or (guild.general_channel if guild else MockTextChannel())
        self.type = interaction_type
        self.locale = locale
        self.guild_locale = guild_locale or locale
        self.response = MockInteractionResponse(self)
        self.followup = MockInteractionFollowup(self)
        self.data: Dict[str, Any] = {}
        self.sent_responses: List[Dict[str, Any]] = []
        self.sent_followups: List[Dict[str, Any]] = []
        self.edited_responses: List[Dict[str, Any]] = []
        self.sent_modals: List[discord.ui.Modal] = []
        self.deferred = False
        self.last_response: Optional[Dict[str, Any]] = None

    async def edit_original_response(self, content: Optional[str] = None, view: Optional[discord.ui.View] = None,
                                     attachments: Optional[List[Any]] = None, **kwargs) -> None:
        data = {
            "content": content,
            "view": view,
            "attachments": attachments,
            "kwargs": kwargs
        }
        self.edited_responses.append(data)
        self.last_response = data


class MockTree:
    def __init__(self):
        self.synced = False

    async def sync(self, guild: Optional[Any] = None) -> List[Any]:
        self.synced = True
        return []


class MockBot(commands.Bot):
    """High-fidelity Mock Bot inheriting commands.Bot for testing."""
    def __init__(self, **kwargs):
        intents = kwargs.pop("intents", discord.Intents.all())
        super().__init__(command_prefix="!", intents=intents, **kwargs)
        self._user_mock = MockUser(id=9999, name="NiteBot", bot=True)
        self.server_settings = default_server_settings
        self._guilds_mock: List[MockGuild] = []
        self._is_closed = False


    @property
    def user(self) -> MockUser:
        return self._user_mock

    @user.setter
    def user(self, val: MockUser):
        self._user_mock = val


    @property
    def guilds(self) -> List[MockGuild]:
        return self._guilds_mock

    def add_mock_guild(self, guild: MockGuild) -> None:
        self._guilds_mock.append(guild)

    def get_guild(self, guild_id: int) -> Optional[MockGuild]:
        for g in self._guilds_mock:
            if g.id == guild_id:
                return g
        return None

    def get_user(self, user_id: int) -> Optional[MockUser]:
        for g in self._guilds_mock:
            m = g.get_member(user_id)
            if m:
                return m
        return None

    async def fetch_user(self, user_id: int) -> MockUser:
        user = self.get_user(user_id)
        if user:
            return user
        return MockUser(id=user_id, name=f"FetchedUser_{user_id}")

    async def fetch_guild(self, guild_id: int, with_counts: bool = True) -> MockGuild:
        guild = self.get_guild(guild_id)
        if guild:
            return guild
        new_g = MockGuild(id=guild_id, name=f"FetchedGuild_{guild_id}")
        self.add_mock_guild(new_g)
        return new_g

    def is_ready(self) -> bool:
        return True

    def is_closed(self) -> bool:
        return self._is_closed

    async def wait_until_ready(self) -> bool:
        return True
