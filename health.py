import enum

class HealthTypeEnum(enum.Enum):
    normal = "normal"
    chimerical = "chimerical"

class DamageEnum(enum.Enum):
    Lethal = "Lethal"
    Aggravated = "Aggravated"
    Bashing = "Bashing"

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

    def set_health_levels(self, levels):
        self.health_levels = [hl for hl in levels]

    def add_damage(self, levels: int, damage_type: DamageEnum):
        """Main damage application function that orchestrates the damage application process."""
        # First fill empty health levels with damage
        available_slots = self._calculate_available_slots()
        damage_added, remaining = self._add_damage_to_empty_slots(levels, damage_type, available_slots)
        
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

    def _add_damage_to_empty_slots(self, levels: int, damage_type: DamageEnum, available_slots: int):
        """Add damage to empty health level slots."""
        to_add = min(levels, available_slots)
        if to_add > 0:
            self.damage = [damage_type.value] * to_add + self.damage
        
        # Return how much was added and how much remains
        return to_add, levels - to_add

    def _upgrade_existing_damage(self, remaining: int, damage_type: DamageEnum):
        """Upgrade existing damage based on new damage type."""
        converted = 0
        
        # Can only upgrade if incoming damage is more severe than existing
        for i in range(len(self.damage)):
            if converted >= remaining:
                break
                
            if self.damage[i] == DamageEnum.Bashing.value:
                if damage_type.value == DamageEnum.Bashing.value:
                    self.damage[i] = DamageEnum.Lethal.value
                else:
                    self.damage[i] = damage_type.value
                converted += 1
        
        # Return how much was converted and how much couldn't be applied
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
            result.append({
                'health_level': hl_name,
                'damage_type': damage_type,
                'penalty': penalty
            })
        return result

    def display(self):
        symbol_map = {
            None: ":stop_button:",
            DamageEnum.Bashing.value: ":regional_indicator_b:",
            DamageEnum.Lethal.value: ":regional_indicator_l:",
            DamageEnum.Aggravated.value: ":regional_indicator_a:"
        }
        lines = []
        for entry in self.map_damage_to_health():
            symbol = symbol_map.get(entry['damage_type'], "O")
            penalty = entry['penalty']
            penalty_str = f" ({penalty})" if penalty != 0 and penalty != -999 else ""
            lines.append(f"{symbol} {entry['health_level']}{penalty_str}")
        return "\n".join(lines)
