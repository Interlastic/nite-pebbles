# nite-pebbles/testing/mocks/core/server_settings.py
# --- MOCK SERVER SETTINGS ---
# Standalone mock implementation for testing Pebbles without the real settings system.
# Supports in-memory caching for tests and optional local JSON storage.

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class MockServerSettings:
    def __init__(self, settings_dir=None):
        if settings_dir:
            self.settings_dir = Path(__file__).parent.parent.parent / settings_dir
            self.settings_dir.mkdir(exist_ok=True)
        else:
            self.settings_dir = None
        self._cache: Dict[int, dict] = {}

    def _get_path(self, server_id: int):
        if self.settings_dir:
            return self.settings_dir / f"{server_id}.json"
        return None

    def reset(self):
        """Reset all in-memory and disk settings to clean defaults."""
        self._cache = {}
        if self.settings_dir and self.settings_dir.exists():
            for f in self.settings_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass

    async def get_settings(self, server_id: int) -> dict:
        if server_id in self._cache:
            return dict(self._cache[server_id])

        path = self._get_path(server_id)
        if path and path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache[server_id] = data
                    return dict(data)
            except Exception:
                pass

        default_data = {"language": "en"}
        self._cache[server_id] = dict(default_data)
        return dict(default_data)

    async def update_settings(self, server_id: int, new_settings: dict):
        self._cache[server_id] = dict(new_settings)
        path = self._get_path(server_id)
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(new_settings, f, indent=4)
            except Exception:
                pass

    async def get_language(self, server_id: Optional[int]) -> str:
        if server_id is None:
            return "en"
        settings = await self.get_settings(server_id)
        return settings.get("language", "en")

    async def start(self):
        pass


server_settings = MockServerSettings()

