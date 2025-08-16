import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Import utilities
from utils import (
    add_user_character,
    get_character_id_by_user_and_name,
    add_counter,
    add_predefined_counter,
    get_counters_for_character,
    update_counter,
    remove_counter,
    rename_counter
)
from counter import PredefinedCounterEnum, CategoryEnum, Counter, CounterTypeEnum

class TestCounterManagement:

    # Test adding a custom counter
    def test_add_custom_counter(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_counter_1"
            character_name = "Counter Test Character"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a custom counter with explicit counter_type
            counter_name = "Test Counter"
            temp = 5
            perm = 10
            category = CategoryEnum.general.value
            comment = "Test comment"
            counter_type = "single_number"

            success, error = add_counter(character_id, counter_name, temp, perm, category, comment, counter_type)

            # Verify counter was added
            assert success is True
            assert error is None

            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            assert counter.temp == temp
            assert counter.perm == perm
            assert counter.category == category
            assert counter.comment == comment
            assert counter.counter_type == counter_type

            # Add a perm_is_maximum counter
            counter_name2 = "Max Counter"
            counter_type2 = "perm_is_maximum"
            success, error = add_counter(character_id, counter_name2, 2, 4, category, "max test", counter_type2)
            assert success is True
            counters = get_counters_for_character(character_id)
            counter2 = next((c for c in counters if c.counter == counter_name2), None)
            assert counter2 is not None
            assert counter2.counter_type == counter_type2

    # Test adding a predefined counter
    def test_add_predefined_counter(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_counter_2"
            character_name = "Predefined Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a predefined counter (willpower)
            counter_type = PredefinedCounterEnum.willpower.value
            perm = 6
            comment = "Willpower test"

            success, error = add_predefined_counter(character_id, counter_type, perm, comment)

            # Verify counter was added
            assert success is True  # Fix assertion
            assert error is None

            # Get counters for the character
            counters = get_counters_for_character(character_id)

            # Check if counter exists with expected values
            counter = next((c for c in counters if c.counter == counter_type), None)
            assert counter is not None
            assert counter.temp == perm  # temp should be equal to perm initially
            assert counter.perm == perm
            assert counter.comment == comment

    # Test updating a counter
    def test_update_counter(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_counter_3"
            character_name = "Update Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter with type perm_is_maximum
            counter_name = "Update Test Counter"
            temp = 5
            perm = 10
            counter_type = "perm_is_maximum"

            add_counter(character_id, counter_name, temp, perm, counter_type=counter_type)

            # Update the counter's temp value (increment within perm)
            delta = 2
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            assert counter.temp == temp + delta

            # Test incrementing temp above perm (should set temp to perm)
            delta = 20
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == perm  # Should not exceed perm

            # Test decrementing temp below zero (should fail and not change temp)
            delta = -20
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is False
            assert error is not None
            assert "cannot be below zero" in error
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == perm  # Should remain unchanged

    # Test removing a counter
    def test_remove_counter(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_counter_4"
            character_name = "Remove Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter
            counter_name = "Counter to Remove"
            add_counter(character_id, counter_name, 5, 10)

            # Verify counter exists
            counters = get_counters_for_character(character_id)
            assert any(c.counter == counter_name for c in counters)

            # Remove the counter
            success, error, details = remove_counter(character_id, counter_name)

            # Verify counter was removed
            assert success is True  # Fix assertion
            assert error is None

            # Check if counter no longer exists
            counters = get_counters_for_character(character_id)
            assert not any(c.counter == counter_name for c in counters)

    # Test string sanitization when adding a counter
    def test_counter_name_sanitization(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_sanitize"
            character_name = "Sanitization Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter with HTML in the name
            counter_name = "<script>alert('XSS')</script>Counter"
            sanitized_name = "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;Counter"

            success, error = add_counter(character_id, counter_name, 5, 10)

            # Verify counter was added with sanitized name
            assert success is True  # Fix assertion
            assert error is None

            # Get counters for the character
            counters = get_counters_for_character(character_id)

            # Check if counter exists with sanitized name
            counter = next((c for c in counters if c.counter == sanitized_name), None)
            assert counter is not None, "Counter with sanitized name not found"

            # Verify that no counter with the unsanitized name exists
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is None, "Counter with unsanitized name should not exist"

            # Add a counter with comment containing HTML
            counter_name = "Comment Test"
            comment = "<b>Important</b> note with control chars\x00\x1F"
            sanitized_comment = "&lt;b&gt;Important&lt;/b&gt; note with control chars"

            success, error = add_counter(character_id, counter_name, 5, 10, CategoryEnum.general.value, comment)

            # Verify counter was added with sanitized comment
            assert success is True  # Fix assertion
            assert error is None

            # Get counters for the character
            counters = get_counters_for_character(character_id)

            # Check if counter exists with sanitized comment
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            assert counter.comment == sanitized_comment

    # Test counter name uniqueness constraint
    def test_counter_name_uniqueness(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_uniqueness"
            character_name = "Uniqueness Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add first counter
            first_counter_name = "Unique Counter"
            success, error = add_counter(character_id, first_counter_name, 5, 10)

            # Verify first counter was added
            assert success is True
            assert error is None

            # Try to add another counter with the same name
            success, error = add_counter(character_id, first_counter_name, 3, 8)

            # Verify it fails due to duplicate name
            assert success is False  # Fix assertion
            assert error is not None
            assert "A counter with that name exists" in error

            # Try to add a counter with the same name but different case
            success, error = add_counter(character_id, first_counter_name.upper(), 3, 8)

            # This should also fail (case-insensitive comparison)
            assert success is False  # Fix assertion
            assert error is not None
            assert "A counter with that name exists" in error


    # Test renaming counter uniqueness constraint
    def test_rename_counter_uniqueness(self, test_characters_collection):
        valid_object_id = "123456789012345678901234"  # Use valid ObjectId

        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_rename_uniqueness"
            character_name = "Rename Uniqueness Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add two counters
            add_counter(character_id, "Counter One", 5, 10)
            add_counter(character_id, "Counter Two", 3, 8)

            # Ensure both counters exist before renaming
            counters = get_counters_for_character(character_id)
            assert any(c.counter == "Counter One" for c in counters)
            assert any(c.counter == "Counter Two" for c in counters)

            # Try to rename "Counter One" to "Counter Two"
            success, error = rename_counter(character_id, "Counter One", "Counter Two")

            # Verify it fails due to duplicate name, not character not found
            assert success is False  # Fix assertion
            assert error is not None
            assert "already exists" in error

            # Try with sanitized name
            success, error = rename_counter(str(character_id), "Counter One", "<i>Counter Three</i>")

            # Verify it succeeds with sanitized name
            assert success is True
            assert error is None

            # Get counters for the character
            counters = get_counters_for_character(str(character_id))

            # Check if counter exists with sanitized name
            counter = next((c for c in counters if c.counter == "&lt;i&gt;Counter Three&lt;/i&gt;"), None)
            assert counter is not None, "Counter with sanitized name not found"

    # Test updating counter category and comment after creation
    def test_update_counter_category_and_comment(self, test_characters_collection):
        from utils import update_counter_category, update_counter_comment, get_counters_for_character
        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_update_cat_comment"
            character_name = "Update CatComment"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            add_counter(character_id, "CounterCat", 1, 2, "general", "Initial comment")
            # Update category
            success, error = update_counter_category(character_id, "CounterCat", "tempers")
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == "CounterCat"), None)
            assert counter.category == "tempers"
            # Update comment
            success, error = update_counter_comment(character_id, "CounterCat", "Updated comment")
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == "CounterCat"), None)
            assert counter.comment == "Updated comment"

    # Test counter retrieval and display formatting
    def test_counter_retrieval_and_display(self, test_characters_collection):
        from counter import CounterTypeEnum
        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_display"
            character_name = "Display Character"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            add_counter(character_id, "DisplayCounter", 2, 5, counter_type=CounterTypeEnum.perm_is_maximum.value)
            counters = get_counters_for_character(character_id)
            assert len(counters) == 1
            counter = counters[0]
            # Test display formatting
            pretty = counter.generate_display_pretty(lambda x: x)
            assert "DisplayCounter" in pretty
            assert ":asterisk:" in pretty or ":stop_button:" in pretty

    # Test maximum allowed counters per character
    def test_maximum_counters_per_character(self, test_characters_collection):
        from utils import MAX_COUNTERS_PER_CHARACTER
        with patch('utils.characters_collection', test_characters_collection), \
             patch('utils.MAX_COUNTERS_PER_CHARACTER', 3):
            user_id = "test_user_max_counters"
            character_name = "MaxCountersChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            # Add up to the limit
            for i in range(3):
                success, error = add_counter(character_id, f"Counter{i}", 1, 2)
                assert success is True
            # Try to add one more
            success, error = add_counter(character_id, "Counter3", 1, 2)
            assert success is False
            assert error is not None
            assert "maximum" in error.lower()

    # Test invalid counter type
    def test_invalid_counter_type(self, test_characters_collection):
        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_invalid_type"
            character_name = "InvalidTypeChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            success, error = add_counter(character_id, "InvalidTypeCounter", 1, 2, counter_type="not_a_type")
            assert success is False
            assert error is not None
            assert "invalid" in error.lower() or "type" in error.lower()

    # Test malformed input (e.g., None or empty counter name)
    def test_malformed_counter_input(self, test_characters_collection):
        with patch('utils.characters_collection', test_characters_collection):
            user_id = "test_user_malformed"
            character_name = "MalformedChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            # None as counter name
            success, error = add_counter(character_id, None, 1, 2)
            assert success is False
            assert error is not None
            # Empty string as counter name
            success, error = add_counter(character_id, "", 1, 2)
            assert success is False
            assert error is not None
            # Whitespace only
            success, error = add_counter(character_id, "   ", 1, 2)
            assert success is False
            assert error is not None

    # Test perm_is_maximum temp cannot exceed perm on init
    def test_perm_is_maximum_temp_cannot_exceed_perm_on_init(self):
        with pytest.raises(ValueError):
            Counter("Test", 6, 5, "general", counter_type=CounterTypeEnum.perm_is_maximum.value)

    # Test perm_is_maximum_bedlam temp and bedlam cannot exceed perm on init
    def test_perm_is_maximum_bedlam_temp_and_bedlam_cannot_exceed_perm_on_init(self):
        # temp > perm
        with pytest.raises(ValueError):
            Counter("Test", 6, 5, "general", bedlam=5, counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value)
        # bedlam > perm
        with pytest.raises(ValueError):
            Counter("Test", 5, 5, "general", bedlam=6, counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value)
        # both valid
        c = Counter("Test", 5, 5, "general", bedlam=5, counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value)
        assert c.temp == 5 and c.bedlam == 5

    # Test other counter types can have temp above perm
    def test_other_counter_types_can_have_temp_above_perm(self):
        c = Counter("Test", 10, 5, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 10 and c.perm == 5

    # Test updating temp perm_is_maximum_bedlam
    def test_update_temp_perm_is_maximum_bedlam(self, test_characters_collection):
        # Setup
        from utils import add_user_character, get_character_id_by_user_and_name, add_counter, update_counter
        user_id = "u"
        character = "c"
        add_user_character(user_id, character)
        character_id = get_character_id_by_user_and_name(user_id, character)
        add_counter(character_id, "bedlamtest", 2, 5, counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value)
        # Try to set temp above perm
        success, error = update_counter(character_id, "bedlamtest", "temp", 10)
        # Should cap at perm
        from utils import get_counters_for_character
        c = next(x for x in get_counters_for_character(character_id) if x.counter == "bedlamtest")
        assert c.temp == c.perm
        # Try to set temp below zero
        success, error = update_counter(character_id, "bedlamtest", "temp", -10)
        assert not success and "below zero" in error

    # Test updating temp other types can exceed perm
    def test_update_temp_other_types_can_exceed_perm(self, test_characters_collection):
        from utils import add_user_character, get_character_id_by_user_and_name, add_counter, update_counter, get_counters_for_character
        user_id = "u"
        character = "c2"
        add_user_character(user_id, character)
        character_id = get_character_id_by_user_and_name(user_id, character)
        add_counter(character_id, "othertest", 2, 5, counter_type=CounterTypeEnum.single_number.value)
        # Set temp above perm
        update_counter(character_id, "othertest", "temp", 10)
        c = next(x for x in get_counters_for_character(character_id) if x.counter == "othertest")
        assert c.temp == 12  # 2 + 10

    # Test updating bedlam perm_is_maximum_bedlam
    def test_update_bedlam_perm_is_maximum_bedlam(self, test_characters_collection):
        from utils import add_user_character, get_character_id_by_user_and_name, add_counter, get_counters_for_character
        user_id = "u"
        character = "c3"
        add_user_character(user_id, character)
        character_id = get_character_id_by_user_and_name(user_id, character)
        add_counter(character_id, "bedlamtest2", 2, 5, counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value)
        # Simulate bedlam update (direct dict manipulation for test)
        counters = get_counters_for_character(character_id)
        c = next(x for x in counters if x.counter == "bedlamtest2")
        # Try to set bedlam above perm
        c.bedlam = 6
        try:
            Counter(c.counter, c.temp, c.perm, c.category, bedlam=c.bedlam, counter_type=c.counter_type)
            assert False, "Should not allow bedlam > perm"
        except ValueError:
            pass

