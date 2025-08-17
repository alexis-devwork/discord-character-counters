from unittest.mock import patch

# Import utilities
from utils import (
    add_user_character,
    get_character_id_by_user_and_name,
    get_all_user_characters_for_user,
    rename_character,
    remove_character,
)


class TestCharacterManagement:
    # Test adding a character
    def test_add_character(self, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch("utils.characters_collection", test_characters_collection):
            # Add a character
            user_id = "test_user_1"
            character_name = "Test Character"

            success, error = add_user_character(user_id, character_name)

            # Verify character was added
            assert success is True
            assert error is None

            # Check if character exists
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            assert character_id is not None

            # Get all characters for user
            characters = get_all_user_characters_for_user(user_id)
            assert len(characters) == 1
            assert characters[0].character == character_name
            assert characters[0].user == user_id

    # Test character name sanitization
    def test_character_name_sanitization(self, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch("utils.characters_collection", test_characters_collection):
            # Add a character with HTML in the name
            user_id = "test_user_sanitize"
            character_name = "<script>alert('XSS')</script>Character"

            # Should fail due to non-alphanumeric characters (except spaces and underscores)
            success, error = add_user_character(user_id, character_name)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Add a character with control characters
            character_name_with_controls = "Bad\x00Character\x1fName"
            success, error = add_user_character(user_id, character_name_with_controls)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Add a character with spaces (should succeed)
            character_name_with_spaces = "Good Character Name"
            success, error = add_user_character(user_id, character_name_with_spaces)
            assert success is True
            assert error is None

            # Add a character with underscores (should succeed)
            character_name_with_underscores = "Good_Character_Name"
            success, error = add_user_character(
                user_id, character_name_with_underscores
            )
            assert success is True
            assert error is None

    # Test character name uniqueness constraint
    def test_character_name_uniqueness(self, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch("utils.characters_collection", test_characters_collection):
            # Add a character
            user_id = "test_user_uniqueness"
            character_name = "Unique Character"

            success, error = add_user_character(user_id, character_name)

            # Verify character was added
            assert success is True
            assert error is None

            # Try to add another character with the same name
            success, error = add_user_character(user_id, character_name)

            # Verify it fails due to duplicate name
            assert success is False
            assert error is not None
            assert "already exists" in error

            # Now test with a different character name and user to avoid interference
            entity_user_id = "test_user_entities"
            entity_character = "Entity Character"

            # Add first character for this user
            success1, error1 = add_user_character(entity_user_id, entity_character)
            assert success1 is True
            assert error1 is None

            # Print characters for this user
            chars = get_all_user_characters_for_user(entity_user_id)
            print(f"Characters for {entity_user_id}: {[c.character for c in chars]}")

            # Try to add the same character again - should fail
            print(
                f"Attempting to add duplicate character: {entity_character} for user {entity_user_id}"
            )
            success2, error2 = add_user_character(entity_user_id, entity_character)

            # Check if it failed
            print(f"Result of duplicate attempt: success={success2}, error={error2}")
            assert success2 is False, "Adding exact duplicate character should fail"
            assert error2 is not None
            assert "already exists" in error2

            # Try adding a differently cased version of the character
            success3, error3 = add_user_character(
                entity_user_id, entity_character.upper()
            )
            assert success3 is True, "Adding differently cased character should succeed"

            # Verify we now have 2 characters for this user
            chars_after = get_all_user_characters_for_user(entity_user_id)
            assert len(chars_after) == 2, (
                f"Expected 2 characters but found {len(chars_after)}"
            )

            # Verify a different user can add a character with the same name
            other_user_id = "test_user_uniqueness_2"
            success, error = add_user_character(other_user_id, character_name)

            # This should succeed (different user)
            assert success is True
            assert error is None

    # Test renaming character uniqueness constraint
    def test_rename_character_uniqueness(self, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch("utils.characters_collection", test_characters_collection):
            # Add two characters
            user_id = "test_user_rename"
            add_user_character(user_id, "Character One")
            add_user_character(user_id, "Character Two")

            # Try to rename "Character One" to "Character Two"
            success, error = rename_character(user_id, "Character One", "Character Two")

            # Verify it fails due to duplicate name
            assert success is False
            assert error is not None
            assert "already exists" in error

            # Try with a different case of an existing name - should succeed
            success, error = rename_character(user_id, "Character One", "character two")
            assert success is True
            assert error is None

            # Get all characters for user
            characters = get_all_user_characters_for_user(user_id)
            assert len(characters) == 2

            # Verify we have both the original and differently-cased names
            character_names = [c.character for c in characters]
            assert "Character Two" in character_names
            assert "character two" in character_names

            # Try with sanitized name - first get the sanitized form
            html_name = "<i>Character Three</i>"
            # Should fail due to non-alphanumeric characters (except spaces and underscores)
            success, error = rename_character(user_id, "Character Two", html_name)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Try renaming to a name that, when sanitized, would match an existing one
            ampersand_name = "Character & Three"
            success, error = rename_character(user_id, "character two", ampersand_name)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Try renaming to a name with underscores (should succeed)
            underscore_name = "Character_Three_With_Underscores"
            success, error = rename_character(user_id, "character two", underscore_name)
            assert success is True
            assert error is None

            # Try renaming to a name with only spaces (should fail)
            only_spaces = "    "
            success, error = rename_character(user_id, "character two", only_spaces)
            assert success is False
            # Accept either the "empty" or "alphanumeric characters, spaces, and underscores" error
            assert (
                "empty" in error.lower()
                or "invalid" in error.lower()
                or "alphanumeric characters, spaces, and underscores" in error.lower()
            )

            # Try renaming to a name with control characters (should fail)
            control_name = "Bad\x00Name"
            success, error = rename_character(user_id, "character two", control_name)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

    def test_maximum_allowed_characters_per_user(self, test_characters_collection):
        with (
            patch("utils.characters_collection", test_characters_collection),
            patch("utils.MAX_USER_CHARACTERS", 5),
        ):
            user_id = "max_user"
            # Add up to the limit
            for i in range(5):
                success, error = add_user_character(user_id, f"Char{i}")
                assert success is True
                assert error is None
            # Try to add one more
            success, error = add_user_character(user_id, "Char5")
            assert success is False
            assert error is not None
            assert "maximum" in error.lower()

    def test_empty_or_whitespace_character_names(self, test_characters_collection):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "empty_name_user"
            # Empty string
            success, error = add_user_character(user_id, "")
            assert success is False
            assert error is not None
            assert "empty" in error.lower() or "invalid" in error.lower()
            # Whitespace only
            success, error = add_user_character(user_id, "   ")
            assert success is False
            assert error is not None
            assert "empty" in error.lower() or "invalid" in error.lower()
            # Add a valid character
            add_user_character(user_id, "ValidName")
            # Try to rename to empty
            success, error = rename_character(user_id, "ValidName", "")
            assert success is False
            assert error is not None
            # Try to rename to whitespace
            success, error = rename_character(user_id, "ValidName", "   ")
            assert success is False
            assert error is not None

    def test_overly_long_character_names(self, test_characters_collection):
        with (
            patch("utils.characters_collection", test_characters_collection),
            patch("utils.MAX_FIELD_LENGTH", 10),
        ):
            user_id = "long_name_user"
            long_name = "A" * 11
            # Add with overly long name
            success, error = add_user_character(user_id, long_name)
            assert success is False
            assert error is not None
            assert "must be at most" in error.lower()
            # Add a valid character
            add_user_character(user_id, "ShortName")
            # Rename to overly long name
            success, error = rename_character(user_id, "ShortName", long_name)
            assert success is False
            assert error is not None
            assert "must be at most" in error.lower()

    def test_removing_characters(self, test_characters_collection):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "remove_user"
            character_name = "Removable"
            add_user_character(user_id, character_name)
            # Remove character
            result = remove_character(user_id, character_name)
            # Handle tuple/list with more than two values, or single value
            if isinstance(result, (tuple, list)):
                success, error = result[:2]
            else:
                success, _error = result, None
            assert success is True
            # error may be None or not present
            # Verify it's gone
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            assert character_id is None
            characters = get_all_user_characters_for_user(user_id)
            assert all(c.character != character_name for c in characters)

    def test_retrieving_characters_for_users_with_none(
        self, test_characters_collection
    ):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "no_chars_user"
            characters = get_all_user_characters_for_user(user_id)
            assert isinstance(characters, list)
            assert len(characters) == 0

    def test_database_errors(self, test_characters_collection):
        # Patch methods to simulate errors
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "db_error_user"
            character_name = "DBErrorChar"
            # Simulate insert error
            with patch.object(
                test_characters_collection,
                "insert_one",
                side_effect=Exception("DB insert failed"),
            ):
                try:
                    success, error = add_user_character(user_id, character_name)
                except Exception as e:
                    success, error = False, str(e)
                assert success is False
                assert error is not None
                assert "db" in error.lower() or "error" in error.lower()
            # Simulate update error
            add_user_character(user_id, "ToRename")
            with patch.object(
                test_characters_collection,
                "update_one",
                side_effect=Exception("DB update failed"),
            ):
                try:
                    success, error = rename_character(user_id, "ToRename", "Renamed")
                except Exception as e:
                    success, error = False, str(e)
                assert success is False
                assert error is not None
                assert "db" in error.lower() or "error" in error.lower()
            # Simulate delete error
            add_user_character(user_id, "ToDelete")
            with patch.object(
                test_characters_collection,
                "delete_one",
                side_effect=Exception("DB delete failed"),
            ):
                try:
                    result = remove_character(user_id, "ToDelete")
                    if isinstance(result, tuple):
                        success, error = result
                    else:
                        success, error = result, None
                except Exception as e:
                    success, error = False, str(e)
                assert success is False
                assert error is not None
                assert "db" in error.lower() or "error" in error.lower()
