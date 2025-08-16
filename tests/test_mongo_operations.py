import unittest
from unittest.mock import patch, MagicMock
from bson import ObjectId
import utils
from counter import UserCharacter, Counter
from health import Health, DamageEnum, HealthTypeEnum, HEALTH_LEVELS, \
    display_health  # Fix NameError by importing Health-related classes

# Mock ObjectId for testing
class MockObjectId:
    def __init__(self, oid=None):
        self.oid = oid or "mock_object_id"

    def __str__(self):
        return self.oid

# Test MongoDB operations
class TestMongoOperations(unittest.TestCase):
    def setUp(self):
        # Create mock collection
        self.mock_collection = MagicMock()

        # Create mock ObjectId
        self.mock_object_id = MockObjectId

        # Set up patch for MongoDB operations
        self.patch_collection = patch('utils.characters_collection', self.mock_collection)
        self.patch_object_id = patch('bson.ObjectId', self.mock_object_id)

        # Start patches
        self.patch_collection.start()
        self.patch_object_id.start()

    def tearDown(self):
        # Stop patches
        self.patch_collection.stop()
        self.patch_object_id.stop()

    def test_add_user_character(self):
        # Configure mock
        self.mock_collection.find_one.return_value = None
        self.mock_collection.count_documents.return_value = 0

        # Test adding a character
        success, error = utils.add_user_character("user123", "Test Character")
        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.insert_one.assert_called_once()

        # Test with character limit reached
        self.mock_collection.count_documents.return_value = utils.MAX_USER_CHARACTERS
        success, error = utils.add_user_character("user123", "Another Character")
        self.assertFalse(success)
        self.assertTrue("maximum number" in error)

        # Test with existing character
        self.mock_collection.count_documents.return_value = 0
        self.mock_collection.find_one.return_value = {"character": "Test Character"}
        success, error = utils.add_user_character("user123", "Test Character")
        self.assertFalse(success)
        self.assertTrue("already exists" in error)

    def test_get_all_user_characters_for_user(self):
        # Configure mock
        self.mock_collection.find.return_value = [
            {"_id": "id1", "user": "user123", "character": "Character 1", "counters": [], "health": []},
            {"_id": "id2", "user": "user123", "character": "Character 2", "counters": [{"counter": "test"}], "health": []}
        ]

        # Get characters
        characters = utils.get_all_user_characters_for_user("user123")

        # Assertions
        self.assertEqual(len(characters), 2)
        self.assertIsInstance(characters[0], UserCharacter)
        self.assertEqual(characters[0].character, "Character 1")
        self.assertEqual(characters[1].character, "Character 2")
        self.assertEqual(len(characters[1].counters), 1)

    def test_add_counter(self):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        # Configure mock
        char_doc = {
            "_id": ObjectId(valid_object_id),
            "user": "user123",
            "character": "Test Character",
            "counters": []
        }
        self.mock_collection.find_one.return_value = char_doc

        # Ensure character_id is obtained via get_character_id_by_user_and_name
        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test adding a counter
        success, error = utils.add_counter(character_id, "Test Counter", 5, 10)

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Test with counter limit reached
        char_doc["counters"] = [{"counter": f"Counter {i}"} for i in range(utils.MAX_COUNTERS_PER_CHARACTER)]
        self.mock_collection.find_one.return_value = char_doc
        success, error = utils.add_counter(character_id, "Another Counter", 5, 10)
        self.assertFalse(success)
        self.assertTrue("maximum number" in error)

        # Test with existing counter
        char_doc["counters"] = [{"counter": "Test Counter"}]
        self.mock_collection.find_one.return_value = char_doc
        success, error = utils.add_counter(character_id, "Test Counter", 5, 10)
        self.assertFalse(success)

    def test_remove_counter(self):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        # Configure mock
        char_doc = {
            "_id": ObjectId(valid_object_id),
            "user": "user123",
            "character": "Test Character",
            "counters": [
                {"counter": "Willpower", "temp": 5, "perm": 10, "category": "tempers"}
            ]
        }
        self.mock_collection.find_one.return_value = char_doc

        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test removing a counter
        success, error, details = utils.remove_counter(character_id, "Willpower")

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(details)
        self.mock_collection.update_one.assert_called_once()

        # Test with nonexistent counter
        success, error, details = utils.remove_counter(character_id, "Nonexistent")
        self.assertTrue(success)  # Should succeed even if counter not found
        self.assertIsNone(error)

    def test_rename_counter(self):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        # Configure mock
        char_doc = {
            "_id": ObjectId(valid_object_id),
            "user": "user123",
            "character": "Test Character",
            "counters": [
                {"counter": "Old Counter", "temp": 5, "perm": 10}
            ]
        }
        self.mock_collection.find_one.return_value = char_doc

        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test renaming a counter
        success, error = utils.rename_counter(character_id, "Old Counter", "New Counter")

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Test with duplicate counter name
        char_doc["counters"].append({"counter": "New Counter"})
        self.mock_collection.find_one.return_value = char_doc
        success, error = utils.rename_counter(character_id, "Old Counter", "New Counter")
        self.assertFalse(success)
        self.assertTrue("already exists" in error)

        # Test with nonexistent counter
        success, error = utils.rename_counter(character_id, "Nonexistent", "New Name")
        self.assertFalse(success)
        self.assertTrue("not found" in error)

    def test_update_counter(self):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        # Configure mock with a counter
        char_doc = {
            "_id": ObjectId(valid_object_id),
            "user": "user123",
            "character": "Test Character",
            "counters": [
                {"counter": "Willpower", "temp": 5, "perm": 10, "counter_type": "perm_is_maximum"}
            ]
        }
        self.mock_collection.find_one.return_value = char_doc

        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test updating temp (increment within perm)
        success, error = utils.update_counter(character_id, "Willpower", "temp", 2)
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(char_doc["counters"][0]["temp"], 7)

        # Test incrementing temp above perm (should set temp to perm)
        success, error = utils.update_counter(character_id, "Willpower", "temp", 10)
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(char_doc["counters"][0]["temp"], 10)  # Should not exceed perm

        # Test decrementing temp below zero (should fail and not change temp)
        success, error = utils.update_counter(character_id, "Willpower", "temp", -20)
        self.assertFalse(success)
        self.assertTrue("cannot be below zero" in error)
        self.assertEqual(char_doc["counters"][0]["temp"], 10)  # Should remain unchanged

        # Test decrementing perm below zero (should not change perm)
        success, error = utils.update_counter(character_id, "Willpower", "perm", -15)
        self.assertFalse(success)
        self.assertTrue("cannot be below zero" in error)
        self.assertEqual(char_doc["counters"][0]["perm"], 10)  # Should not go below zero

    def test_remove_character(self):
        # Configure mock
        self.mock_collection.find_one.return_value = {
            "_id": "mock_object_id",
            "user": "user123",
            "character": "Test Character",
            "counters": [{"counter": "Willpower", "temp": 5, "perm": 10}]
        }

        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test removing a character
        success, error, details = utils.remove_character("user123", "Test Character")

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(details)
        self.mock_collection.delete_one.assert_called_once()

        # Test with nonexistent character
        self.mock_collection.find_one.return_value = None
        success, error, details = utils.remove_character("user123", "Nonexistent")
        self.assertFalse(success)
        self.assertTrue("not found" in error)

    def test_rename_character(self):
        user_id = "test_user_rename"
        character_name = "Old Name"

        # Configure mock for character creation
        self.mock_collection.find_one.return_value = None
        self.mock_collection.count_documents.return_value = 0

        # Create the character exactly as in test_add_user_character
        success, error = utils.add_user_character(user_id, character_name)
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.insert_one.assert_called_once()

        # Validate it was created the same way
        self.mock_collection.find_one.return_value = {"_id": "mock_object_id", "user": user_id, "character": character_name}
        character_id = utils.get_character_id_by_user_and_name(user_id, character_name)
        self.assertIsNotNone(character_id)
        self.assertEqual(character_id, "mock_object_id")

        # Now test renaming
        self.mock_collection.find_one.side_effect = [
            {"_id": "mock_object_id", "user": user_id, "character": character_name},
            None
        ]
        success, error = utils.rename_character(user_id, character_name, "New Name")
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Test with nonexistent character
        self.mock_collection.find_one.side_effect = [None]
        success, error = utils.rename_character(user_id, "Nonexistent", "New Name")
        self.assertFalse(success)
        self.assertTrue("not found" in error)

        # Test with duplicate name
        self.mock_collection.find_one.side_effect = [
            {"_id": "mock_object_id", "user": user_id, "character": character_name},
            {"_id": "other_id", "user": user_id, "character": "New Name"}
        ]
        success, error = utils.rename_character(user_id, character_name, "New Name")
        self.assertFalse(success)
        self.assertTrue("already exists" in error)

    def test_init(self):
        health = Health(HealthTypeEnum.normal.value)  # Fix NameError

        # Test with default values
        self.assertEqual(health.health_type, HealthTypeEnum.normal.value)
        self.assertEqual(health.damage, [])
        self.assertEqual(health.health_levels, list(HEALTH_LEVELS.keys()))

        # Test with provided values
        damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value]
        health_levels = ["Level1", "Level2"]
        health = Health(HealthTypeEnum.chimerical.value, damage, health_levels)
        self.assertEqual(health.health_type, HealthTypeEnum.chimerical.value)
        self.assertEqual(health.damage, damage)
        self.assertEqual(health.health_levels, health_levels)

    def test_set_health_levels(self):
        health = Health(HealthTypeEnum.normal.value)
        custom_levels = ["Custom1", "Custom2", "Custom3"]
        health.set_health_levels(custom_levels)
        self.assertEqual(health.health_levels, custom_levels)

    def test_add_damage_to_empty_slots(self):
        health = Health(HealthTypeEnum.normal.value)  # Fix NameError
        # Add 3 damage to empty health track
        added, remaining = health._add_damage_to_empty_slots(3, DamageEnum.Bashing, 7)
        self.assertEqual(added, 3)
        self.assertEqual(remaining, 0)
        self.assertEqual(health.damage, [DamageEnum.Bashing.value] * 3)

        # Add more damage than slots available
        health = Health(HealthTypeEnum.normal.value)
        added, remaining = health._add_damage_to_empty_slots(10, DamageEnum.Bashing, 7)
        self.assertEqual(added, 7)
        self.assertEqual(remaining, 3)
        self.assertEqual(len(health.damage), 7)

    # def test_upgrade_existing_damage(self):
    #     # Set up health with bashing damage
    #     health = Health(HealthTypeEnum.normal.value)
    #     health.damage = [DamageEnum.Bashing.value] * 7
    #
    #     # Upgrade bashing to lethal
    #     converted, not_taken = health._upgrade_existing_damage(2, DamageEnum.Lethal)
    #     self.assertEqual(converted, 2)
    #     self.assertEqual(not_taken, 0)
    #     # First two damages should be upgraded
    #     self.assertEqual(health.damage[0], DamageEnum.Lethal.value)
    #     self.assertEqual(health.damage[1], DamageEnum.Lethal.value)
    #     self.assertEqual(health.damage[2], DamageEnum.Bashing.value)
    #
    #     health.damage = [DamageEnum.Bashing.value] * 7
    #     converted, not_taken = health._upgrade_existing_damage(3, DamageEnum.Lethal)
    #
    #     # Upgrade more than available
    #     converted, not_taken = health._upgrade_existing_damage(4, DamageEnum.Aggravated)
    #     self.assertEqual(converted, 3)  # Only 3 to convert
    #     self.assertEqual(not_taken, 1)
    #     # All damage should be upgraded
    #     self.assertEqual(health.damage, [DamageEnum.Aggravated.value] * 3)

    # def test_add_damage(self):
    #     health = Health(HealthTypeEnum.normal.value)
    #
    #     # Add bashing damage
    #     result = health.add_damage(3, DamageEnum.Bashing)
    #     self.assertIsNone(result)  # No message when damage is taken
    #     self.assertEqual(health.damage, [DamageEnum.Bashing.value] * 3)
    #
    #     # Add lethal damage, should upgrade some bashing
    #     result = health.add_damage(2, DamageEnum.Lethal)
    #     self.assertIsNone(result)
    #     self.assertEqual(health.damage.count(DamageEnum.Lethal.value), 2)
    #     self.assertEqual(health.damage.count(DamageEnum.Bashing.value), 3)
    #
    #     # Fill the health track
    #     health = Health(HealthTypeEnum.normal.value)
    #     health.health_levels = ["Level1", "Level2", "Level3"]  # Only 3 health levels
    #
    #     # Add more damage than health track can hold
    #     result = health.add_damage(5, DamageEnum.Bashing)
    #     self.assertIsNotNone(result)  # Should get a message
    #     self.assertTrue("2 additional levels" in result)
    #     self.assertEqual(len(health.damage), 3)  # Only 3 damage recorded

    def test_remove_damage(self):
        health = Health(HealthTypeEnum.normal.value)  # Fix NameError
        health.damage = [
            DamageEnum.Aggravated.value,
            DamageEnum.Lethal.value,
            DamageEnum.Bashing.value
        ]

        # Remove 2 damage
        health.remove_damage(2)
        self.assertEqual(health.damage, [DamageEnum.Aggravated.value])

        # Remove more than exists
        health.remove_damage(5)
        self.assertEqual(health.damage, [])

    def test_map_damage_to_health(self):
        health = Health(HealthTypeEnum.normal.value)  # Fix NameError
        health.damage = [
            DamageEnum.Aggravated.value,
            DamageEnum.Lethal.value
        ]

        # First seven health levels from standard list
        expected_first_health_level = {
            'health_level': list(HEALTH_LEVELS.keys())[0],
            'damage_type': DamageEnum.Aggravated.value,
            'penalty': HEALTH_LEVELS[list(HEALTH_LEVELS.keys())[0]]
        }

        # Map damage
        result = health.map_damage_to_health()
        self.assertEqual(len(result), len(health.health_levels))
        self.assertEqual(result[0], expected_first_health_level)
        self.assertEqual(result[1]['damage_type'], DamageEnum.Lethal.value)
        self.assertIsNone(result[2]['damage_type'])  # No damage at this level

    def test_display(self):
        normal_health = Health(HealthTypeEnum.normal.value)  # Fix NameError
        normal_health.damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value]

        # Display should not be empty
        result = normal_health.display()
        self.assertTrue(len(result) > 0)

        # Test display with normal and chimerical health
        all_health = [
            {"health_type": "normal", "damage": [DamageEnum.Bashing.value]},
            {"health_type": "chimerical", "damage": [DamageEnum.Lethal.value, DamageEnum.Lethal.value]}
        ]
        result = normal_health.display(all_health)
        self.assertTrue(len(result) > 0)
        self.assertTrue(":blue_square: :regional_indicator_c:" in result)  # Header for chimerical health

class TestDisplayHealth(unittest.TestCase):
    def test_display_health_normal_only(self):
        normal_health = Health(HealthTypeEnum.normal.value)
        normal_health.damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value]

        result = display_health(normal_health)
        self.assertTrue(":regional_indicator_b: Bruised" in result)
        self.assertTrue(":regional_indicator_l: Hurt" in result)
        self.assertTrue(":stop_button: Injured" in result)

    def test_display_health_with_chimerical(self):
        normal_health = Health(HealthTypeEnum.normal.value)
        normal_health.damage = [DamageEnum.Bashing.value]

        chimerical_health = Health(HealthTypeEnum.chimerical.value)
        chimerical_health.damage = [DamageEnum.Lethal.value, DamageEnum.Aggravated.value]

        result = display_health(normal_health, chimerical_health)
        self.assertTrue(":blue_square: :regional_indicator_c:" in result)  # Header
        self.assertTrue(":regional_indicator_b: :regional_indicator_l: Bruised" in result)
        self.assertTrue(":stop_button: :regional_indicator_a: Hurt" in result)

if __name__ == "__main__":
    unittest.main()
