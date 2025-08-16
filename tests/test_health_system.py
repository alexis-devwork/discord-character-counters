import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Import health-related functionality
from health import Health, HealthTypeEnum, DamageEnum, display_health

class TestHealthSystem:

    # Test health initialization
    def test_health_initialization(self):
        # Create a health object with default values
        health = Health(health_type=HealthTypeEnum.normal.value)

        # Check default values
        assert health.health_type == HealthTypeEnum.normal.value
        assert health.damage == []
        assert len(health.health_levels) > 0  # Should have default health levels

        # Create a health object with custom values
        custom_damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value]
        custom_levels = ["Level1", "Level2", "Level3"]
        health = Health(
            health_type=HealthTypeEnum.chimerical.value,
            damage=custom_damage,
            health_levels=custom_levels
        )

        # Check custom values
        assert health.health_type == HealthTypeEnum.chimerical.value
        assert health.damage == custom_damage
        assert health.health_levels == custom_levels

    # Test adding damage
    def test_add_damage(self):
        # Create a health object
        health = Health(health_type=HealthTypeEnum.normal.value)
        initial_levels = len(health.health_levels)

        # Add bashing damage
        levels_to_add = 2
        health.add_damage(levels_to_add, DamageEnum.Bashing)

        # Check if damage was added correctly
        assert len(health.damage) == levels_to_add
        assert all(d == DamageEnum.Bashing.value for d in health.damage)

        # Add more damage than health levels
        excess_levels = initial_levels + 1
        msg = health.add_damage(excess_levels, DamageEnum.Lethal)

        # Check if warning message was generated
        assert msg is not None
        # Check if damage list is at maximum length
        assert len(health.damage) == initial_levels

    # Test removing damage
    def test_remove_damage(self):
        # Create a health object with some damage
        health = Health(health_type=HealthTypeEnum.normal.value)
        health.damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value, DamageEnum.Aggravated.value]
        initial_damage = len(health.damage)

        # Remove some damage
        levels_to_remove = 2
        health.remove_damage(levels_to_remove)

        # Check if damage was removed correctly
        assert len(health.damage) == initial_damage - levels_to_remove

        # Remove more damage than exists
        health.remove_damage(10)

        # Check if damage list is empty
        assert len(health.damage) == 0

    # Test damage type upgrade logic
    def test_damage_upgrade(self):
        # Create a health object
        health = Health(health_type=HealthTypeEnum.normal.value)

        # Add bashing damage
        health.add_damage(1, DamageEnum.Bashing)
        assert health.damage[0] == DamageEnum.Bashing.value


        # Add another lethal damage (should add a new damage level)
        health.add_damage(1, DamageEnum.Lethal)
        assert health.damage[0] == DamageEnum.Lethal.value
        assert health.damage[1] == DamageEnum.Bashing.value
        assert len(health.damage) == 2  # Should now have 2 damage levels

        # Add aggravated damage (should upgrade the first lethal to aggravated)
        health.add_damage(1, DamageEnum.Aggravated)
        assert health.damage[0] == DamageEnum.Aggravated.value
        assert health.damage[1] == DamageEnum.Lethal.value
        assert health.damage[2] == DamageEnum.Bashing.value
        assert len(health.damage) == 3  # Should still have 2 damage levels

    # Test display health function
    def test_display_health(self):
        # Create normal health object
        normal_health = Health(health_type=HealthTypeEnum.normal.value)
        normal_health.damage = [DamageEnum.Bashing.value, DamageEnum.Lethal.value]

        # Test display with only normal health
        display = display_health(normal_health)
        assert display is not None
        assert ":regional_indicator_b:" in display  # Should show bashing damage
        assert ":regional_indicator_l:" in display  # Should show lethal damage

        # Create chimerical health object
        chimerical_health = Health(health_type=HealthTypeEnum.chimerical.value)
        chimerical_health.damage = [DamageEnum.Aggravated.value]

        # Test display with both normal and chimerical health
        combined_display = display_health(normal_health, chimerical_health)
        assert combined_display is not None
        assert ":blue_square: :regional_indicator_c:" in combined_display  # Should have header
        assert ":regional_indicator_b:" in combined_display  # Normal bashing
        assert ":regional_indicator_l:" in combined_display  # Normal lethal
        assert ":regional_indicator_a:" in combined_display  # Chimerical aggravated
