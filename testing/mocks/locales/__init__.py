# nite-pebbles/testing/mocks/locales/__init__.py
# --- MOCK LOCALES ---
# High-fidelity standalone localization mock for nite-pebbles testing.
# Loads translations directly from nite-pebbles/locales/*.json.

import json
from pathlib import Path
from typing import Any, Optional, Union
import discord

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "de", "pl"]

DISCORD_LOCALE_MAP = {
    discord.Locale.german: "de",
    discord.Locale.polish: "pl",
    discord.Locale.british_english: "en",
    discord.Locale.american_english: "en",
}

# Cache for loaded JSON locales
_pebble_cache: dict[str, dict] = {}

PEBBLE_LOCALES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "locales"



def _get_nested(data: dict, key: str, default: Any = None) -> Any:
    """Get a nested value from a dictionary using dot notation."""
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
        if value is None:
            return default
    return value


def load_language(lang: str) -> dict:
    """Load a language JSON and cache it."""
    return load_pebble_language(lang)


def load_pebble_language(lang: str) -> dict:
    """Load a Pebble JSON language file and cache it."""
    if lang in _pebble_cache:
        return _pebble_cache[lang]

    json_path = PEBBLE_LOCALES_DIR / f"{lang}.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _pebble_cache[lang] = data
                return data
        except Exception:
            pass

    # Fallback to English if not found
    if lang != DEFAULT_LANGUAGE:
        return load_pebble_language(DEFAULT_LANGUAGE)

    return {}


async def resolve_locale(context: Any) -> str:
    """
    Resolve the best language for a context based on:
    1. User override (from mock DB)
    2. Discord locale
    3. Guild setting
    4. Default (en)
    """
    try:
        from core.db_manager import db
        from core.server_settings import server_settings
    except ImportError:
        db = None
        server_settings = None

    user_id = None
    guild_id = None
    interaction_locale = None
    guild_locale = None

    if isinstance(context, discord.Interaction):
        user_id = context.user.id if context.user else None
        guild_id = context.guild_id or (context.guild.id if context.guild else None)
        interaction_locale = context.locale
        guild_locale = context.guild_locale
    elif isinstance(context, discord.Message):
        user_id = context.author.id if context.author else None
        guild_id = context.guild.id if context.guild else None
    elif isinstance(context, (discord.Member, discord.User)):
        user_id = context.id
        if isinstance(context, discord.Member) and context.guild:
            guild_id = context.guild.id
    elif isinstance(context, discord.Guild):
        guild_id = context.id
    else:
        user_id = getattr(getattr(context, "user", None), "id", None) or getattr(getattr(context, "author", None), "id", None)
        guild_id = getattr(getattr(context, "guild", None), "id", None) or getattr(context, "guild_id", None)
        interaction_locale = getattr(context, "locale", None)
        guild_locale = getattr(context, "guild_locale", None)

    # 1. Check User Override in DB
    if user_id and db:
        try:
            user_pref = await db.get_user_info(user_id, "language_override")
            if user_pref and user_pref != "dynamic" and user_pref in SUPPORTED_LANGUAGES:
                return user_pref
        except Exception:
            pass

    # 2. Check Discord Locale
    if interaction_locale:
        if interaction_locale in DISCORD_LOCALE_MAP:
            return DISCORD_LOCALE_MAP[interaction_locale]
        locale_str = str(interaction_locale).split("-")[0].lower()
        if locale_str in SUPPORTED_LANGUAGES:
            return locale_str

    if guild_locale:
        if guild_locale in DISCORD_LOCALE_MAP:
            return DISCORD_LOCALE_MAP[guild_locale]
        locale_str = str(guild_locale).split("-")[0].lower()
        if locale_str in SUPPORTED_LANGUAGES:
            return locale_str

    # 3. Check Guild Setting
    if guild_id and server_settings:
        try:
            guild_lang = await server_settings.get_language(guild_id)
            if guild_lang in SUPPORTED_LANGUAGES:
                return guild_lang
        except Exception:
            pass

    return DEFAULT_LANGUAGE


def get_string(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Get a localized string by key with optional interpolation."""
    if not lang or lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    data = load_pebble_language(lang)
    value = _get_nested(data, key)

    # Fallback to English if not found
    if value is None and lang != DEFAULT_LANGUAGE:
        en_data = load_pebble_language(DEFAULT_LANGUAGE)
        value = _get_nested(en_data, key)

    if value is None:
        return f"[{key}]"

    if isinstance(value, str):
        value = value.replace("\\n", "\n")
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value

    return str(value)


async def get_localized(interaction: discord.Interaction, key: str, **kwargs) -> str:
    """Shorthand to resolve locale and get a localized string in one call."""
    lang = await resolve_locale(interaction)
    return get_string(key, lang, **kwargs)


def get_list(key: str, lang: str = DEFAULT_LANGUAGE) -> list:
    """Get a localized list of strings."""
    if not lang or lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    data = load_pebble_language(lang)
    value = _get_nested(data, key)

    if value is None and lang != DEFAULT_LANGUAGE:
        en_data = load_pebble_language(DEFAULT_LANGUAGE)
        value = _get_nested(en_data, key)

    if isinstance(value, list):
        return value
    return []


def clear_cache():
    """Clear the cached language files."""
    global _pebble_cache
    _pebble_cache = {}


_ = get_string

