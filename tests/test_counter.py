import pytest
from counter import (
    Counter,
    CounterFactory,
    PredefinedCounterEnum,
    CounterTypeEnum,
    CategoryEnum,
)

class TestCounter:

    def test_generate_display_pretty(self):
        # Test perm_is_maximum_bedlam counter
        counter = Counter(
            "Willpower", 3, 5, "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            bedlam=2
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :red_square: :red_square:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_is_maximum counter
        counter = Counter(
            "Willpower", 3, 5, "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum.value
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :stop_button: :stop_button:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_not_maximum counter
        counter = Counter(
            "Glory", 2, 5, "reknown",
            counter_type=CounterTypeEnum.perm_not_maximum.value
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Glory\n:stop_button: :stop_button: :stop_button: :stop_button: :stop_button:\n:asterisk: :asterisk:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

class TestCounterFactory:

    def test_create_factory_method(self):
        # Test creating willpower through factory method
        counter = CounterFactory.create(PredefinedCounterEnum.willpower, 5, "Test comment")
        assert counter.counter == "willpower"
        assert counter.temp == 5
        assert counter.perm == 5

        # Test with override name for supported types
        counter = CounterFactory.create(PredefinedCounterEnum.glory, 5, override_name="Custom Glory")
        assert counter.counter == "Custom Glory"

class TestPredefinedCounterFactory:

    def test_predefined_counter_factory_creates_expected_counters(self):
        from counter import CounterFactory, PredefinedCounterEnum

        # Willpower
        counter = CounterFactory.create(PredefinedCounterEnum.willpower, 7, "A comment")
        assert counter.counter == "willpower"
        assert counter.temp == 7
        assert counter.perm == 7
        assert counter.comment == "A comment"

        # Mana
        counter = CounterFactory.create(PredefinedCounterEnum.mana, 5)
        assert counter.counter == "mana"
        assert counter.temp == 5
        assert counter.perm == 5

        # Override name
        counter = CounterFactory.create(PredefinedCounterEnum.glory, 3, override_name="Renown")
        assert counter.counter == "Renown"
        assert counter.temp == 0
        assert counter.perm == 3

        # Invalid enum should raise
        import pytest
        with pytest.raises(ValueError):
            CounterFactory.create(12345, 1)  # Pass an invalid type, not a string
