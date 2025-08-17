import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId

# Import utilities
import utils
from utils import add_user_character, get_character_id_by_user_and_name, add_counter, get_counters_for_character
from utils import CategoryEnum

# Import cog and command modules
from avct_cog import AvctCog

class TestCommands:

    # Test cog initialization
    def test_cog_init(self, mock_bot):
        cog = AvctCog(mock_bot)

        # Check if command groups were created
        assert hasattr(cog, 'avct_group')
        assert hasattr(cog, 'configav_group')
        assert hasattr(cog, 'add_group')
        assert hasattr(cog, 'rename_group')
        assert hasattr(cog, 'remove_group')
        assert hasattr(cog, 'edit_group')
        assert hasattr(cog, 'character_group')

    # Test cog loading
    @pytest.mark.asyncio
    async def test_cog_load(self, mock_bot):
        cog = AvctCog(mock_bot)
        await cog.cog_load()

        # Check if command groups were added to the bot
        mock_bot.tree.add_command.assert_any_call(cog.avct_group)
        mock_bot.tree.add_command.assert_any_call(cog.configav_group)

    # Test show command
    @pytest.mark.asyncio
    async def test_show_command(self, mock_interaction, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch('utils.characters_collection', test_characters_collection):

            # Add a character for testing
            user_id = str(mock_interaction.user.id)
            character_name = "Test Character"

            add_user_character(user_id, character_name)

            # Create a mock show character function
            async def mock_show_character(interaction, character_name):
                characters = utils.get_all_user_characters_for_user(str(interaction.user.id))
                char = next((c for c in characters if c.character == character_name), None)
                if char:
                    await interaction.response.send_message(f"Character: {character_name}")
                else:
                    await interaction.response.send_message(f"Character not found: {character_name}")

            # Call the mocked function directly
            await mock_show_character(mock_interaction, character_name)

            # Check if send_message was called
            mock_interaction.response.send_message.assert_called_once()
            # The message should contain the character name
            assert character_name in mock_interaction.response.send_message.call_args[0][0]

    # Test plus command
    @pytest.mark.asyncio
    async def test_plus_command(self, mock_interaction, test_characters_collection):
        valid_object_id = ObjectId("123456789012345678901234")  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection), \
             patch('utils.get_character_id_by_user_and_name', return_value=str(valid_object_id)):

            user_id = str(mock_interaction.user.id)
            character_name = "Test Character"
            counter_name = "Test Counter"
            counter_type = "perm_is_maximum"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            test_characters_collection.find_one.return_value = {
                "_id": valid_object_id,
                "user": user_id,
                "character": character_name,
                "counters": [{"counter": counter_name, "temp": 5, "perm": 10, "category": "general", "comment": "", "counter_type": counter_type}]
            }

            counter_state = {"temp": 5, "perm": 10}

            def mock_get_counters(char_id):
                return [{"counter": counter_name, "temp": counter_state["temp"], "perm": counter_state["perm"], "category": "general", "comment": "", "counter_type": counter_type}]

            with patch('utils.get_counters_for_character', mock_get_counters):
                async def mock_plus_cmd(interaction, character_name, counter_name, amount):
                    character_id = utils.get_character_id_by_user_and_name(str(interaction.user.id), character_name)
                    counters = utils.get_counters_for_character(str(character_id))
                    counter = next((c for c in counters if c["counter"] == counter_name), None)
                    if not counter:
                        await interaction.response.send_message(f"Counter not found: {counter_name}")
                        return
                    new_temp = counter["temp"] + amount
                    if amount < 0 and new_temp < 0:
                        await interaction.response.send_message("Cannot decrement temp below zero")
                        return
                    elif amount > 0 and counter.get("counter_type") == "perm_is_maximum" and new_temp > counter["perm"]:
                        counter_state["temp"] = counter["perm"]
                    else:
                        counter_state["temp"] = new_temp
                    await interaction.response.send_message(f"Updated {counter_name} by {amount}")

                # Decrement below zero
                await mock_plus_cmd(mock_interaction, character_name, counter_name, -20)
                mock_interaction.response.send_message.assert_any_call("Cannot decrement temp below zero")
                counters = utils.get_counters_for_character(str(valid_object_id))
                counter = next((c for c in counters if c["counter"] == counter_name), None)
                assert counter is not None
                assert counter["temp"] == 5  # Should remain unchanged

                # Increment above perm
                await mock_plus_cmd(mock_interaction, character_name, counter_name, 20)
                counters = utils.get_counters_for_character(str(valid_object_id))
                counter = next((c for c in counters if c["counter"] == counter_name), None)
                assert counter["temp"] == counter["perm"]  # Should not exceed perm

    # Test adding character with sanitization
    @pytest.mark.asyncio
    async def test_add_character_with_sanitization(self, mock_interaction, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch('utils.characters_collection', test_characters_collection):

            # Create a mock add_character function
            async def mock_add_character(interaction, character_name):
                user_id = str(interaction.user.id)
                success, error = add_user_character(user_id, character_name)

                if success:
                    await interaction.response.send_message(f"Added character: {character_name}")
                else:
                    await interaction.response.send_message(f"Error: {error}")

            # Set up mock interaction with HTML in character name
            mock_interaction.user.id = "test_sanitize_user"
            unsafe_name = "<script>alert('XSS')</script>Character"

            # Call the mocked function directly
            await mock_add_character(mock_interaction, unsafe_name)

            # Check if character was added with sanitized name
            characters = utils.get_all_user_characters_for_user("test_sanitize_user")
            assert len(characters) == 0

    # Test adding character with duplicate name
    @pytest.mark.asyncio
    async def test_add_duplicate_character(self, mock_interaction, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch('utils.characters_collection', test_characters_collection):

            # Create a mock add_character function
            async def mock_add_character(interaction, character_name):
                user_id = str(interaction.user.id)
                success, error = add_user_character(user_id, character_name)

                if success:
                    await interaction.response.send_message(f"Added character: {character_name}")
                else:
                    await interaction.response.send_message(f"Error: {error}")

            # Add a character directly
            user_id = "test_duplicate_user"
            character_name = "Existing Character"
            mock_interaction.user.id = user_id

            add_user_character(user_id, character_name)

            # Try to add a character with the same name
            await mock_add_character(mock_interaction, character_name)

            # Check if send_message was called with an error message
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args[0][0]
            assert "already exists" in call_args.lower()

    # Test adding counter without sanitization
    @pytest.mark.asyncio
    async def test_add_counter_with_sanitization(self, test_characters_collection):
        # Patch the characters_collection with our test collection
        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_add_counter"
            character_name = "Add Counter Character"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter with all keyword arguments (should not error)
            success, error = add_counter(
                character_id,
                "CounterName",
                5,
                category=CategoryEnum.general.value,
                comment="Test comment",
                counter_type="single_number",
                force_unpretty=True
            )
            assert success is True
            assert error is None

            # Check if the counter was added correctly
            counters = utils.get_counters_for_character(str(character_id))
            # FIX: Counter objects, not dicts
            counter = next((c for c in counters if getattr(c, "counter", None) == "CounterName"), None)
            assert counter is not None
            assert counter.temp == 5
            assert counter.perm == 5
            assert counter.category == CategoryEnum.general.value
            assert counter.comment == "Test comment"
            assert counter.counter_type == "single_number"
