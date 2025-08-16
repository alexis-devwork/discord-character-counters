import unittest
from unittest.mock import patch, MagicMock

import utils
from counter import UserCharacter, Counter
from health import Health, DamageEnum, HealthTypeEnum, HEALTH_LEVELS, display_health

# Patch ObjectId globally for this test file
from bson import ObjectId as RealObjectId
def fake_objectid(oid=None):
    # Always return a valid ObjectId string
    return str(oid) if oid else "507f1f77bcf86cd799439011"

ObjectId = fake_objectid

# Test MongoDB operations
class TestMongoOperations(unittest.TestCase):
    def setUp(self):
        # Patch utils to use our fake ObjectId
        patcher = patch('utils.ObjectId', fake_objectid)
        self.objectid_patch = patcher
        self.objectid_patch.start()

        # Create mock collection
        self.mock_collection = MagicMock()
        self.patch_collection = patch('utils.characters_collection', self.mock_collection)
        self.patch_collection.start()

    def tearDown(self):
        self.patch_collection.stop()
        self.objectid_patch.stop()

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
        valid_object_id = "507f1f77bcf86cd799439011"

        # Ensure character_id is obtained via get_character_id_by_user_and_name
        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")

        # Test adding a counter
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": []
        }
        self.mock_collection.find_one.return_value = char_doc
        success, error = utils.add_counter(character_id, "Test Counter", 5, 10)
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Reset mock for next assertion
        self.mock_collection.update_one.reset_mock()

        # Test with counter limit reached
        char_doc_limit = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [{"counter": f"Counter {i}"} for i in range(utils.MAX_COUNTERS_PER_CHARACTER)]
        }
        self.mock_collection.find_one.return_value = char_doc_limit
        success, error = utils.add_counter(character_id, "Another Counter", 5, 10)
        self.assertFalse(success)
        self.assertTrue("maximum number" in error)

        # Test with existing counter
        char_doc_existing = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [{"counter": "Test Counter"}]
        }
        self.mock_collection.find_one.return_value = char_doc_existing
        success, error = utils.add_counter(character_id, "Test Counter", 5, 10)
        self.assertFalse(success)
        assert("exists for this character" in error)

    def test_get_user_character_by_id(self):
        valid_object_id = "123456789012345678901234"

        # Configure mock
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [],
            "health": []
        }
        self.mock_collection.find_one.return_value = char_doc

        # Test getting character by ID
        character = utils.get_user_character_by_id(valid_object_id)

        # Assertions
        self.assertIsInstance(character, UserCharacter)
        self.assertEqual(character.character, "Test Character")

    def test_delete_user_character(self):
        valid_object_id = "123456789012345678901234"

        # Configure mock
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [],
            "health": []
        }
        self.mock_collection.find_one.return_value = char_doc

        # Test deleting a character
        success, error = utils.delete_user_character(valid_object_id)

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.delete_one.assert_called_once()

        # Test deleting a non-existent character
        self.mock_collection.find_one.return_value = None
        success, error = utils.delete_user_character(valid_object_id)
        self.assertFalse(success)
        self.assertTrue("not found" in error)

    def test_add_health(self):
        valid_object_id = "123456789012345678901234"

        # Configure mock
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [],
            "health": []
        }
        self.mock_collection.find_one.return_value = char_doc

        # Ensure character_id is obtained via get_character_id_by_user_and_name
        character_id = utils.get_character_id_by_user_and_name("user123", "Test Character")  # FIXED

        # Test adding health
        success, error = utils.add_health(character_id, 100, 50)

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Test with health limit reached
        char_doc["health"] = [{"level": i} for i in HEALTH_LEVELS]
        success, error = utils.add_health(character_id, 100, 50)
        self.assertFalse(success)
        self.assertTrue("maximum health level" in error)

        # Test with existing health
        char_doc["health"] = [{"level": 100}]
        success, error = utils.add_health(character_id, 100, 50)
        self.assertFalse(success)
        self.assertTrue("already exists" in error)

    def test_get_user_character_health(self):
        valid_object_id = "123456789012345678901234"

        # Configure mock
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [],
            "health": [{"level": 100}]
        }
        self.mock_collection.find_one.return_value = char_doc

        # Test getting character health
        health = utils.get_user_character_health(valid_object_id)

        # Assertions
        self.assertEqual(len(health), 1)
        self.assertEqual(health[0]["level"], 100)

    def test_delete_health(self):
        valid_object_id = "123456789012345678901234"

        # Configure mock
        char_doc = {
            "_id": valid_object_id,
            "user": "user123",
            "character": "Test Character",
            "counters": [],
            "health": [{"level": 100}]
        }
        self.mock_collection.find_one.return_value = char_doc

        # Test deleting health
        success, error = utils.delete_health(valid_object_id, 100)

        # Assertions
        self.assertTrue(success)
        self.assertIsNone(error)
        self.mock_collection.update_one.assert_called_once()

        # Simulate health already deleted for next call
        char_doc["health"] = []

        # Test deleting non-existent health
        success, error = utils.delete_health(valid_object_id, 100)
        self.assertFalse(success)
        self.assertTrue("not found" in error)

if __name__ == "__main__":
    unittest.main()
