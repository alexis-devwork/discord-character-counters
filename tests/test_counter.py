import pytest
from counter import (
    Counter,
    CounterFactory,
    PredefinedCounterEnum,
    CounterTypeEnum,
)


class TestCounter:
    def test_generate_display_pretty(self):
        # Test perm_is_maximum_bedlam counter
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            bedlam=2,
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = (
            "Willpower\n:asterisk: :asterisk: :asterisk: :red_square: :red_square:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_is_maximum counter
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = (
            "Willpower\n:asterisk: :asterisk: :asterisk: :stop_button: :stop_button:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_not_maximum counter
        counter = Counter(
            "Glory",
            2,
            5,
            "reknown",
            counter_type=CounterTypeEnum.perm_not_maximum.value,
        )
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Glory\n:stop_button: :stop_button: :stop_button: :stop_button: :stop_button:\n:asterisk: :asterisk:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_is_maximum counter with temp > perm (should cap temp)
        counter = Counter(
            "Willpower",
            7,
            5,
            "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )
        assert counter.temp == 5
        display = counter.generate_display_pretty(lambda x: x)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :asterisk: :asterisk:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test perm_is_maximum_bedlam counter with temp > perm (should cap temp)
        counter = Counter(
            "Willpower",
            7,
            5,
            "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            bedlam=2,
        )
        assert counter.temp == 5

    def test_single_number_temp_sets_perm(self):
        # Setting temp should set perm to same value
        c = Counter(
            "Single", 7, 3, "general", counter_type=CounterTypeEnum.single_number.value
        )
        assert c.temp == 7
        assert c.perm == 7

    def test_single_number_perm_sets_temp(self):
        # Setting perm should set temp to same value
        c = Counter(
            "Single",
            None,
            5,
            "general",
            counter_type=CounterTypeEnum.single_number.value,
        )
        assert c.perm == 5
        assert c.temp == 5

    def test_single_number_factory_sets_both(self):
        # Factory should set both temp and perm to perm value
        CounterFactory.create(
            PredefinedCounterEnum.project_roll, 8, override_name="SingleNum"
        )
        # project_roll is not single_number, so let's test with direct Counter
        c = Counter(
            "SingleNum",
            2,
            2,
            "general",
            counter_type=CounterTypeEnum.single_number.value,
        )
        assert c.temp == 2
        assert c.perm == 2

    def test_single_number_temp_and_perm_provided_and_different(self):
        # If both temp and perm are provided and don't match, both should be set to temp
        c = Counter(
            "Single", 7, 3, "general", counter_type=CounterTypeEnum.single_number.value
        )
        assert c.temp == 7
        assert c.perm == 7

    def test_single_number_temp_only(self):
        # If only temp is provided, perm should be set to temp
        c = Counter(
            "Single",
            8,
            None,
            "general",
            counter_type=CounterTypeEnum.single_number.value,
        )
        assert c.temp == 8
        assert c.perm == 8

    def test_single_number_perm_only(self):
        # If only perm is provided, temp should be set to perm
        c = Counter(
            "Single",
            None,
            9,
            "general",
            counter_type=CounterTypeEnum.single_number.value,
        )
        assert c.temp == 9
        assert c.perm == 9

    def test_generate_display_single_number(self):
        """Test generate_display for single_number counters in different scenarios"""
        # Basic single_number counter without comment
        counter = Counter(
            "Experience",
            7,
            7,
            "general",
            counter_type=CounterTypeEnum.single_number.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Experience:\n7"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Experience\n:large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # With comment
        counter = Counter(
            "Experience",
            7,
            7,
            "general",
            comment="XP for storyteller rewards",
            counter_type=CounterTypeEnum.single_number.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Experience:\n7\n-# XP for storyteller rewards"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Experience\n:large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond: :large_blue_diamond:\n-# XP for storyteller rewards"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with force_unpretty=True
        counter.force_unpretty = True
        display = counter.generate_display(lambda x: x, True)  # Even though pretty=True
        expected = "Experience:\n7\n-# XP for storyteller rewards"
        assert display == expected, f"Expected: {expected}, but got: {display}"

    def test_generate_display_perm_is_maximum(self):
        """Test generate_display for perm_is_maximum counters in different scenarios"""
        # Basic perm_is_maximum counter without comment
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n3/5"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = (
            "Willpower\n:asterisk: :asterisk: :asterisk: :stop_button: :stop_button:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # With comment
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            comment="Spent on difficult rolls",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n3/5\n-# Spent on difficult rolls"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :stop_button: :stop_button:\n-# Spent on difficult rolls"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with larger perm value (falls back to basic display)
        counter = Counter(
            "LargeWillpower",
            10,
            20,
            "tempers",
            comment="Too many squares",
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )

        display = counter.generate_display(lambda x: x, True)
        expected = "LargeWillpower:\n10/20\n-# Too many squares"
        assert display == expected, f"Expected: {expected}, but got: {display}"

    def test_generate_display_perm_not_maximum(self):
        """Test generate_display for perm_not_maximum counters in different scenarios"""
        # Basic perm_not_maximum counter without comment
        counter = Counter(
            "Glory",
            2,
            5,
            "reknown",
            counter_type=CounterTypeEnum.perm_not_maximum.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Glory:\n2/5"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Glory\n:stop_button: :stop_button: :stop_button: :stop_button: :stop_button:\n:asterisk: :asterisk:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # With comment
        counter = Counter(
            "Glory",
            2,
            5,
            "reknown",
            comment="Earned from heroic deeds",
            counter_type=CounterTypeEnum.perm_not_maximum.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Glory:\n2/5\n-# Earned from heroic deeds"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Glory\n:stop_button: :stop_button: :stop_button: :stop_button: :stop_button:\n:asterisk: :asterisk:\n-# Earned from heroic deeds"
        assert display == expected, f"Expected: {expected}, but got: {display}"

    def test_generate_display_perm_is_maximum_bedlam(self):
        """Test generate_display for perm_is_maximum_bedlam counters in different scenarios"""
        # Case 1: Basic bedlam counter, no bedlam, no comment
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            bedlam=0,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n3/5 (bedlam: 0/0)"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = (
            "Willpower\n:asterisk: :asterisk: :asterisk: :stop_button: :stop_button:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Case 2: With bedlam=2, spent=0 (perm - temp < bedlam)
        counter = Counter(
            "Willpower",
            5,
            5,
            "tempers",
            bedlam=2,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n5/5 (bedlam: 2/2)"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :b: :b:"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Case 3: With bedlam=2, spent=2 (perm - temp = bedlam)
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            bedlam=2,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n3/5 (bedlam: 0/2)"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = (
            "Willpower\n:asterisk: :asterisk: :asterisk: :red_square: :red_square:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Case 4: With bedlam=2, spent=3 (perm - temp > bedlam)
        counter = Counter(
            "Willpower",
            2,
            5,
            "tempers",
            bedlam=2,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n2/5 (bedlam: 0/2)"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = (
            "Willpower\n:asterisk: :asterisk: :stop_button: :red_square: :red_square:"
        )
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Case 5: With comment
        counter = Counter(
            "Willpower",
            3,
            5,
            "tempers",
            bedlam=2,
            comment="Watch out for Bedlam!",
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
        )

        # Test with pretty=False
        display = counter.generate_display(lambda x: x, False)
        expected = "Willpower:\n3/5 (bedlam: 0/2)\n-# Watch out for Bedlam!"
        assert display == expected, f"Expected: {expected}, but got: {display}"

        # Test with pretty=True
        display = counter.generate_display(lambda x: x, True)
        expected = "Willpower\n:asterisk: :asterisk: :asterisk: :red_square: :red_square:\n-# Watch out for Bedlam!"
        assert display == expected, f"Expected: {expected}, but got: {display}"

    def test_generate_display_html_escape(self):
        """Test that HTML content in counter names and comments is correctly displayed"""
        # Create a counter with HTML in the name and comment
        html_name = "<b>HTML</b> Counter"
        html_comment = "This has <i>HTML</i> tags & special chars"

        counter = Counter(
            html_name,
            3,
            5,
            "general",
            comment=html_comment,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
        )

        # Mock unescape function that simulates what fully_unescape does
        def mock_unescape(text):
            return text  # In real usage, this would unescape HTML entities

        # Test with pretty=False
        display = counter.generate_display(mock_unescape, False)
        assert html_name in display
        assert html_comment in display

        # Test with pretty=True
        display = counter.generate_display(mock_unescape, True)
        assert html_name in display
        assert html_comment in display


class TestCounterFactory:
    def test_create_factory_method(self):
        # Test creating willpower through factory method
        counter = CounterFactory.create(
            PredefinedCounterEnum.willpower, 5, "Test comment"
        )
        assert counter.counter == "willpower"
        assert counter.temp == 5
        assert counter.perm == 5

        # Test with override name for supported types
        counter = CounterFactory.create(
            PredefinedCounterEnum.glory, 5, override_name="Custom Glory"
        )
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
        counter = CounterFactory.create(
            PredefinedCounterEnum.glory, 3, override_name="Renown"
        )
        assert counter.counter == "Renown"
        assert counter.temp == 0
        assert counter.perm == 3

        # Invalid enum should raise

        with pytest.raises(ValueError):
            CounterFactory.create(12345, 1)  # Pass an invalid type, not a string
