# nite-pebbles/tests/test_pebbles_manifest.py
import pytest
import json
from pathlib import Path

PEBBLES_ROOT = Path(__file__).parent.parent


class TestPebblesManifest:
    @pytest.fixture
    def manifest(self):
        manifest_file = PEBBLES_ROOT / "pebbles.json"
        assert manifest_file.exists(), "pebbles.json must exist in nite-pebbles root"
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def test_manifest_structure(self, manifest):
        assert "people" in manifest, "pebbles.json must contain 'people'"
        assert "entries" in manifest, "pebbles.json must contain 'entries'"
        assert isinstance(manifest["people"], dict)
        assert isinstance(manifest["entries"], list)
        assert len(manifest["entries"]) > 0

    def test_people_schema(self, manifest):
        for person_id, person_info in manifest["people"].items():
            assert "name" in person_info, f"Person {person_id} missing 'name'"
            assert isinstance(person_info["name"], str)

    def test_entries_schema_and_file_existence(self, manifest):
        known_people = set(manifest["people"].keys())

        for entry in manifest["entries"]:
            assert "extension_file" in entry, "Entry missing 'extension_file'"
            assert "name" in entry, "Entry missing 'name'"
            assert "description" in entry, "Entry missing 'description'"
            assert "dependencies" in entry, "Entry missing 'dependencies'"
            assert "credits" in entry, "Entry missing 'credits'"

            assert isinstance(entry["dependencies"], list)
            assert isinstance(entry["credits"], dict)

            # Check that extension file actually exists in nite-pebbles
            ext_path = entry["extension_file"].replace(".", "/") + ".py"
            full_path = PEBBLES_ROOT / ext_path
            assert full_path.exists(), f"Extension file '{ext_path}' does not exist in nite-pebbles"

            # Check credits
            assert "Creators" in entry["credits"]
            assert "Contributers" in entry["credits"]

            for creator in entry["credits"]["Creators"]:
                assert "id" in creator or "name" in creator
                if "id" in creator:
                    assert creator["id"] in known_people, f"Creator ID '{creator['id']}' not in people"

            for contributor in entry["credits"]["Contributers"]:
                assert "id" in contributor or "name" in contributor
                if "id" in contributor:
                    assert contributor["id"] in known_people, f"Contributor ID '{contributor['id']}' not in people"
