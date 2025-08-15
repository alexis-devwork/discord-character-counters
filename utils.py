import discord
from discord.ext import commands
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum
import html
import re
from config import (
    MAX_USER_CHARACTERS,
    MAX_COUNTERS_PER_CHARACTER,
    MAX_FIELD_LENGTH,
    MAX_COMMENT_LENGTH,
)


Base = declarative_base()

class UserCharacter(Base):
    __tablename__ = "user_characters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False)
    character = Column(String, nullable=False)
    counters = relationship("Counter", back_populates="character", cascade="all, delete-orphan")

class CategoryEnum(enum.Enum):
    general = "general"
    tempers = "tempers"
    xp = "xp"
    items = "items"
    projects = "projects"
    other = "other"

class Counter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    counter = Column(String, nullable=False)
    temp = Column(Integer, nullable=False)
    perm = Column(Integer, nullable=False)
    character_id = Column(Integer, ForeignKey("user_characters.id"), nullable=False)
    category = Column(String, nullable=False, default=CategoryEnum.general.value)
    comment = Column(String, nullable=True)  # <-- Added comment field
    character = relationship("UserCharacter", back_populates="counters")

engine = create_engine("sqlite:///db.sqlite3")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()

def validate_length(field: str, value: str, max_len: int) -> bool:
    return value is not None and len(value) <= max_len

def sanitize_and_validate(field: str, value: str, max_len: int) -> str:
    value = sanitize_string(value)
    if not validate_length(field, value, max_len):
        raise ValueError(f"{field.capitalize()} must be at most {max_len} characters.")
    return value

def sanitize_string(s: str) -> str:
    if s is None:
        return None
    # Remove control characters and escape HTML special chars
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    return html.escape(s)

def add_user_character(user_id: str, character: str):
    try:
        character = sanitize_and_validate("character", character, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    # Check if character already exists for this user (after length validation)
    existing = session.query(UserCharacter).filter_by(user=user_id, character=character).first()
    if existing:
        session.close()
        return False, "A character with that name already exists for you."
    # Check character limit
    count = session.query(UserCharacter).filter_by(user=user_id).count()
    if count >= MAX_USER_CHARACTERS:
        session.close()
        return False, f"You have reached the maximum number of characters ({MAX_USER_CHARACTERS})."
    new_entry = UserCharacter(user=user_id, character=character)
    session.add(new_entry)
    session.commit()
    session.close()
    return True, None

def get_all_user_characters_for_user(user_id: str):
    session = SessionLocal()
    results = session.query(UserCharacter).filter_by(user=user_id).all()
    session.close()
    return results

def add_counter(character_id: int, counter_name: str, temp: int, perm: int, category: str = CategoryEnum.general.value, comment: str = None):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
        if comment is not None:
            comment = sanitize_and_validate("comment", comment, MAX_COMMENT_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    char = session.query(UserCharacter).filter_by(id=character_id).first()
    if not char:
        session.close()
        return False, "Character not found."
    # Check if counter already exists for this character (after length validation)
    existing = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if existing:
        session.close()
        return False, "A counter with that name exists for this character."
    # Enforce maximum counters per character
    count = session.query(Counter).filter_by(character_id=character_id).count()
    if count >= MAX_COUNTERS_PER_CHARACTER:
        session.close()
        return False, f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER})."
    # Validate category
    if category not in CategoryEnum.__members__:
        category = CategoryEnum.general.value
    new_counter = Counter(counter=counter_name, temp=temp, perm=perm, character=char, category=category, comment=comment)
    session.add(new_counter)
    session.commit()
    session.close()
    return True, None

def update_counter(character_id: int, counter_name: str, field: str, delta: int):
    counter_name = sanitize_string(counter_name)
    session = SessionLocal()
    counter = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter:
        session.close()
        return False, "Counter not found."
    if field == "temp":
        new_value = counter.temp + delta
        if new_value < 0:
            session.close()
            return False, "Cannot decrement temp below zero."
        counter.temp = new_value
    elif field == "perm":
        new_value = counter.perm + delta
        if new_value < 0:
            session.close()
            return False, "Cannot decrement perm below zero."
        counter.perm = new_value
    else:
        session.close()
        return False, "Invalid field."
    session.commit()
    session.close()
    return True, None

def set_counter_comment(character_id: int, counter_name: str, comment: str):
    counter_name = sanitize_string(counter_name)
    comment = sanitize_string(comment)
    session = SessionLocal()
    counter = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter:
        session.close()
        return False, "Counter not found."
    counter.comment = comment
    session.commit()
    session.close()
    return True, None

def get_counters_for_character(character_id: int):
    session = SessionLocal()
    counters = session.query(Counter).filter_by(character_id=character_id).all()
    session.close()
    return counters

def get_character_id_by_user_and_name(user_id: str, character_name: str):
    try:
        character_name = sanitize_and_validate("character", character_name, MAX_FIELD_LENGTH)
    except ValueError:
        return None
    session = SessionLocal()
    char = session.query(UserCharacter).filter_by(user=user_id, character=character_name).first()
    result = char.id if char else None
    session.close()
    return result

