# nite-pebbles/tests/test_zero_leakage.py
import ast
import os
import sys
from pathlib import Path
import pytest

PEBBLES_DIR = Path(__file__).resolve().parent.parent


def get_all_pebble_python_files():
    py_files = []
    for root, dirs, files in os.walk(PEBBLES_DIR):
        if any(ignored in root for ignored in [".git", "__pycache__", ".pytest_cache"]):
            continue
        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)
    return py_files


class TestZeroLeakage:
    def test_sys_path_isolation(self):
        """Assert that parent directory is not in sys.path during testing."""
        parent_dir = str(PEBBLES_DIR.parent.resolve())
        # The parent directory itself must not be in sys.path
        assert parent_dir not in sys.path, f"Parent repository directory '{parent_dir}' found in sys.path"

    def test_all_modules_contained_within_pebbles(self):
        """Assert that no non-pebble modules from the parent repository are loaded."""
        parent_dir = PEBBLES_DIR.parent.resolve()
        for name, mod in list(sys.modules.items()):
            if not mod or not hasattr(mod, "__file__") or not mod.__file__:
                continue
            mod_path = Path(mod.__file__).resolve()
            # If the module is located under the parent repository directory, it MUST be inside nite-pebbles/
            if parent_dir in mod_path.parents or mod_path == parent_dir:
                assert PEBBLES_DIR in mod_path.parents or mod_path == PEBBLES_DIR or mod_path.is_relative_to(PEBBLES_DIR), (
                    f"Module '{name}' was loaded from parent repository outside pebbles: {mod_path}"
                )


    def test_no_hardcoded_user_paths(self):
        """Ensure no hardcoded absolute user environment paths in pebble source files."""
        py_files = get_all_pebble_python_files()
        banned_prefixes = ["/home/", "/Users/", "C:\\Users\\"]

        violations = []
        for file_path in py_files:
            if file_path.name == "test_zero_leakage.py":
                continue
            content = file_path.read_text(encoding="utf-8")
            for prefix in banned_prefixes:
                if prefix in content:
                    violations.append(f"{file_path.relative_to(PEBBLES_DIR)} contains hardcoded path prefix '{prefix}'")

        assert not violations, f"Hardcoded environment path references detected:\n" + "\n".join(violations)

