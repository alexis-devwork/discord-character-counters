import pytest
from unittest.mock import patch

# Import utilities
from utils import (
    add_user_character,
    get_character_id_by_user_and_name,
    add_counter,
    add_predefined_counter,
    get_counters_for_character,
    update_counter,
    remove_counter,
    rename_counter,
)
from counter import PredefinedCounterEnum, CategoryEnum, Counter, CounterTypeEnum


class TestCounterManagement:
    # Test adding a custom counter
    def test_add_custom_counter(self, test_characters_collection):

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_counter_1"
            character_name = "Counter Test Character"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a custom counter with explicit counter_type
            counter_name = "Test Counter"
            value = 5
            category = CategoryEnum.general.value
            comment = "Test comment"
            counter_type = "single_number"

            success, error = add_counter(
                character_id,
                counter_name,
                value,
                category=category,
                comment=comment,
                counter_type=counter_type,
            )

            # Verify counter was added
            assert success is True
            assert error is None

            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            # For single_number, both temp and perm should be set to value
            assert counter.temp == value
            assert counter.perm == value
            assert counter.category == category
            assert counter.comment == comment
            assert counter.counter_type == counter_type

            # Add a perm_is_maximum counter
            counter_name2 = "Max Counter"
            counter_type2 = "perm_is_maximum"
            success, error = add_counter(
                character_id,
                counter_name2,
                2,
                category=category,
                comment="max test",
                counter_type=counter_type2,
            )
            assert success is True
            counters = get_counters_for_character(character_id)
            counter2 = next((c for c in counters if c.counter == counter_name2), None)
            assert counter2 is not None
            assert counter2.counter_type == counter_type2

    # Test adding a predefined counter
    def test_add_predefined_counter(self, test_characters_collection):

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_counter_2"
            character_name = "Predefined Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a predefined counter (willpower)
            counter_type = PredefinedCounterEnum.willpower.value
            perm = 6
            comment = "Willpower test"

            success, error = add_predefined_counter(
                character_id, counter_type, perm, comment
            )

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

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_counter_3"
            character_name = "Update Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter with type perm_is_maximum
            counter_name = "Update Test Counter"
            value = 5
            counter_type = "perm_is_maximum"

            add_counter(character_id, counter_name, value, counter_type=counter_type)

            # Update the counter's temp value (increment within perm)
            delta = 2
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            # FIX: temp should be capped at perm (which is 5), not value + delta
            assert counter.temp == min(value + delta, counter.perm)

            # Test incrementing temp above perm (should set temp to perm)
            delta = 20
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            # Since perm was set to 5, temp should not exceed 5
            assert counter.temp == 5

            # Test decrementing temp below zero (should fail and not change temp)
            delta = -20
            success, error = update_counter(character_id, counter_name, "temp", delta)
            assert success is False
            assert error is not None
            assert "cannot be below zero" in error
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == 5  # Should remain unchanged

    # Test removing a counter
    def test_remove_counter(self, test_characters_collection):

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_counter_4"
            character_name = "Remove Counter Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter
            counter_name = "Counter to Remove"
            add_counter(character_id, counter_name, 5)

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

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_sanitize"
            character_name = "Sanitization Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add a counter with HTML in the name
            counter_name = "<script>alert('XSS')</script>Counter"
            success, error = add_counter(character_id, counter_name, 5)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Add a counter with control characters
            counter_name_with_controls = "Bad\x00Counter\x1fName"
            success, error = add_counter(character_id, counter_name_with_controls, 5)
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Add a counter with spaces (should succeed)
            counter_name_with_spaces = "Good Counter Name"
            success, error = add_counter(character_id, counter_name_with_spaces, 5)
            assert success is True
            assert error is None

            # Add a counter with comment containing HTML (comment is allowed to be sanitized, so no change)
            counter_name = "CommentTest"
            comment = "<b>Important</b> note with control chars\x00\x1f"
            sanitized_comment = "&lt;b&gt;Important&lt;/b&gt; note with control chars"
            success, error = add_counter(
                character_id,
                counter_name,
                5,
                category=CategoryEnum.general.value,
                comment=comment,
            )
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter is not None
            assert counter.comment == sanitized_comment

    # Test counter name uniqueness constraint
    def test_counter_name_uniqueness(self, test_characters_collection):

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_uniqueness"
            character_name = "Uniqueness Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add first counter
            first_counter_name = "Unique Counter"
            success, error = add_counter(character_id, first_counter_name, 5)

            # Verify first counter was added
            assert success is True
            assert error is None

            # Try to add another counter with the same name
            success, error = add_counter(character_id, first_counter_name, 3)

            # Verify it fails due to duplicate name
            assert success is False  # Fix assertion
            assert error is not None
            assert "A counter with that name exists" in error

            # Try to add a counter with the same name but different case
            success, error = add_counter(character_id, first_counter_name.upper(), 3)

            # This should also fail (case-insensitive comparison)
            assert success is False  # Fix assertion
            assert error is not None
            assert "A counter with that name exists" in error

    # Test renaming counter uniqueness constraint
    def test_rename_counter_uniqueness(self, test_characters_collection):

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_rename_uniqueness"
            character_name = "Rename Uniqueness Test"

            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)

            # Add two counters
            add_counter(character_id, "CounterOne", 5)
            add_counter(character_id, "CounterTwo", 3)

            # Try to rename "CounterOne" to "CounterTwo"
            success, error = rename_counter(character_id, "CounterOne", "CounterTwo")
            assert success is False
            assert "already exists" in error

            # Try with non-alphanumeric name
            non_alnum_name = "<i>CounterThree</i>"
            success, error = rename_counter(
                str(character_id), "CounterOne", non_alnum_name
            )
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

            # Try renaming to a name with spaces (should succeed)
            spaced_name = "Counter Three With Spaces"
            success, error = rename_counter(
                str(character_id), "CounterOne", spaced_name
            )
            assert success is True
            assert error is None

            # Try renaming to a name with only spaces (should fail)
            only_spaces = "    "
            success, error = rename_counter(
                str(character_id), "CounterOne", only_spaces
            )
            assert success is False
            assert "empty" in error.lower() or "invalid" in error.lower()

            # Try renaming to a name with control characters (should fail)
            control_name = "Bad\x00Name"
            success, error = rename_counter(
                str(character_id), "CounterOne", control_name
            )
            assert success is False
            assert "alphanumeric characters, spaces, and underscores" in error

    # Test updating counter category and comment after creation
    def test_update_counter_category_and_comment(self, test_characters_collection):
        from utils import (
            set_counter_category,
            update_counter_comment,
            get_counters_for_character,
        )

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_update_cat_comment"
            character_name = "Update CatComment"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            add_counter(
                character_id,
                "CounterCat",
                1,
                category="general",
                comment="Initial comment",
            )
            # Update category
            success, error = set_counter_category(character_id, "CounterCat", "tempers")
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == "CounterCat"), None)
            assert counter.category == "tempers"
            # Update comment
            success, error = update_counter_comment(
                character_id, "CounterCat", "Updated comment"
            )
            assert success is True
            assert error is None
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == "CounterCat"), None)
            assert counter.comment == "Updated comment"

    # Test counter retrieval and display formatting
    def test_counter_retrieval_and_display(self, test_characters_collection):
        from counter import CounterTypeEnum

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_display"
            character_name = "Display Character"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            add_counter(
                character_id,
                "DisplayCounter",
                2,
                counter_type=CounterTypeEnum.perm_is_maximum.value,
            )
            counters = get_counters_for_character(character_id)
            assert len(counters) == 1
            counter = counters[0]
            # Test display formatting
            pretty = counter.generate_display_pretty(lambda x: x)
            assert "DisplayCounter" in pretty
            assert ":asterisk:" in pretty or ":stop_button:" in pretty

    # Test maximum allowed counters per character
    def test_maximum_counters_per_character(self, test_characters_collection):

        with (
            patch("utils.characters_collection", test_characters_collection),
            patch("utils.MAX_COUNTERS_PER_CHARACTER", 3),
        ):
            user_id = "test_user_max_counters"
            character_name = "MaxCountersChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            # Add up to the limit
            for i in range(3):
                success, error = add_counter(character_id, f"Counter{i}", 1)
                assert success is True
            # Try to add one more
            success, error = add_counter(character_id, "Counter4", 1)
            assert success is False
            assert error is not None
            assert "maximum" in error.lower()

    # Test invalid counter type
    def test_invalid_counter_type(self, test_characters_collection):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_invalid_type"
            character_name = "InvalidTypeChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            success, error = add_counter(
                character_id, "InvalidTypeCounter", 1, counter_type="not_a_type"
            )
            assert success is False
            assert error is not None
            assert "invalid" in error.lower() or "type" in error.lower()

    # Test malformed input (e.g., None or empty counter name)
    def test_malformed_counter_input(self, test_characters_collection):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_malformed"
            character_name = "MalformedChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            # None as counter name
            success, error = add_counter(character_id, None, 1)
            assert success is False
            assert error is not None
            # Empty string as counter name
            success, error = add_counter(character_id, "", 1)
            assert success is False
            assert error is not None
            # Whitespace only
            success, error = add_counter(character_id, "   ", 1)
            assert success is False
            assert error is not None

    # Test perm_is_maximum temp cannot exceed perm on init
    def test_perm_is_maximum_temp_cannot_exceed_perm_on_init(self):
        c = Counter(
            "Test", 6, 5, "general", counter_type=CounterTypeEnum.perm_is_maximum.value
        )
        assert c.temp == 5

    # Test perm_is_maximum_bedlam temp and bedlam cannot exceed perm on init
    def test_perm_is_maximum_bedlam_temp_and_bedlam_cannot_exceed_perm_on_init(self):
        c = Counter(
            "Test",
            6,
            5,
            "general",
            bedlam=5,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )
        assert c.temp == 5 and c.bedlam == 5
        with pytest.raises(ValueError):
            Counter(
                "Test",
                5,
                5,
                "general",
                bedlam=6,
                counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            )
        c = Counter(
            "Test",
            5,
            5,
            "general",
            bedlam=5,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )
        assert c.temp == 5 and c.bedlam == 5

    # Test updating a perm_is_maximum_bedlam counter
    def test_update_perm_is_maximum_bedlam_counter(self, test_characters_collection):
        from counter import CounterTypeEnum

        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_bedlam"
            character_name = "Bedlam Character"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            add_counter(
                character_id,
                "BedlamCounter",
                2,
                counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            )
            success, error = update_counter(character_id, "BedlamCounter", "temp", 10)
            assert success is True
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == "BedlamCounter"), None)
            assert counter.temp == counter.perm
            success, error = update_counter(character_id, "BedlamCounter", "temp", -20)
            assert not success
            assert "below zero" in error

    # Test initializing perm_is_maximum and perm_is_maximum_bedlam with temp > perm
    def test_init_perm_is_maximum_and_bedlam_temp_above_perm(self):
        from counter import Counter, CounterTypeEnum

        c = Counter(
            "MaxCounterInit",
            6,
            5,
            "general",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )
        assert c.temp == 5
        c = Counter(
            "BedlamCounterInit",
            6,
            5,
            "general",
            bedlam=2,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )
        assert c.temp == 5 and c.bedlam == 2

    def test_single_number_counter_temp_and_perm_sync(self, test_characters_collection):
        with patch("utils.characters_collection", test_characters_collection):
            user_id = "test_user_single_number"
            character_name = "SingleNumberChar"
            add_user_character(user_id, character_name)
            character_id = get_character_id_by_user_and_name(user_id, character_name)
            # Add single_number counter
            counter_name = "SingleNum"
            success, error = add_counter(
                character_id, counter_name, 3, counter_type="single_number"
            )
            assert success is True
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            # Both temp and perm should be equal to temp (3)
            assert counter.temp == 3
            assert counter.perm == 3
            # Increment temp by 7, both should be 10
            success, error = update_counter(character_id, counter_name, "temp", 7)
            assert success is True
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == 10
            assert counter.perm == 10
            # Decrement perm by 8, both should be 2
            success, error = update_counter(character_id, counter_name, "perm", -8)
            assert success is True
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == 2
            assert counter.perm == 2
            # Try to decrement temp below zero (should fail)
            success, error = update_counter(character_id, counter_name, "temp", -5)
            assert not success
            assert "below zero" in error
            counters = get_counters_for_character(character_id)
            counter = next((c for c in counters if c.counter == counter_name), None)
            assert counter.temp == 2
            assert counter.perm == 2
