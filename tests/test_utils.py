import pytest
from unittest.mock import patch, MagicMock
from utils import (
    sanitize_string,
    validate_length,
    sanitize_and_validate,
    fully_unescape,
    generate_counters_output,
    add_counter,
    update_counter,
    add_predefined_counter,
    get_character_id_by_user_and_name,
    CategoryEnum,
    PredefinedCounterEnum,
    CounterFactory,
    MAX_COUNTERS_PER_CHARACTER,
    MAX_FIELD_LENGTH,
)
from counter import Counter, CounterTypeEnum


class TestSanitizationFunctions:
    def test_sanitize_string(self):
        # Test with normal string
        assert sanitize_string("Normal String") == "Normal String"

        # Test with HTML entities
        assert sanitize_string("<script>alert('XSS')</script>") == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"

        # Test with control characters
        assert sanitize_string("Test\x00String\x1f") == "TestString"

        # Test with None
        assert sanitize_string(None) is None

    def test_validate_length(self):
        # Test valid length
        assert validate_length("field", "abc", 5) is True

        # Test exact length
        assert validate_length("field", "abcde", 5) is True

        # Test too long
        assert validate_length("field", "abcdef", 5) is False

        # Test with None
        assert validate_length("field", None, 5) is False

    def test_sanitize_and_validate(self):
        # Test valid input
        assert sanitize_and_validate("field", "abc", 20) == "abc"

        # Test input exceeding max length
        with pytest.raises(ValueError, match="Field must be at most 20 characters."):
            sanitize_and_validate("field", "abcdefghijk" * 2, 20)

        # Test sanitization with HTML
        assert sanitize_and_validate("field", "<b>test</b>", 50) == "&lt;b&gt;test&lt;/b&gt;"

        # Test sanitization and validation together
        with pytest.raises(ValueError, match="Field must be at most 20 characters."):
            sanitize_and_validate("field", "<script>" + "a" * 50, 20)

        # Test empty string
        assert sanitize_and_validate("field", "", 20) == ""

        # Test with None
        with pytest.raises(ValueError, match="Field must be at most 20 characters."):
            sanitize_and_validate("field", None, 20)

    def test_fully_unescape(self):
        # Test HTML entities
        assert fully_unescape("&lt;test&gt;") == "<test>"

        # Test numeric entities
        assert fully_unescape("&#65;&#66;&#67;") == "ABC"

        # Test hex entities
        assert fully_unescape("&#x41;&#x42;&#x43;") == "ABC"

        # Test mixed
        assert fully_unescape("&lt;&#65;&#x42;&gt;") == "<AB>"


class TestGenerateCountersOutput:
    def test_generate_counters_output_empty(self):
        counters = []
        result = generate_counters_output(counters, fully_unescape)
        assert result == ""

    def test_generate_counters_output_single_category(self):
        counters = [
            Counter("Willpower", 5, 10, CategoryEnum.tempers.value),
            Counter("Rage", 3, 5, CategoryEnum.tempers.value),
        ]
        result = generate_counters_output(counters, fully_unescape)
        assert "**Tempers**" in result
        assert "Willpower" in result
        assert "Rage" in result

    def test_generate_counters_output_multiple_categories(self):
        counters = [
            Counter("Willpower", 5, 10, CategoryEnum.tempers.value),
            Counter("Glory", 3, 5, CategoryEnum.reknown.value),
            Counter("Magic Wand", 2, 3, CategoryEnum.items.value),
        ]
        result = generate_counters_output(counters, fully_unescape)

        # Check for all categories
        assert "**Tempers**" in result
        assert "**Reknown**" in result
        assert "**Items**" in result

        # Check for counters
        assert "Willpower" in result
        assert "Glory" in result
        assert "Magic Wand" in result

    def test_generate_counters_output_with_comments(self):
        counters = [
            Counter("Willpower", 5, 10, CategoryEnum.tempers.value, "Important stat"),
            Counter("Glory", 3, 5, CategoryEnum.reknown.value),
        ]
        result = generate_counters_output(counters, fully_unescape)

        # Check for comment
        assert "-# Important stat" in result


@pytest.fixture
def fake_characters_collection(monkeypatch):
    class FakeCollection:
        def __init__(self):
            self.chars = {}
        def find_one(self, query):
            if "_id" in query:
                for c in self.chars.values():
                    if c.get("_id") == query["_id"]:
                        return c
            elif "user" in query and "character" in query:
                for c in self.chars.values():
                    if c.get("user") == query["user"] and c.get("character") == query["character"]:
                        return c
            return None
        def update_one(self, query, update):
            char = self.find_one(query)
            if char:
                char.update(update["$set"])
        def insert_one(self, doc):
            # Simulate MongoDB assigning an _id if not present
            if "_id" not in doc:
                import bson
                doc["_id"] = bson.ObjectId()
            self.chars[doc["_id"]] = doc
        def count_documents(self, query):
            return sum(1 for c in self.chars.values() if c.get("user") == query["user"])
    fake = FakeCollection()
    monkeypatch.setattr("utils.characters_collection", fake)
    return fake

def make_character_doc(user="u", character="c", _id="507f1f77bcf86cd799439011", counters=None):
    return {
        "user": user,
        "character": character,
        "_id": _id,
        "counters": counters if counters is not None else [],
        "health": [],
    }

def test_add_counter_negative_values(fake_characters_collection):
    char_doc = make_character_doc()
    fake_characters_collection.chars["507f1f77bcf86cd799439011"] = char_doc
    # Negative temp
    success, error = add_counter("507f1f77bcf86cd799439011", "test", -1, 1)
    assert not success and "below zero" in error
    # Negative perm
    success, error = add_counter("507f1f77bcf86cd799439011", "test", 1, -1)
    assert not success and "below zero" in error