# --- Autocomplete helpers ---
async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    session.close()
    return [
        discord.app_commands.Choice(name=char.character, value=char.character)
        for char in chars if current.lower() in char.character.lower()
    ][:25]

async def counter_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    counters = []
    for char in chars:
        for counter in char.counters:
            if current.lower() in counter.counter.lower():
                counters.append(counter.counter)
    session.close()
    unique_counters = list(dict.fromkeys(counters))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

async def category_autocomplete(interaction: discord.Interaction, current: str):
    categories = [c.value for c in CategoryEnum]
    return [
        discord.app_commands.Choice(name=cat, value=cat)
        for cat in categories if current.lower() in cat.lower()
    ][:25]

# --- Subcommand autocomplete for /avct ---
SUBCOMMANDS = [
    "addcharacter",
    "listcharacters",
    "addcounter",
    "changetemp",
    "changeperm",
    "listcounters",
    "hellobyname"
]

async def subcommand_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=cmd, value=cmd)
        for cmd in SUBCOMMANDS if current.lower() in cmd.lower()
    ][:25]





# --- Subcommand autocomplete helpers ---
async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    session.close()
    return [
        discord.app_commands.Choice(name=char.character, value=char.character)
        for char in chars if current.lower() in char.character.lower()
    ][:25]

async def counter_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    counters = []
    for char in chars:
        for counter in char.counters:
            if current.lower() in counter.counter.lower():
                counters.append(counter.counter)
    session.close()
    unique_counters = list(dict.fromkeys(counters))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

def remove_character(user_id: str, character_name: str):
    # character_name is already sanitized from autocomplete, only validate length
    if character_name is None or not validate_length("character", character_name, MAX_FIELD_LENGTH):
        return False, "Invalid character name.", None
    session = SessionLocal()
    char = session.query(UserCharacter).filter_by(user=user_id, character=character_name).first()
    if not char:
        session.close()
        return False, "Character not found.", None
    # Gather details before deletion
    counters = session.query(Counter).filter_by(character_id=char.id).all()
    details = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
    session.delete(char)
    session.commit()
    session.close()
    return True, None, details

def remove_counter(character_id: int, counter_name: str):
    # counter_name is already sanitized from autocomplete, only validate length
    if counter_name is None or not validate_length("counter", counter_name, MAX_FIELD_LENGTH):
        return False, "Invalid counter name.", None
    session = SessionLocal()
    counter_obj = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter_obj:
        session.close()
        return False, "Counter not found.", None
    # Gather character state before deletion
    counters = session.query(Counter).filter_by(character_id=character_id).all()
    details = "\n".join([f"{c.counter} [{c.category}]: {c.temp}/{c.perm}" for c in counters])
    session.delete(counter_obj)
    session.commit()
    session.close()
    return True, None, details

def set_counter_category(character_id: int, counter_name: str, category: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    counter = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter:
        session.close()
        return False, "Counter not found."
    if category not in CategoryEnum.__members__:
        category = CategoryEnum.general.value
    counter.category = category
    session.commit()
    session.close()
    return True, None

def set_counter_comment(character_id: int, counter_name: str, comment: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        comment = sanitize_and_validate("comment", comment, MAX_COMMENT_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    counter = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter:
        session.close()
        return False, "Counter not found."
    counter.comment = comment
    session.commit()
    session.close()
    return True, None

def fully_unescape(s: str) -> str:
    # Handles both named and numeric character references
    import re
    s = html.unescape(s)
    # Replace numeric character references (e.g., &#x27; or &#39;)
    def numeric_entity_replacer(match):
        ent = match.group(1)
        if ent.startswith('x') or ent.startswith('X'):
            return chr(int(ent[1:], 16))
        else:
            return chr(int(ent))
    return re.sub(r'&#(x[0-9A-Fa-f]+|\d+);', numeric_entity_replacer, s)

def rename_character(user_id: str, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    if not validate_length("character", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."
    try:
        new_name = sanitize_and_validate("character", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    # Check if new_name already exists for this user (after length validation)
    existing = session.query(UserCharacter).filter_by(user=user_id, character=new_name).first()
    if existing:
        session.close()
        return False, "A character with that name already exists for you."
    char = session.query(UserCharacter).filter_by(user=user_id, character=old_name).first()
    if not char:
        session.close()
        return False, "Character to rename not found."
    char.character = new_name
    session.commit()
    session.close()
    return True, None

def rename_counter(character_id: int, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    if not validate_length("counter", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."
    try:
        new_name = sanitize_and_validate("counter", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    # Check if new_name already exists for this character (after length validation)
    existing = session.query(Counter).filter_by(character_id=character_id, counter=new_name).first()
    if existing:
        session.close()
        return False, "A counter with that name already exists for this character."
    counter_obj = session.query(Counter).filter_by(character_id=character_id, counter=old_name).first()
    if not counter_obj:
        session.close()
        return False, "Counter to rename not found."
    counter_obj.counter = new_name
    session.commit()
    session.close()
    return True, None

