from sqlalchemy import Column, Integer, String, ForeignKey, Enum, PickleType
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class HealthTypeEnum(enum.Enum):
    normal = "normal"
    chimerical = "chimerical"

class DamageEnum(enum.Enum):
    Lethal = "Lethal"
    Aggravated = "Aggravated"
    Bashing = "Bashing"  # Add Bashing to the enum

class HealthLevelEnum(enum.Enum):
    Bruised = 0
    Hurt = -1
    Injured = -1
    Wounded = -2
    Mauled = -2
    Crippled = -4
    Incapacitated = -999

HEALTH_LEVEL_ORDER = [
    HealthLevelEnum.Bruised,
    HealthLevelEnum.Hurt,
    HealthLevelEnum.Injured,
    HealthLevelEnum.Wounded,
    HealthLevelEnum.Mauled,
    HealthLevelEnum.Crippled,
    HealthLevelEnum.Incapacitated,
]

class Health(Base):
    __tablename__ = "health"
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey("user_characters.id"), nullable=False)
    health_type = Column(Enum(HealthTypeEnum), nullable=False)
    damage = Column(PickleType, nullable=False)  # List of DamageEnum
    health_levels = Column(PickleType, nullable=False)  # List of HealthLevelEnum

    def __init__(self, character, health_type):
        self.character = character
        self.health_type = health_type
        self.damage = []
        # Initialize with one of each health level, sorted
        self.health_levels = sorted(
            [hl for hl in HEALTH_LEVEL_ORDER],
            key=lambda x: HEALTH_LEVEL_ORDER.index(x)
        )

    def set_health_levels(self, levels):
        # Always sort from most to least using HEALTH_LEVEL_ORDER
        self.health_levels = sorted(
            levels,
            key=lambda x: HEALTH_LEVEL_ORDER.index(x)
        )

    def add_damage(self, levels: int, damage_type: DamageEnum):
        """
        Add 'levels' of 'damage_type' to the beginning of the damage list.
        Never allow damage entries to exceed the number of health levels.
        If the number of damage entries is less than the number of health levels,
        add damage until filled, then for any remaining levels, convert Bashing or add new damage as needed,
        but never exceed the maximum. If there are extra levels, respond with a message about how many could not be taken.
        """
        total_levels = len(self.health_levels)
        message = None
        available_slots = total_levels - len(self.damage)
        to_add = min(levels, available_slots)
        if to_add > 0:
            self.damage = [damage_type] * to_add + self.damage
        remaining = levels - to_add
        if remaining > 0:
            # Now self.damage is full, so convert Bashing up to remaining, but never exceed total_levels
            converted = 0
            for i in range(len(self.damage)):
                if converted >= remaining:
                    break
                if self.damage[i] == DamageEnum.Bashing:
                    self.damage[i] = damage_type
                    converted += 1
            # Calculate how many levels could not be taken (if not enough Bashing to convert)
            not_taken = remaining - converted
            if not_taken > 0:
                message = f"{not_taken} additional levels of {damage_type.value} damage could not be taken (no room left in health track)."
        return message

    def remove_damage(self, levels: int):
        """Remove 'levels' items from the end of the damage list."""
        if levels > 0:
            self.damage = self.damage[:-levels] if levels <= len(self.damage) else []

    def map_damage_to_health(self):
        """
        Returns an ordered list of dicts:
        {
            'health_level': HealthLevelEnum,
            'damage_type': DamageEnum or None,
            'penalty': int
        }
        Maps each health_level to the corresponding damage entry (or None if not present).
        """
        result = []
        for idx, hl in enumerate(self.health_levels):
            damage_type = self.damage[idx] if idx < len(self.damage) else None
            result.append({
                'health_level': hl,
                'damage_type': damage_type,
                'penalty': hl.value
            })
        return result

    def display(self):
        """
        Returns a formatted string of the health track, one row per line:
        O for no damage, B for bruised, L for lethal, A for agg,
        then the damage type, then (penalty) if not 0 or -999.
        """
        symbol_map = {
            None: "O",
            DamageEnum.Bashing: "B",
            DamageEnum.Lethal: "L",
            DamageEnum.Aggravated: "A"
        }
        lines = []
        for entry in self.map_damage_to_health():
            symbol = symbol_map.get(entry['damage_type'], "O")
            dmg_type = entry['damage_type'].value if entry['damage_type'] else "None"
            penalty = entry['penalty']
            penalty_str = f" ({penalty})" if penalty != 0 and penalty != -999 else ""
            lines.append(f"{symbol} {dmg_type}{penalty_str}")
        return "\n".join(lines)

# Add this relationship to UserCharacter in counter.py:
# health_entries = relationship("Health", back_populates="character", cascade="all, delete-orphan")
