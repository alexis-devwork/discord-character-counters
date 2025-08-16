import discord
from discord.ext import commands
import html
import re
import os
from dotenv import load_dotenv
from config import (
    MAX_USER_CHARACTERS,
    MAX_COUNTERS_PER_CHARACTER,
    MAX_FIELD_LENGTH,
    MAX_COMMENT_LENGTH,
    DISPLAY_MODE,
)
from pymongo import MongoClient
from counter import (
    PredefinedCounterEnum,
    CategoryEnum,
    Counter,
    CounterFactory,
    UserCharacter,
    SplatEnum,
)
from health import Health, HealthTypeEnum
from bson import ObjectId
from collections import defaultdict

# Load environment variables
load_dotenv()

# Get MongoDB connection details from environment variables
mongo_connection_string = os.getenv("MONGO_CONNECTION_STRING")
mongo_db_name = os.getenv("MONGO_DB_NAME")

# Connect to MongoDB
client = MongoClient(mongo_connection_string)
db = client[mongo_db_name]
characters_collection = db["characters"]

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
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    return html.escape(s)

def add_user_character(user_id: str, character: str):
    # Prevent empty or whitespace-only character names
    if character is None or character.strip() == "":
        return False, "Character name cannot be empty or whitespace only."
    try:
        character = sanitize_and_validate("character", character, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    # Check if character already exists
    if _character_exists(user_id, character):
        return False, "A character with that name already exists for you."

    # Check character limit
    if _user_at_character_limit(user_id):
        return False, f"You have reached the maximum number of characters ({MAX_USER_CHARACTERS})."

    # Create and insert the new character
    new_entry = _create_character_entry(user_id, character)
    characters_collection.insert_one(new_entry)
    return True, None

def _character_exists(user_id: str, character: str) -> bool:
    """Check if a character with the given name exists for the user."""
    character = sanitize_string(character)
    return characters_collection.find_one({"user": user_id, "character": character}) is not None

def _user_at_character_limit(user_id: str) -> bool:
    """Check if the user has reached the maximum character limit."""
    count = characters_collection.count_documents({"user": user_id})
    return count >= MAX_USER_CHARACTERS

def _create_character_entry(user_id: str, character: str) -> dict:
    """Create a new character entry dictionary."""
    return {
        "user": user_id,
        "character": character,
        "counters": [],
        "health": [],
    }

def get_all_user_characters_for_user(user_id: str):
    chars = list(characters_collection.find({"user": user_id}))
    # Ensure character names are sanitized for consistency
    return [UserCharacter(c["user"], sanitize_string(c["character"]), c.get("counters", []), c.get("health", []), id=str(c["_id"])) for c in chars]

def add_counter(character_id: str, counter_name: str, temp: int, perm: int, category: str = CategoryEnum.general.value, comment: str = None, counter_type: str = "single_number"):
    # Prevent empty or whitespace-only counter names
    if counter_name is None or counter_name.strip() == "":
        return False, "Counter name cannot be empty or whitespace only."
    # Prevent negative values
    if temp is not None and temp < 0:
        return False, "Temp value cannot be below zero."
    if perm is not None and perm < 0:
        return False, "Perm value cannot be below zero."
    # Validate counter_type
    from counter import CounterTypeEnum
    valid_types = {ct.value for ct in CounterTypeEnum}
    if counter_type not in valid_types:
        return False, "Invalid counter type."
    # Validate inputs
    try:
        counter_name, category, comment = _validate_counter_inputs(counter_name, category, comment)
    except ValueError as ve:
        return False, str(ve)

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])

    # Sanitize counter_name before checking for duplicates
    sanitized_name = sanitize_string(counter_name)
    if any(sanitize_string(c["counter"]).lower() == sanitized_name.lower() for c in counters):
        return False, "A counter with that name exists for this character."

    # Check counter limit
    if _character_at_counter_limit(counters):
        return False, f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER})."

    # Create and add the counter
    new_counter = Counter(counter_name, temp, perm, category, comment, counter_type=counter_type).__dict__
    counters.append(new_counter)
    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
    return True, None

