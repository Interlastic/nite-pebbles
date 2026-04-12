# nite-pebbles/testing/mocks/core/server_settings.py
# --- MOCK SERVER SETTINGS ---
# This is a mock implementation for testing Pebbles without the real settings system.
# It uses the local 'test_settings/' folder for storage.

import os
import json
from pathlib import Path
from typing import Optional

class MockServerSettings:
    def __init__(self, settings_dir="test_settings"):
        self.settings_dir = Path(__file__).parent.parent.parent / settings_dir
        self.settings_dir.mkdir(exist_ok=True)

    def _get_path(self, server_id: int):
        return self.settings_dir / f"{server_id}.json"

    async def get_settings(self, server_id: int) -> dict:
        path = self._get_path(server_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"language": "en"}

    async def update_settings(self, server_id: int, new_settings: dict):
        path = self._get_path(server_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_settings, f, indent=4)

    async def get_language(self, server_id: Optional[int]) -> str:
        if server_id is None: return "en"
        settings = await self.get_settings(server_id)
        return settings.get("language", "en")

    async def start(self): pass

server_settings = MockServerSettings()
