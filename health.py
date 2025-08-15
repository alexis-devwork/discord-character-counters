from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import declarative_base
import enum
import json

# Use the same Base as counter.py to ensure all tables are in the same metadata
from counter import Base

class HealthTypeEnum(enum.Enum):
    normal = "normal"
    chimerical = "chimerical"

class DamageEnum(enum.Enum):
    Lethal = "Lethal"
    Aggravated = "Aggravated"
    Bashing = "Bashing"

# Replace HealthLevelEnum with a dict
HEALTH_LEVELS = {
    "Bruised": 0,
    "Hurt": -1,
    "Injured": -1,
    "Wounded": -2,
    "Mauled": -2,
    "Crippled": -4,
    "Incapacitated": -999,
}

class Health(Base):
    __tablename__ = "health"
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey("user_characters.id"), nullable=False)
    health_type = Column(Enum(HealthTypeEnum), nullable=False)
    damage = Column(Text, nullable=False)  # Store as JSON string
    health_levels = Column(Text, nullable=False)  # Store as JSON string

    def __init__(self, character, health_type):
        self.character_id = character.id
        self.health_type = health_type
        self.damage = json.dumps([])
        # Add all health level names in definition order
        names = list(HEALTH_LEVELS.keys())
        self.health_levels = json.dumps(names)

    def set_health_levels(self, levels):
        # Accepts a list of names, stores as names
        names = []
        for hl in levels:
            names.append(hl)
        self.health_levels = json.dumps(names)

    def add_damage(self, levels: int, damage_type: DamageEnum):
        damage_list = json.loads(self.damage)
        total_levels = len(json.loads(self.health_levels))
        message = None
        available_slots = total_levels - len(damage_list)
        to_add = min(levels, available_slots)
        if to_add > 0:
            damage_list = [damage_type.value] * to_add + damage_list
        remaining = levels - to_add
        if remaining > 0:
            converted = 0
            for i in range(len(damage_list)):
                if converted >= remaining:
                    break
                if damage_list[i] == DamageEnum.Bashing.value:
                    if damage_type.value == DamageEnum.Bashing.value:
                        damage_list[i] = DamageEnum.Lethal.value
                    else:
                        damage_list[i] = damage_type.value
                    converted += 1
            not_taken = remaining - converted
            if not_taken > 0:
                message = f"{not_taken} additional levels of {damage_type.value} damage could not be taken (no room left in health track)."
        self.damage = json.dumps(damage_list)
        return message

    def remove_damage(self, levels: int):
        damage_list = json.loads(self.damage)
        if levels > 0:
            damage_list = damage_list[:-levels] if levels <= len(damage_list) else []
        self.damage = json.dumps(damage_list)

    def map_damage_to_health(self):
        health_levels_list = json.loads(self.health_levels)
        damage_list = json.loads(self.damage)
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

# Add this relationship to UserCharacter in counter.py:
# health_entries = relationship("Health", back_populates="character", cascade="all, delete-orphan")