def _validate_counter_inputs(counter_name: str, category: str, comment: str = None):
    """Validate and sanitize counter inputs."""
    counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
    category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
    if comment is not None:
        comment = sanitize_and_validate("comment", comment, MAX_COMMENT_LENGTH)
    return counter_name, category, comment

def _get_character_by_id(character_id: str):
    """Get a character document by ID."""
    return characters_collection.find_one({"_id": ObjectId(character_id)})

def _counter_exists(counters: list, counter_name: str) -> bool:
    """Check if a counter with the given name exists in the counters list."""
    return any(c["counter"] == counter_name for c in counters)

def _character_at_counter_limit(counters: list) -> bool:
    """Check if the character has reached the maximum counter limit."""
    return len(counters) >= MAX_COUNTERS_PER_CHARACTER

def update_counter(character_id: str, counter_name: str, field: str, value: int):
    # Prevent negative updates
    if value is not None and value < 0:
        return False, "Value cannot be below zero."

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            success, error = _update_counter_field(c, field, value)
            if not success:
                return False, error

            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None
    return False, "Counter not found."

def _update_counter_field(counter: dict, field: str, delta: int):
    """Update a specific field of a counter by the given delta."""
    if field == "temp":
        return _update_temp_field(counter, delta)
    elif field == "perm":
        return _update_perm_field(counter, delta)
    else:
        return False, "Invalid field."

def _update_temp_field(counter: dict, delta: int):
    """Update the temp field of a counter."""
    new_value = counter["temp"] + delta

    if counter["counter_type"] in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
        if new_value > counter["perm"]:
            counter["temp"] = counter["perm"]
        elif new_value < 0:
            return False, "Cannot decrement temp below zero."
        else:
            counter["temp"] = new_value
    else:
        if new_value < 0:
            return False, "Cannot decrement temp below zero."
        counter["temp"] = new_value

    return True, None

def _update_perm_field(counter: dict, delta: int):
    """Update the perm field of a counter."""
    new_value = counter["perm"] + delta
    if new_value < 0:
        return False, "Cannot decrement perm below zero."

    counter["perm"] = new_value

    # Adjust temp if necessary
    if counter["counter_type"] in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
        if counter["temp"] > counter["perm"]:
            counter["temp"] = counter["perm"]

    return True, None

def set_counter_comment(character_id: str, counter_name: str, comment: str):
    comment = sanitize_string(comment)
    # Convert character_id to ObjectId for MongoDB lookup
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            c["comment"] = comment
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None
    return False, "Counter not found."

def get_counters_for_character(character_id: str):
    from bson import ObjectId
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return []
    # Convert MongoDB counters to Counter objects
    from counter import Counter
    counters = []
    for c in char_doc.get("counters", []):
        counter = Counter(
            counter=c.get("counter"),
            temp=c.get("temp", 0),
            perm=c.get("perm", 0),
            counter_type=c.get("counter_type", "standard"),
            category=c.get("category", "general"),
            comment=c.get("comment", ""),
            bedlam=c.get("bedlam", 0)
        )
        counters.append(counter)
    return counters

def get_character_id_by_user_and_name(user_id: str, character_name: str):
    try:
        character_name = sanitize_and_validate("character", character_name, MAX_FIELD_LENGTH)
    except ValueError:
        return None
    character_name = sanitize_string(character_name)
    char_doc = characters_collection.find_one({"user": user_id, "character": character_name})
    return str(char_doc["_id"]) if char_doc else None

# --- Autocomplete helpers ---
async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    chars = list(characters_collection.find({"user": user_id}))
    # Always sanitize for display and matching
    return [
        discord.app_commands.Choice(name=sanitize_string(char["character"]), value=sanitize_string(char["character"]))
        for char in chars if current.lower() in sanitize_string(char["character"]).lower()
    ][:25]

