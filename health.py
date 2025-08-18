import enum


class HealthTypeEnum(enum.Enum):
    normal = "normal"
    chimerical = "chimerical"


class DamageEnum(enum.Enum):
    Aggravated = "Aggravated"
    Lethal = "Lethal"
    Bashing = "Bashing"


class HealthLevelEnum(enum.Enum):
    Bruised = "Bruised"
    Hurt = "Hurt"
    Injured = "Injured"
    Wounded = "Wounded"
    Mauled = "Mauled"
    Crippled = "Crippled"
    Incapacitated = "Incapacitated"


HEALTH_LEVELS = {
    "Bruised": 0,
    "Hurt": -1,
    "Injured": -1,
    "Wounded": -2,
    "Mauled": -2,
    "Crippled": -4,
    "Incapacitated": -999,
}


class Health:
    def __init__(self, health_type, damage=None, health_levels=None):
        self.health_type = health_type
        self.damage = damage if damage is not None else []
        # Add all health level names in definition order
        if health_levels is None:
            self.health_levels = list(HEALTH_LEVELS.keys())
        else:
            self.health_levels = health_levels

    @classmethod
    def from_dict(cls, d):
        return cls(
            health_type=d.get("health_type"),
            damage=d.get("damage", []),
            health_levels=d.get("health_levels", None),
        )

    def set_health_levels(self, levels):
        self.health_levels = [hl for hl in levels]

    def add_damage(self, levels: int, damage_type: DamageEnum):
        """Main damage application function that orchestrates the damage application process."""
        # First fill empty health levels with damage
        available_slots = self._calculate_available_slots()
        damage_added, remaining = self._add_damage_to_empty_slots(
            levels, damage_type, available_slots
        )

        # If there's remaining damage, upgrade existing damage
        converted, not_taken = 0, 0
        if remaining > 0:
            converted, not_taken = self._upgrade_existing_damage(remaining, damage_type)

        # Return message if damage couldn't be fully applied
        return self._generate_damage_message(not_taken, damage_type)

    def _calculate_available_slots(self):
        """Calculate how many empty health level slots are available."""
        total_levels = len(self.health_levels)
        return total_levels - len(self.damage)

    def _add_damage_to_empty_slots(
        self, levels: int, damage_type: DamageEnum, available_slots: int
    ):
        """Add damage to empty health level slots. Only prepend if there is space; never shift or reorder existing damage."""
        to_add = min(levels, available_slots)
        if to_add > 0 and available_slots > 0:
            self.damage = [damage_type.value] * to_add + self.damage
            # Sort damage by severity, with Aggravated first, then Lethal, then Bashing
            # Use a list of specific order instead of enum to ensure consistent sorting
            damage_order = {
                DamageEnum.Aggravated.value: 0,
                DamageEnum.Lethal.value: 1,
                DamageEnum.Bashing.value: 2,
            }
            # Use a stable sort to preserve the relative order of duplicate entries
            self.damage = sorted(
                self.damage, key=lambda d: damage_order.get(d, float("inf"))
            )
        # If no slots are available, do not modify self.damage
        return to_add, levels - to_add

    def _upgrade_existing_damage(self, remaining: int, damage_type: DamageEnum):
        """
        Upgrade existing damage in-place, starting from the top of the tracker.
        Only upgrade bashing slots, never shift or reorder.
        - Additional bashing upgrades bashing to lethal.
        - Lethal upgrades bashing to lethal.
        - Aggravated upgrades bashing to aggravated.
        """
        converted = 0
        for i in range(len(self.damage)):
            if converted >= remaining:
                break
            if self.damage[i] == DamageEnum.Bashing.value:
                if damage_type.value == DamageEnum.Aggravated.value:
                    self.damage[i] = DamageEnum.Aggravated.value
                else:
                    # Both bashing and lethal upgrade bashing to lethal
                    self.damage[i] = DamageEnum.Lethal.value
                converted += 1

        # Sort damage after conversion to maintain consistent order
        if converted > 0:
            damage_order = {
                DamageEnum.Aggravated.value: 0,
                DamageEnum.Lethal.value: 1,
                DamageEnum.Bashing.value: 2,
            }
            self.damage = sorted(
                self.damage, key=lambda d: damage_order.get(d, float("inf"))
            )

        not_taken = remaining - converted
        return converted, not_taken

    def _generate_damage_message(self, not_taken: int, damage_type: DamageEnum):
        """Generate a message about damage that couldn't be applied."""
        if not_taken > 0:
            return f"{not_taken} additional levels of {damage_type.value} damage could not be taken (no room left in health track)."
        return None

    def remove_damage(self, levels: int):
        damage_list = self.damage
        if levels > 0:
            damage_list = damage_list[:-levels] if levels <= len(damage_list) else []
        self.damage = damage_list

    def map_damage_to_health(self):
        health_levels_list = self.health_levels
        damage_list = self.damage
        result = []
        for idx, hl_name in enumerate(health_levels_list):
            penalty = HEALTH_LEVELS[hl_name]
            damage_type = damage_list[idx] if idx < len(damage_list) else None
            result.append(
                {
                    "health_level": hl_name,
                    "damage_type": damage_type,
                    "penalty": penalty,
                }
            )
        return result

    def display(self, all_health_entries=None):
        """
        Display this health tracker, pairing with chimerical health if available.
        """
        if self.health_type == "normal" and all_health_entries:
            chimerical_health = next(
                (h for h in all_health_entries if h.get("health_type") == "chimerical"),
                None,
            )
            if chimerical_health:
                chimerical_obj = Health(
                    health_type=chimerical_health.get("health_type"),
                    damage=chimerical_health.get("damage", []),
                    health_levels=chimerical_health.get("health_levels", None),
                )
                return self._display_paired(chimerical_obj)
        return self._display_single()

    def _display_single(self):
        return display_health(self)

    def _display_paired(self, chimerical_obj):
        return display_health(self, chimerical_obj)


def display_health(normal_health, chimerical_health=None):
    """
    Display health levels with symbols for normal and optional chimerical health.

    Args:
        normal_health: A Health object of normal type
        chimerical_health: An optional Health object of chimerical type

    Returns:
        str: A formatted string displaying the health levels
    """
    symbol_map = {
        None: ":stop_button:",
        DamageEnum.Bashing.value: ":regional_indicator_b:",
        DamageEnum.Lethal.value: ":regional_indicator_l:",
        DamageEnum.Aggravated.value: ":regional_indicator_a:",
    }

    lines = []

    # If we have both normal and chimerical health, add a header row
    if chimerical_health:
        lines.append(":blue_square: :regional_indicator_c:")

    # Map both health objects to their entries
    normal_entries = normal_health.map_damage_to_health()
    chimerical_entries = (
        chimerical_health.map_damage_to_health() if chimerical_health else None
    )

    # Create display for each health level
    for idx, normal_entry in enumerate(normal_entries):
        normal_symbol = symbol_map.get(normal_entry["damage_type"], "O")
        penalty = normal_entry["penalty"]
        penalty_str = f" ({penalty})" if penalty != 0 and penalty != -999 else ""
        health_level_text = f"{normal_entry['health_level']}{penalty_str}"

        if chimerical_health and idx < len(chimerical_entries):
            chimerical_entry = chimerical_entries[idx]
            chimerical_symbol = symbol_map.get(chimerical_entry["damage_type"], "O")
            lines.append(f"{normal_symbol} {chimerical_symbol} {health_level_text}")
        else:
            lines.append(f"{normal_symbol} {health_level_text}")

    return "\n".join(lines)
