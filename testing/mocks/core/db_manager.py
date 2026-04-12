# nite-pebbles/testing/mocks/core/db_manager.py
# --- MOCK DATABASE MANAGER ---
# This is a mock implementation for testing Pebbles without the real PostgreSQL database.
# It saves everything to a local 'test_db.json' file.

import json
import os
import asyncio
from pathlib import Path
from typing import Optional, Any, Dict, Union, List

class MockDBManager:
    def __init__(self, filename="test_db.json"):
        self.filename = Path(__file__).parent.parent.parent / filename
        self.enabled = True
        self.data = self._load()

    def _load(self):
        if self.filename.exists():
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"global": {}, "users": {}}

    def _save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # --- User Info ---
    async def get_user_info(self, user_id: int, keys: Union[str, List[str]] = None) -> Any:
        user_data = self.data["users"].get(str(user_id), {})
        if isinstance(keys, str):
            return user_data.get(keys)
        elif isinstance(keys, list):
            return {k: user_data.get(k) for k in keys}
        return user_data

    async def save_user_info(self, user_id: int, key_or_dict: Union[str, Dict[str, Any]], value: Any = None):
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {}
        
        if isinstance(key_or_dict, dict):
            self.data["users"][uid].update(key_or_dict)
        else:
            self.data["users"][uid][key_or_dict] = value
        self._save()

    # --- Global Data ---
    async def get_global_data(self, keys: Union[str, List[str]]) -> Any:
        if isinstance(keys, list):
            return {k: self.data["global"].get(k) for k in keys}
        return self.data["global"].get(keys)

    async def save_global_data(self, key_or_dict: Union[str, Dict[str, Any]], value: Any = None):
        if isinstance(key_or_dict, dict):
            self.data["global"].update(key_or_dict)
        else:
            self.data["global"][key_or_dict] = value
        self._save()

    async def connect(self): return True
    async def close(self): pass

db = MockDBManager()