async def counter_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    chars = list(characters_collection.find({"user": user_id}))
    counters = []
    for char in chars:
        for counter in char.get("counters", []):
            if current.lower() in counter["counter"].lower():
                counters.append(counter["counter"])
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

async def splat_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=s.value, value=s.value)
        for s in SplatEnum
        if current.lower() in s.value.lower()
    ][:25]

async def counter_name_autocomplete_for_character(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    character = sanitize_string(interaction.namespace.character)
    char_doc = characters_collection.find_one({"user": user_id, "character": character})
    if not char_doc:
        return []
    counters = char_doc.get("counters", [])
    filtered = [
        c["counter"] for c in counters
        if current.lower() in c["counter"].lower()
    ]
    unique_counters = list(dict.fromkeys(filtered))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

def remove_character(user_id: str, character_name: str):
    if character_name is None or not validate_length("character", character_name, MAX_FIELD_LENGTH):
        return False, "Invalid character name.", None

    character_name = sanitize_string(character_name)
    char_doc = characters_collection.find_one({"user": user_id, "character": character_name})

    if not char_doc:
        return False, "Character not found.", None

    # Get counter details before deleting
    details = _format_counter_details(char_doc.get("counters", []))

    # Delete character
    characters_collection.delete_one({"_id": char_doc["_id"]})

    return True, None, details

def _format_counter_details(counters: list) -> str:
    """Format counter details into a string."""
    return "\n".join([f"{c['counter']}: {c['temp']}/{c['perm']}" for c in counters])

def remove_counter(character_id: str, counter_name: str):
    if counter_name is None or not validate_length("counter", counter_name, MAX_FIELD_LENGTH):
        return False, "Invalid counter name.", None

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found.", None

    # Remove counter
    counters = char_doc.get("counters", [])
    counters = [c for c in counters if c["counter"] != counter_name]

    # Update character
    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})

    # Format remaining counters details
    details = _format_remaining_counters(counters)

    return True, None, details

def _format_remaining_counters(counters: list) -> str:
    """Format remaining counters into a string."""
    return "\n".join([f"{c['counter']} [{c['category']}]: {c['temp']}/{c['perm']}" for c in counters])