def test_update_counter_negative_values(fake_characters_collection):
    char_doc = make_character_doc(counters=[{"counter": "test", "temp": 1, "perm": 1, "counter_type": "single_number"}])
    fake_characters_collection.chars["507f1f77bcf86cd799439011"] = char_doc
    # Negative update
    success, error = update_counter("507f1f77bcf86cd799439011", "test", "temp", -2)
    assert not success and "below zero" in error

def test_add_counter_empty_name(fake_characters_collection):
    char_doc = make_character_doc()
    fake_characters_collection.chars["507f1f77bcf86cd799439011"] = char_doc
    success, error = add_counter("507f1f77bcf86cd799439011", "   ", 1, 1)
    assert not success and "empty" in error

def test_add_counter_invalid_type(fake_characters_collection):
    char_doc = make_character_doc()
    fake_characters_collection.chars["507f1f77bcf86cd799439011"] = char_doc
    success, error = add_counter("507f1f77bcf86cd799439011", "test", 1, 1, counter_type="not_a_type")
    assert not success and "invalid" in error.lower()

def test_add_counter_duplicate_name(fake_characters_collection):
    # Create character first
    user_id = "u"
    character = "c"
    from utils import add_user_character, get_character_id_by_user_and_name
    add_user_character(user_id, character)
    character_id = get_character_id_by_user_and_name(user_id, character)
    # Add initial counter
    add_counter(character_id, "test", 1, 1)
    # Try to add duplicate
    success, error = add_counter(character_id, "test", 2, 2)
    assert not success and "exists" in error

def test_add_counter_max_limit(fake_characters_collection, monkeypatch):
    # Create character first
    user_id = "u"
    character = "c"
    from utils import add_user_character, get_character_id_by_user_and_name
    add_user_character(user_id, character)
    character_id = get_character_id_by_user_and_name(user_id, character)
    # Fill up counters
    for i in range(MAX_COUNTERS_PER_CHARACTER):
        add_counter(character_id, f"c{i}", 1, 1)
    # Try to add one more
    success, error = add_counter(character_id, "new", 1, 1)
    assert not success and "maximum" in error

def test_add_predefined_counter_invalid_type(fake_characters_collection):
    # Create character first
    user_id = "u"
    character = "c"
    from utils import add_user_character, get_character_id_by_user_and_name
    add_user_character(user_id, character)
    character_id = get_character_id_by_user_and_name(user_id, character)
    success, error = add_predefined_counter(character_id, "not_a_type", 1)
    assert not success and "invalid" in error.lower()

def test_add_predefined_counter_duplicate(fake_characters_collection):
    # Create character first
    user_id = "u"
    character = "c"
    from utils import add_user_character, get_character_id_by_user_and_name
    add_user_character(user_id, character)
    character_id = get_character_id_by_user_and_name(user_id, character)
    # Add initial counter
    add_predefined_counter(character_id, PredefinedCounterEnum.willpower.value, 1)
    # Try to add duplicate
    success, error = add_predefined_counter(character_id, PredefinedCounterEnum.willpower.value, 2)
    assert not success and "exists" in error

def test_add_predefined_counter_max_limit(fake_characters_collection):
    # Create character first
    user_id = "u"
    character = "c"
    from utils import add_user_character, get_character_id_by_user_and_name
    add_user_character(user_id, character)
    character_id = get_character_id_by_user_and_name(user_id, character)
    # Fill up counters
    for i in range(MAX_COUNTERS_PER_CHARACTER):
        add_counter(character_id, f"c{i}", 1, 1)
    # Try to add predefined counter
    success, error = add_predefined_counter(character_id, PredefinedCounterEnum.willpower.value, 1)
    assert not success and "maximum" in error

def test_counter_factory_negative_perm():
    from counter import CounterFactory, PredefinedCounterEnum
    with pytest.raises(ValueError):
        CounterFactory.create(PredefinedCounterEnum.willpower, -1)

def test_counter_factory_invalid_type():
    from counter import CounterFactory
    with pytest.raises(ValueError):
        CounterFactory.create("not_enum", 1)

def test_counter_factory_item_with_charges_requires_name():
    from counter import CounterFactory, PredefinedCounterEnum
    with pytest.raises(ValueError):
        CounterFactory.create(PredefinedCounterEnum.item_with_charges, 1)

def test_counter_factory_project_roll_requires_name():
    from counter import CounterFactory, PredefinedCounterEnum
    with pytest.raises(ValueError):
        CounterFactory.create(PredefinedCounterEnum.project_roll, 1)

def test_add_counter_bedlam_negative(fake_characters_collection):
    # Directly test Counter creation with negative bedlam
    from counter import Counter
    with pytest.raises(ValueError):
        Counter("willpower", 1, 1, CategoryEnum.tempers.value, bedlam=-1)

def test_add_counter_set_temp_below_zero(fake_characters_collection):
    # Simulate setting temp directly below zero
    from counter import Counter
    # Should raise on creation
    with pytest.raises(ValueError):
        Counter("willpower", -5, 1, CategoryEnum.tempers.value)

def test_add_counter_set_perm_below_zero(fake_characters_collection):
    # Simulate setting perm directly below zero
    from counter import Counter
    with pytest.raises(ValueError):
        Counter("willpower", 1, -5, CategoryEnum.tempers.value)

def test_add_counter_set_bedlam_below_zero(fake_characters_collection):
    # Simulate setting bedlam directly below zero
    from counter import Counter
    with pytest.raises(ValueError):
        Counter("willpower", 1, 1, CategoryEnum.tempers.value, bedlam=-10)
