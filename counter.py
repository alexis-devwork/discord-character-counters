from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, joinedload
import enum

Base = declarative_base()

# Minimal UserCharacter class for ORM relationship
class UserCharacter(Base):
    __tablename__ = "user_characters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    character = Column(String, nullable=False)
    user = Column(String, nullable=False)
    counters = relationship("Counter", back_populates="character", cascade="all, delete-orphan")


class CounterTypeEnum(enum.Enum):
    single_number = "single_number"
    perm_is_maximum = "perm_is_maximum"
    perm_is_maximum_bedlam = "perm_is_maximum_bedlam"
    perm_not_maximum = "perm_not_maximum"
    xp = "xp"
    health = "health"


class PredefinedCounterEnum(enum.Enum):
    willpower = "willpower"
    mana = "mana"
    blood_pool = "blood pool"
    willpower_fae = "willpower_fae"
    glamour = "glamour"
    nightmare = "nightmare"
    banality = "banality"
    glory = "glory"
    honor = "honor"
    wisdom = "wisdom"
    rage = "rage"
    gnosis = "gnosis"
    item_with_charges = "item_with_charges"
    project_roll = "project_roll"


class CategoryEnum(enum.Enum):
    tempers = "tempers"
    reknown = "reknown"
    general = "general"
    health = "health"
    items = "items"
    other = "other"
    projects = "projects"
    xp = "xp"

class Counter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    counter = Column(String, nullable=False)
    temp = Column(Integer, nullable=False)
    perm = Column(Integer, nullable=False)
    character_id = Column(Integer, ForeignKey("user_characters.id"), nullable=False)
    category = Column(String, nullable=False, default=CategoryEnum.general.value)
    comment = Column(String, nullable=True)
    bedlam = Column(Integer, nullable=True, default=0)  # Renamed back from third_counter to bedlam
    counter_type = Column(String, nullable=False, default="single_number")
    character = relationship("UserCharacter", back_populates="counters")

    def generate_display(self, fully_unescape_func):
        base = f"{fully_unescape_func(self.counter)}: {self.temp}/{self.perm}"

        if self.counter_type == CounterTypeEnum.perm_is_maximum_bedlam.value:
            if not self.bedlam:
                self.bedlam = 0
            spent_pts = self.perm - self.temp
            unspent_bedlam = self.bedlam - spent_pts if spent_pts < self.bedlam else 0
            return f"{base} (bedlam: {unspent_bedlam}/{self.bedlam})"
        return base

class CounterFactory:
    @staticmethod
    def create(counter_type: PredefinedCounterEnum, character, perm, comment=None, override_name=None):
        name = override_name if override_name else counter_type.value
        match counter_type:
            case PredefinedCounterEnum.glory:
                return CounterFactory.create_glory(character, perm, comment, name)
            case PredefinedCounterEnum.honor:
                return CounterFactory.create_honor(character, perm, comment, name)
            case PredefinedCounterEnum.wisdom:
                return CounterFactory.create_wisdom(character, perm, comment, name)
            case PredefinedCounterEnum.willpower:
                return CounterFactory.create_willpower(character, perm, comment, name)
            case PredefinedCounterEnum.mana:
                return CounterFactory.create_mana(character, perm, comment, name)
            case PredefinedCounterEnum.blood_pool:
                return CounterFactory.create_blood_pool(character, perm, comment, name)
            case PredefinedCounterEnum.willpower_fae:
                return CounterFactory.create_willpower_fae(character, perm, comment, "willpower")
            case PredefinedCounterEnum.glamour:
                return CounterFactory.create_glamour(character, perm, comment, name)
            case PredefinedCounterEnum.nightmare:
                return CounterFactory.create_nightmare(character, comment, name)
            case PredefinedCounterEnum.banality:
                return CounterFactory.create_banality(character, perm, comment, name)
            case PredefinedCounterEnum.rage:
                return CounterFactory.create_rage(character, perm, comment, name)
            case PredefinedCounterEnum.gnosis:
                return CounterFactory.create_gnosis(character, perm, comment, name)
            case PredefinedCounterEnum.item_with_charges:
                return CounterFactory.create_item_with_charges(character, perm, comment, name)
            case PredefinedCounterEnum.project_roll:
                return CounterFactory.create_project_roll(character, perm, comment, name)
            case _:
                raise ValueError("Unknown counter type")

    @staticmethod
    def create_willpower(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "willpower",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_mana(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "mana",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.general.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_blood_pool(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "blood pool",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.general.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_willpower_fae(character, perm, comment=None, name=None):
        # Always use "willpower" as the display name
        return Counter(
            counter="willpower",
            temp=perm,
            perm=perm,
            bedlam=0,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_glamour(character, perm, comment=None, name=None):
        return Counter(
            counter="glamour" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_nightmare(character, comment=None, name=None):
        return Counter(
            counter="nightmare" if not name else name,
            temp=0,
            perm=10,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_banality(character, perm, comment=None, name=None):
        return Counter(
            counter="banality" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_glory(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "glory",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_honor(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "honor",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_wisdom(character, perm, comment=None, name=None):
        return Counter(
            counter=name if name else "wisdom",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_rage(character, perm, comment=None, name=None):
        return Counter(
            counter="rage" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_gnosis(character, perm, comment=None, name=None):
        return Counter(
            counter="gnosis" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_item_with_charges(character, perm, comment=None, name=None):
        if not name:
            raise ValueError("A name must be provided for item_with_charges counters.")
        return Counter(
            counter=name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.items.value,
            comment=comment,
            character=character
        )

    @staticmethod
    def create_project_roll(character, perm, comment=None, name=None):
        if not name:
            raise ValueError("A name must be provided for project_roll counters.")
        return Counter(
            counter=name,
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.projects.value,
            comment=comment,
            character=character
        )

def create_all_tables(engine):
    Base.metadata.create_all(engine)

class SplatEnum(enum.Enum):
    sorc = "sorc"
    changeling = "changeling"
    vampire = "vampire"
    fera = "fera"