def set_counter_category(character_id: str, counter_name: str, category: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    # Update counter category
    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            c["category"] = category
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None

    return False, "Counter not found."

def set_counter_comment(character_id: str, counter_name: str, comment: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        comment = sanitize_and_validate("comment", comment, MAX_COMMENT_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    # Update counter comment
    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            c["comment"] = comment
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None

    return False, "Counter not found."

def update_counter_comment(character_id: str, counter_name: str, new_comment: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        new_comment = sanitize_and_validate("comment", new_comment, MAX_COMMENT_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            c["comment"] = new_comment
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None

    return False, "Counter not found."

def fully_unescape(s: str) -> str:
    import re
    s = html.unescape(s)
    def numeric_entity_replacer(match):
        ent = match.group(1)
        if ent.startswith('x') or ent.startswith('X'):
            return chr(int(ent[1:], 16))
        else:
            return chr(int(ent))
    return re.sub(r'&#(x[0-9A-Fa-f]+|\d+);', numeric_entity_replacer, s)

def rename_character(user_id: str, old_name: str, new_name: str):
    # Prevent empty or whitespace-only new name
    if new_name is None or new_name.strip() == "":
        return False, "Character name cannot be empty or whitespace only."
    if not validate_length("character", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."

    try:
        new_name = sanitize_and_validate("character", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    old_name = sanitize_string(old_name)
    new_name = sanitize_string(new_name)

    # Check if source character exists
    char_doc = characters_collection.find_one({"user": user_id, "character": old_name})
    if not char_doc:
        return False, "Character to rename not found."

    # Check if target name already exists
    if characters_collection.find_one({"user": user_id, "character": new_name}):
        return False, "A character with that name already exists for you."

    # Rename character
    characters_collection.update_one({"_id": char_doc["_id"]}, {"$set": {"character": new_name}})

    return True, None

def rename_counter(character_id: str, old_name: str, new_name: str):
    # Prevent empty or whitespace-only new name
    if new_name is None or new_name.strip() == "":
        return False, "Counter name cannot be empty or whitespace only."
    if not validate_length("counter", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."

    try:
        new_name = sanitize_and_validate("counter", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])

    # Check if target name already exists
    if any(c["counter"] == new_name for c in counters):
        return False, "A counter with that name already exists for this character."

    # Rename counter
    for c in counters:
        if c["counter"] == old_name:
            c["counter"] = new_name
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None

    return False, "Counter to rename not found."

def add_predefined_counter(character_id: str, counter_type: str, perm: int, comment: str = None, override_name: str = None):
    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    # Validate counter type
    try:
        enum_type = PredefinedCounterEnum(counter_type)
    except ValueError:
        return False, "Invalid predefined counter type."

    # Process counter name
    name = sanitize_string(override_name if override_name else enum_type.value)

    counters = char_doc.get("counters", [])

    # Check if counter already exists
    if any(sanitize_string(c["counter"]) == name for c in counters):
        return False, "A counter with that name exists for this character."

    # Check counter limit
    if len(counters) >= MAX_COUNTERS_PER_CHARACTER:
        return False, f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER})."

    # Create and add counter
    counter_obj = CounterFactory.create(enum_type, perm, comment, override_name).__dict__
    counter_obj["counter"] = name  # Ensure counter name is sanitized
    counters.append(counter_obj)

    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})

    return True, None

def generate_counters_output(counters, fully_unescape_func):
    # Group counters by category
    grouped_counters = _group_counters_by_category(counters)

    # Generate output lines
    msg_lines = []

    # Add counters in order of category enum
    shown_categories = _add_ordered_categories(grouped_counters, msg_lines, fully_unescape_func)

    # Add any remaining categories
    _add_remaining_categories(grouped_counters, shown_categories, msg_lines, fully_unescape_func)

    return "\n".join(msg_lines).strip()

def _group_counters_by_category(counters):
    """Group counters by their category."""
    grouped = defaultdict(list)
    for c in counters:
        grouped[c.category].append(c)
    return grouped

def _add_ordered_categories(grouped_counters, msg_lines, fully_unescape_func):
    """Add counters from categories in the order defined by CategoryEnum."""
    shown = set()
    category_order = [c.value for c in CategoryEnum]

    for cat in category_order:
        if cat in grouped_counters:
            # Add category header
            msg_lines.append(f"**{cat.capitalize()}**")

            # Add sorted counters
            for c in sorted(grouped_counters[cat], key=lambda x: x.counter.lower()):
                msg_lines.append(c.generate_display(fully_unescape_func, DISPLAY_MODE))
                if c.comment:
                    msg_lines.append(f"-# {fully_unescape_func(c.comment)}")

            shown.add(cat)

    return shown

def _add_remaining_categories(grouped_counters, shown_categories, msg_lines, fully_unescape_func):
    """Add counters from categories not in CategoryEnum."""
    for cat in grouped_counters.keys():
        if cat not in shown_categories:
            # Add category header
            msg_lines.append(f"**{cat.capitalize()}**")

            # Add sorted counters
            for c in sorted(grouped_counters[cat], key=lambda x: x.counter.lower()):
                msg_lines.append(c.generate_display(fully_unescape_func, DISPLAY_MODE))
                if c.comment:
                    msg_lines.append(f"-# {fully_unescape_func(c.comment)}")

def update_counter_category(character_id: str, counter_name: str, new_category: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        new_category = sanitize_and_validate("category", new_category, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)

    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            c["category"] = new_category
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None

    return False, "Counter not found."
