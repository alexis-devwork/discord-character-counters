import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum
import html
import re

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MAX_USER_CHARACTERS = int(os.getenv("MAX_USER_CHARACTERS", "10"))  # Default to 10 if not set
MAX_COUNTERS_PER_CHARACTER = int(os.getenv("MAX_COUNTERS_PER_CHARACTER", "20"))  # Default to 20 if not set

intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True

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

MAX_FIELD_LENGTH = 30
MAX_COMMENT_LENGTH = 30

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

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot(command_prefix="/avct", intents=intents)
tree = bot.tree

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

# --- AVCT group with subcommands ---
avct_group = discord.app_commands.Group(name="avct", description="AVCT commands")

@avct_group.command(name="addcharacter", description="Add a character")
async def addcharacter(interaction: discord.Interaction, character: str):
    character = sanitize_string(character)
    user_id = str(interaction.user.id)
    success, error = add_user_character(user_id, character)
    if success:
        await interaction.response.send_message(f"Character '{character}' added for you.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@avct_group.command(name="listcharacters", description="List your characters")
async def listcharacters(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await interaction.response.send_message("No characters found.", ephemeral=True)
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

@avct_group.command(name="addcounter", description="Add a counter to a character")
@discord.app_commands.autocomplete(character=character_name_autocomplete, category=category_autocomplete)
async def addcounter(
    interaction: discord.Interaction,
    character: str,
    counter: str,
    temp: int,
    perm: int,
    category: str,  # Now required
    comment: str = None
):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    category = sanitize_string(category)
    comment = sanitize_string(comment)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    # Validate category
    if category not in [c.value for c in CategoryEnum]:
        await interaction.response.send_message("Invalid category selected.", ephemeral=True)
        return
    success, error = add_counter(character_id, counter, temp, perm, category, comment)
    if success:
        await interaction.response.send_message(
            f"Counter '{counter}' (category: {category}) added to character '{character}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)

@avct_group.command(name="temp", description="Change temp value for a counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def temp(interaction: discord.Interaction, character: str, counter: str, delta: int):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success, error = update_counter(character_id, counter, "temp", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await interaction.response.send_message(
            f"Temp for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

@avct_group.command(name="perm", description="Change perm value for a counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def perm(interaction: discord.Interaction, character: str, counter: str, delta: int):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success, error = update_counter(character_id, counter, "perm", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await interaction.response.send_message(
            f"Perm for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

@avct_group.command(name="hellobyname", description="Greet the user by display name and username")
async def hellobyname(interaction: discord.Interaction):
    display_name = interaction.user.display_name
    username = interaction.user.name
    await interaction.response.send_message(f"Hello, {display_name} (username: {username})! 👋", ephemeral=True)

# Remove the incorrect usage of @avct_group.command with a class (CharacterGroup).
# Instead, add the "counters" command directly under the "character" subcommand group

character_group = discord.app_commands.Group(name="character", description="Character related commands")

@character_group.command(name="counters", description="List counters for a character")
@discord.app_commands.autocomplete(character=character_name_autocomplete)
async def counters(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message(
            "Character not found for this user. Please select a character from the dropdown/autocomplete.",
            ephemeral=True
        )
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await interaction.response.send_message("No counters found for this character.", ephemeral=True)
        return

    # Group counters by category
    from collections import defaultdict
    grouped = defaultdict(list)
    for c in counters:
        grouped[c.category].append(c)

    msg_lines = []
    for cat in sorted(grouped.keys(), key=lambda x: x.lower()):
        cat_title = f"**{cat.capitalize()}**"
        msg_lines.append(cat_title)
        for c in grouped[cat]:
            line = f"{c.counter}: {c.temp}/{c.perm}"
            msg_lines.append(line)
            if c.comment:
                msg_lines.append(f"-# {c.comment}")

    msg = "\n".join(msg_lines).strip()
    await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

# Register the character group as a subcommand of avct_group
avct_group.add_command(character_group)

tree.add_command(avct_group)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# --- Prefix/Text commands for compatibility ---
@bot.command(name="avctaddcharacter")
async def addcharacter_text(ctx, character: str):
    user_id = str(ctx.author.id)
    success, error = add_user_character(user_id, character)
    if success:
        await ctx.send(f"Character '{character}' added for you.")
    else:
        await ctx.send(error)

@bot.command(name="avctlistcharacters")
async def listcharacters_text(ctx):
    user_id = str(ctx.author.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await ctx.send("No characters found.")
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await ctx.send(f"Characters for you:\n{msg}")

@bot.command(name="avctaddcounter")
async def addcounter_text(ctx, character: str, counter: str, temp: int, perm: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = add_counter(character_id, counter, temp, perm)
    if success:
        await ctx.send(f"Counter '{counter}' added to character '{character}'.")
    else:
        await ctx.send(error or "Failed to add counter.")

@bot.command(name="avcttemp")
async def temp_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = update_counter(character_id, counter, "temp", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await ctx.send(
            f"Temp for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}")
    else:
        await ctx.send(error or "Counter or character not found.")

@bot.command(name="avctperm")
async def perm_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = update_counter(character_id, counter, "perm", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await ctx.send(
            f"Perm for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}")
    else:
        await ctx.send(error or "Counter or character not found.")

@bot.command(name="avctlistcounters")
async def listcounters_text(ctx, character: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await ctx.send("No counters found for this character.")
        return
    msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
    await ctx.send(f"Counters for character '{character}':\n{msg}")

@bot.command(name="avcthellobyname")
async def hellobyname_text(ctx):
    display_name = ctx.author.display_name
    username = ctx.author.name
    await ctx.send(f"Hello, {display_name} (username: {username})! 👋")

@bot.command(name="avctcharacter")
async def character_text(ctx, character: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await ctx.send("No counters found for this character.")
        return
    msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
    await ctx.send(f"Counters for character '{character}':\n{msg}")

def rename_character(user_id: str, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    try:
        if not validate_length("character", old_name, MAX_FIELD_LENGTH):
            raise ValueError(f"Character must be at most {MAX_FIELD_LENGTH} characters.")
        new_name = sanitize_and_validate("character", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
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

@avct_group.command(name="renamecharacter", description="Rename a character (only if new name does not exist for you)")
@discord.app_commands.autocomplete(old_name=character_name_autocomplete)
async def renamecharacter(interaction: discord.Interaction, old_name: str, new_name: str):
    new_name = sanitize_string(new_name)
    user_id = str(interaction.user.id)
    success, error = rename_character(user_id, old_name, new_name)
    if success:
        await interaction.response.send_message(f"Character '{old_name}' renamed to '{new_name}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@bot.command(name="avctrenamecharacter")
async def renamecharacter_text(ctx, old_name: str, new_name: str):
    user_id = str(ctx.author.id)
    success, error = rename_character(user_id, old_name, new_name)
    if success:
        await ctx.send(f"Character '{old_name}' renamed to '{new_name}'.")
    else:
        await ctx.send(error)

def rename_counter(character_id: int, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    try:
        if not validate_length("counter", old_name, MAX_FIELD_LENGTH):
            raise ValueError(f"Counter must be at most {MAX_FIELD_LENGTH} characters.")
        new_name = sanitize_and_validate("counter", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
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

@avct_group.command(name="renamecounter", description="Rename a counter (only if new name does not exist for this character)")
@discord.app_commands.autocomplete(character=character_name_autocomplete, old_name=counter_name_autocomplete)
async def renamecounter(interaction: discord.Interaction, character: str, old_name: str, new_name: str):
    new_name = sanitize_string(new_name)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success, error = rename_counter(character_id, old_name, new_name)
    if success:
        await interaction.response.send_message(f"Counter '{old_name}' renamed to '{new_name}' for character '{character}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@bot.command(name="avctrenamecounter")
async def renamecounter_text(ctx, character: str, old_name: str, new_name: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = rename_counter(character_id, old_name, new_name)
    if success:
        await ctx.send(f"Counter '{old_name}' renamed to '{new_name}' for character '{character}'.")
    else:
        await ctx.send(error)

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

@avct_group.command(name="removecharacter", description="Remove a character and show its details to everyone")
@discord.app_commands.autocomplete(character=character_name_autocomplete)
async def removecharacter(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    success, error, details = remove_character(user_id, character)
    if success:
        msg = f"Character '{character}' was removed.\nDetails before removal:\n{details if details else 'No counters.'}"
        await interaction.response.send_message(msg, ephemeral=False)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@bot.command(name="avctremovecharacter")
async def removecharacter_text(ctx, character: str):
    user_id = str(ctx.author.id)
    success, error, details = remove_character(user_id, character)
    if success:
        msg = f"Character '{character}' was removed.\nDetails before removal:\n{details if details else 'No counters.'}"
        await ctx.send(msg)
    else:
        await ctx.send(error)

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

@avct_group.command(name="removecounter", description="Remove a counter and show character state to everyone")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def removecounter(interaction: discord.Interaction, character: str, counter: str):
    character = sanitize_string(character)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success, error, details = remove_counter(character_id, counter)
    if success:
        msg = (
            f"Counter '{counter}' was removed from character '{character}'.\n"
            f"Character state before removal:\n{details if details else 'No counters.'}"
        )
        await interaction.response.send_message(msg, ephemeral=False)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@bot.command(name="avctremovecounter")
async def removecounter_text(ctx, character: str, counter: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error, details = remove_counter(character_id, counter)
    if success:
        msg = (
            f"Counter '{counter}' was removed from character '{character}'.\n"
            f"Character state before removal:\n{details if details else 'No counters.'}"
        )
        await ctx.send(msg)
    else:
        await ctx.send(error)

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

@avct_group.command(name="setcountercategory", description="Set the category for an existing counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete, category=category_autocomplete)
async def setcountercategory(
    interaction: discord.Interaction,
    character: str,
    counter: str,
    category: str  # Now required
):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    category = sanitize_string(category)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    if category not in [c.value for c in CategoryEnum]:
        await interaction.response.send_message("Invalid category selected.", ephemeral=True)
        return
    success, error = set_counter_category(character_id, counter, category)
    if success:
        await interaction.response.send_message(
            f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

@bot.command(name="avctsetcountercategory")
async def setcountercategory_text(ctx, character: str, counter: str, category: str = CategoryEnum.general.value):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = set_counter_category(character_id, counter, category)
    if success:
        await ctx.send(f"Category for counter '{counter}' on character '{character}' set to '{category}'.")
    else:
        await ctx.send(error or "Failed to set category.")

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

@avct_group.command(name="setcountercomment", description="Set the comment for an existing counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def setcountercomment(
    interaction: discord.Interaction,
    character: str,
    counter: str,
    comment: str
):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    comment = sanitize_string(comment)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success, error = set_counter_comment(character_id, counter, comment)
    if success:
        await interaction.response.send_message(
            f"Comment for counter '{counter}' on character '{character}' set to '{comment}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

@bot.command(name="avctsetcountercomment")
async def setcountercomment_text(ctx, character: str, counter: str, comment: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = set_counter_comment(character_id, counter, comment)
    if success:
        await ctx.send(f"Comment for counter '{counter}' on character '{character}' set to '{comment}'.")
    else:
        await ctx.send(error or "Failed to set comment.")

bot.run(TOKEN)
