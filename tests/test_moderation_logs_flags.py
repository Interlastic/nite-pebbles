# nite-pebbles/tests/test_moderation_logs_flags.py
import pytest
from moderation_logs.ui import LoggingFlags, PRESETS


class TestModerationLogsFlags:
    def test_flag_uniqueness(self):
        flag_values = [flag.value for flag in LoggingFlags]
        assert len(flag_values) == len(set(flag_values)), "Every LoggingFlag must have a unique power-of-2 value"

    def test_bitwise_flag_combinations(self):
        combined = LoggingFlags.MESSAGE_CREATE | LoggingFlags.MESSAGE_DELETE | LoggingFlags.MEMBER_JOIN
        assert combined & LoggingFlags.MESSAGE_CREATE
        assert combined & LoggingFlags.MESSAGE_DELETE
        assert combined & LoggingFlags.MEMBER_JOIN
        assert not (combined & LoggingFlags.ROLE_CREATE)

    def test_bitwise_flag_removal(self):
        combined = LoggingFlags.MESSAGE_CREATE | LoggingFlags.MESSAGE_DELETE
        modified = combined & ~LoggingFlags.MESSAGE_CREATE
        assert not (modified & LoggingFlags.MESSAGE_CREATE)
        assert modified & LoggingFlags.MESSAGE_DELETE

    def test_preset_essential(self):
        essential = PRESETS["essential"]
        assert essential & LoggingFlags.MEMBER_JOIN
        assert essential & LoggingFlags.MEMBER_LEAVE_KICK
        assert essential & LoggingFlags.MEMBER_BAN_UNBAN
        assert essential & LoggingFlags.ROLE_CREATE
        assert essential & LoggingFlags.ROLE_UPDATE
        assert essential & LoggingFlags.ROLE_DELETE
        assert essential & LoggingFlags.CHANNEL_CREATE
        assert essential & LoggingFlags.CHANNEL_UPDATE
        assert essential & LoggingFlags.CHANNEL_DELETE
        assert essential & LoggingFlags.GUILD_UPDATE

        # Essential should not include optional voice effects
        assert not (essential & LoggingFlags.VOICE_EFFECT)

    def test_preset_moderate(self):
        moderate = PRESETS["moderate"]
        essential = PRESETS["essential"]
        # Moderate must contain everything essential has plus messages/threads
        assert (moderate & essential) == essential
        assert moderate & LoggingFlags.MESSAGE_EDIT
        assert moderate & LoggingFlags.MESSAGE_DELETE
        assert moderate & LoggingFlags.THREAD_CREATE

    def test_preset_clear(self):
        assert PRESETS["clear"] == 0

    def test_preset_everything(self):
        everything = PRESETS["everything"]
        for flag in LoggingFlags:
            assert everything & flag == flag
