import pytest
from utils import add_health_level
from bson import ObjectId
from health import Health, DamageEnum


class FakeCharacterRepository:
    def __init__(self):
        self.data = {}

    def find_one(self, query):
        return self.data.get(str(query["_id"]))

    def update_one(self, query, update):
        char_id = str(query["_id"])
        if char_id in self.data:
            self.data[char_id].update(update["$set"])


@pytest.fixture
def fake_character_repository(monkeypatch):
    repo = FakeCharacterRepository()
    monkeypatch.setattr("utils.CharacterRepository", repo)
    return repo


def test_add_health_level_sorting(fake_character_repository):
    # Setup a fake character with a health tracker
    character_id = ObjectId()
    fake_character_repository.data[str(character_id)] = {
        "_id": character_id,
        "health": [
            {
                "health_type": "normal",
                "health_levels": ["Wounded", "Bruised", "Injured"],
            }
        ],
    }

    # Add a new health level and verify sorting
    success, error = add_health_level(str(character_id), "normal", "Hurt")
    assert success, f"Failed to add health level: {error}"

    updated_health = fake_character_repository.data[str(character_id)]["health"][0]
    assert updated_health["health_levels"] == [
        "Bruised",
        "Hurt",
        "Injured",
        "Wounded",
    ], "Health levels were not sorted correctly."


def test_add_health_level_with_duplicates(fake_character_repository):
    # Setup a fake character with a health tracker
    character_id = ObjectId()
    fake_character_repository.data[str(character_id)] = {
        "_id": character_id,
        "health": [
            {
                "health_type": "normal",
                "health_levels": ["Bruised", "Hurt", "Hurt", "Injured"],
            }
        ],
    }

    # Add a duplicate health level and verify sorting
    success, error = add_health_level(str(character_id), "normal", "Hurt")
    assert success, f"Failed to add health level: {error}"

    updated_health = fake_character_repository.data[str(character_id)]["health"][0]
    assert updated_health["health_levels"] == [
        "Bruised",
        "Hurt",
        "Hurt",
        "Hurt",
        "Injured",
    ], "Health levels with duplicates were not sorted correctly."


def test_add_health_level_invalid_type(fake_character_repository):
    # Setup a fake character with a health tracker
    character_id = ObjectId()
    fake_character_repository.data[str(character_id)] = {
        "_id": character_id,
        "health": [
            {
                "health_type": "normal",
                "health_levels": ["Bruised", "Hurt", "Injured"],
            }
        ],
    }

    # Add an invalid health level and verify failure
    success, error = add_health_level(str(character_id), "normal", "InvalidLevel")
    assert not success, "Adding an invalid health level should fail."
    assert error == "Invalid health level type: InvalidLevel", (
        "Unexpected error message."
    )


def test_add_damage_sorts_damage(fake_character_repository):
    # Create a health object
    health = Health(health_type="normal", health_levels=["Bruised", "Hurt", "Injured"])

    # Add damage in a random order
    health.add_damage(1, DamageEnum.Lethal)
    health.add_damage(1, DamageEnum.Bashing)
    health.add_damage(1, DamageEnum.Aggravated)

    # Verify that damage is sorted in the order of DamageEnum
    assert health.damage == [
        DamageEnum.Aggravated.value,
        DamageEnum.Lethal.value,
        DamageEnum.Bashing.value,
    ]


def test_add_damage_preserves_duplicates_and_sorts(fake_character_repository):
    # Create a health object with enough health levels to accommodate all damage
    health = Health(
        health_type="normal",
        health_levels=["Bruised", "Hurt", "Injured", "Wounded", "Mauled"],
    )

    # Add duplicate damage types in a random order
    health.add_damage(2, DamageEnum.Bashing)
    health.add_damage(1, DamageEnum.Lethal)
    health.add_damage(2, DamageEnum.Aggravated)

    # Verify that duplicates are preserved and damage is sorted
    assert health.damage == [
        DamageEnum.Aggravated.value,
        DamageEnum.Aggravated.value,
        DamageEnum.Lethal.value,
        DamageEnum.Bashing.value,
        DamageEnum.Bashing.value,
    ]
