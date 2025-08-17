"""
Configuration file for pytest.

This file sets up common fixtures and configurations for tests.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dotenv import load_dotenv
from bson.objectid import ObjectId  # Import ObjectId for mock user IDs

# Load test environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.test"))

# Add the parent directory to sys.path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Mock MongoDB for all tests
@pytest.fixture(autouse=True)
def mock_mongodb():
    """Mock MongoDB connections for all tests."""
    with patch("pymongo.MongoClient") as mock_client:
        # Create mock db and collection
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Set up the mocks
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        yield {"client": mock_client, "db": mock_db, "collection": mock_collection}


# Test MongoDB collection for storing actual test data
@pytest.fixture
def test_characters_collection():
    """Provide a test collection for character data."""
    test_collection = MagicMock()

    # In-memory storage for test documents
    test_data = {}
    next_id = 1

    # Mock find_one
    def mock_find_one(filter_dict):
        if not filter_dict:
            return None

        # For character lookups, add special handling for character name checks
        if "character" in filter_dict and "user" in filter_dict:
            user = filter_dict["user"]
            character_name = filter_dict["character"]

            # Look for exact matches first
            for doc in test_data.values():
                if doc.get("user") == user and doc.get("character") == character_name:
                    print(f"Found exact character match: {character_name}")
                    return doc

            print(f"No exact character match found for: {character_name}")

        # Standard lookup for other queries
        for doc_id, doc in test_data.items():
            match = True
            for key, value in filter_dict.items():
                if key == "_id" and str(value) != str(doc_id):
                    match = False
                    break
                elif key != "_id" and (key not in doc or doc[key] != value):
                    match = False
                    break
            if match:
                return doc

        return None

    # Mock find
    def mock_find(filter_dict=None):
        if not filter_dict:
            return list(test_data.values())

        results = []
        for doc in test_data.values():
            match = True
            for key, value in filter_dict.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
        return results

    # Mock insert_one
    def mock_insert_one(doc):
        nonlocal next_id

        # Check for duplicate character names
        if "character" in doc and "user" in doc:
            for existing_doc in test_data.values():
                if (
                    existing_doc.get("user") == doc["user"]
                    and existing_doc.get("character") == doc["character"]
                ):
                    print(f"Duplicate character detected: {doc['character']}")
                    # Return a mock that will cause a duplicate key error
                    mock_result = MagicMock()
                    mock_result.inserted_id = None
                    return mock_result

        # No duplicate, proceed with insert
        # Generate a valid ObjectId for _id
        from bson.objectid import ObjectId

        doc_id = str(ObjectId())
        doc["_id"] = doc_id
        test_data[doc_id] = doc

        # Debug inserted document
        print(f"Inserted document: {doc}")

        # Mock InsertOneResult
        result = MagicMock()
        result.inserted_id = doc_id
        return result

    # Mock update_one
    def mock_update_one(filter_dict, update_dict, upsert=False):
        doc = mock_find_one(filter_dict)
        if doc:
            # Handle $set operator
            if "$set" in update_dict:
                for key, value in update_dict["$set"].items():
                    doc[key] = value

            # Handle $pull operator
            if "$pull" in update_dict:
                for key, pull_criteria in update_dict["$pull"].items():
                    if key in doc and isinstance(doc[key], list):
                        # Simple implementation - just matches exact dicts
                        doc[key] = [item for item in doc[key] if item != pull_criteria]

            # Mock UpdateResult
            result = MagicMock()
            result.modified_count = 1
            return result
        elif upsert:
            # Create new document for upsert
            new_doc = {}
            for key, value in filter_dict.items():
                new_doc[key] = value

            if "$set" in update_dict:
                for key, value in update_dict["$set"].items():
                    new_doc[key] = value

            return mock_insert_one(new_doc)
        else:
            # No match, no update
            result = MagicMock()
            result.modified_count = 0
            return result

    # Mock delete_one
    def mock_delete_one(filter_dict):
        doc = mock_find_one(filter_dict)
        if doc:
            del test_data[doc["_id"]]
            # Mock DeleteResult
            result = MagicMock()
            result.deleted_count = 1
            return result
        else:
            # No match, no delete
            result = MagicMock()
            result.deleted_count = 0
            return result

    # Mock count_documents
    def mock_count_documents(filter_dict):
        return len(mock_find(filter_dict))

    # Assign mock methods
    test_collection.find_one = mock_find_one
    test_collection.find = mock_find
    test_collection.insert_one = mock_insert_one
    test_collection.update_one = mock_update_one
    test_collection.delete_one = mock_delete_one
    test_collection.count_documents = mock_count_documents

    return test_collection


# Mock Discord bot for Discord-related tests
@pytest.fixture
def mock_bot():
    """Create a mock Discord bot for testing."""
    bot = MagicMock()
    bot.tree = MagicMock()
    return bot


# Mock Discord interaction for testing app commands
@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction for testing commands."""
    interaction = MagicMock()
    interaction.response = AsyncMock()  # Use AsyncMock for asynchronous methods
    interaction.response.send_message = (
        AsyncMock()
    )  # Ensure send_message is asynchronous
    interaction.user = MagicMock()
    interaction.user.id = ObjectId("123456789012345678901234")  # Use a valid ObjectId
    interaction.namespace = MagicMock()
    return interaction
