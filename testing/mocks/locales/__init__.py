# nite-pebbles/testing/mocks/locales/__init__.py
# --- MOCK LOCALES ---
# This loads translations from the REAL nite-pebbles/locales/*.json files.

import json
from pathlib import Path

def get_string(key, lang="en", **kwargs):
    # Path to nite-pebbles/locales/
    locales_dir = Path(__file__).parent.parent.parent.parent / "locales"
    path = locales_dir / f"{lang}.json"
    
    # Fallback to English
    if not path.exists():
        path = locales_dir / "en.json"
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Traverse key (e.g., "ui.buttons.accept")
        parts = key.split(".")
        val = data
        for part in parts:
            val = val.get(part, {})
        
        if not isinstance(val, str):
            # If not found, try English fallback within the dictionary
            if lang != "en":
                return get_string(key, "en", **kwargs)
            return key
            
        return val.format(**kwargs)
    except Exception as e:
        return f"[{key}]"
