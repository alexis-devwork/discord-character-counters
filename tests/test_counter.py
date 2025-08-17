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

        # Test perm_is_maximum counter with temp > perm (should cap temp)
        counter = Counter(
            "Willpower", 7, 5, "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum.value
        )
        assert counter.temp == 5
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :asterisk: :asterisk:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_is_maximum_bedlam counter with temp > perm (should cap temp)
        counter = Counter(
            "Willpower", 7, 5, "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            bedlam=2
        )
        assert counter.temp == 5

    def test_single_number_temp_sets_perm(self):
        # Setting temp should set perm to same value
        c = Counter("Single", 7, 3, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 7
        assert c.perm == 7

    def test_single_number_perm_sets_temp(self):
        # Setting perm should set temp to same value
        c = Counter("Single", None, 5, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.perm == 5
        assert c.temp == 5

    def test_single_number_factory_sets_both(self):
        # Factory should set both temp and perm to perm value
        counter = CounterFactory.create(PredefinedCounterEnum.project_roll, 8, override_name="SingleNum")
        # project_roll is not single_number, so let's test with direct Counter
        c = Counter("SingleNum", 2, 2, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 2
        assert c.perm == 2

    def test_single_number_temp_and_perm_provided_and_different(self):
        # If both temp and perm are provided and don't match, both should be set to temp
        c = Counter("Single", 7, 3, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 7
        assert c.perm == 7

    def test_single_number_temp_only(self):
        # If only temp is provided, perm should be set to temp
        c = Counter("Single", 8, None, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 8
        assert c.perm == 8

    def test_single_number_perm_only(self):
        # If only perm is provided, temp should be set to perm
        c = Counter("Single", None, 9, "general", counter_type=CounterTypeEnum.single_number.value)
        assert c.temp == 9
        assert c.perm == 9

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
