# nite-pebbles/testing/mocks/locales/__init__.py
import json
from pathlib import Path

def get_string(key, lang="en", **kwargs):
    locales_dir = Path(__file__).parent.parent.parent.parent / "locales"
    path = locales_dir / f"{lang}.json"
    
    if not path.exists():
        path = locales_dir / "en.json"
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        parts = key.split(".")
        val = data
        for part in parts:
            val = val.get(part, {})
        
        if not isinstance(val, str):
            if lang != "en":
                return get_string(key, "en", **kwargs)
            return key
            
        return val.format(**kwargs)
    except Exception as e:
        return f"[{key}]"

def get_list(key, lang="en", **kwargs):
    return []

async def resolve_locale(interaction):
    return "en"

def get_localized(interaction, key, **kwargs):
    return get_string(key, "en", **kwargs)
