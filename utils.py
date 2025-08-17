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
    DISPLAY_MODE,  # <-- Ensure DISPLAY_MODE is imported
)
from pymongo import MongoClient
from counter import (
    PredefinedCounterEnum,
    CategoryEnum,
    Counter,
    CounterFactory,
    UserCharacter,
    CounterTypeEnum,
)
from bson import ObjectId
from utils_helpers import (
    _character_exists,
    _find_character_doc_by_user_and_name,
    _get_character_by_id,
    _character_at_counter_limit,
    _user_at_character_limit,
    _create_character_entry,
)
from health import HealthLevelEnum  # Add this import

# Load environment variables
load_dotenv()


def get_bot_token():
    """
    Get the Discord bot token from environment variables.
    """
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in your .env file.")
    return token


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


def sanitize_and_validate_fields(field_map: dict) -> dict:
    """
    Sanitize and validate multiple fields at once.
    field_map: dict of field_name -> (value, max_len)
    Returns dict of field_name -> sanitized value.
    Raises ValueError if any field fails validation.
    """
    result = {}
    for field, (value, max_len) in field_map.items():
        result[field] = sanitize_and_validate(field, value, max_len)
    return result


def sanitize_string(s: str) -> str:
    if s is None:
        return None
    s = s.strip()
    s = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)
    s = html.escape(s)
    return s


def sanitize_for_lookup(character: str) -> str:
    """
    Sanitize and escape a character name for lookup (used for autocomplete input).
    This ensures that if the user selects an unescaped name from autocomplete,
    it is properly escaped for DB lookup, avoiding double escaping.
    """
    if character is None:
        return None
    character = character.strip()
    character = html.escape(character)
    return character


class CharacterRepository:
    @staticmethod
    def find_one(query):
        return characters_collection.find_one(query)

    @staticmethod
    def find(query):
        return list(characters_collection.find(query))

    @staticmethod
    def insert_one(doc):
        return characters_collection.insert_one(doc)

    @staticmethod
    def update_one(query, update):
        return characters_collection.update_one(query, update)

    @staticmethod
    def delete_one(query):
        return characters_collection.delete_one(query)

    @staticmethod
    def count_documents(query):
        return characters_collection.count_documents(query)


def add_user_character(user_id: str, character: str):
    # Prevent empty or whitespace-only character names
    if character is None or character.strip() == "":
        return False, "Character name cannot be empty or whitespace only."
    # Allow alphanumeric, spaces, and underscores
    if not re.fullmatch(r"[A-Za-z0-9_ ]+", character.strip()):
        return (
            False,
            "Character name must only contain alphanumeric characters, spaces, and underscores.",
        )
    # Check raw length before sanitization
    if len(character.strip()) > MAX_FIELD_LENGTH:
        return False, f"Character name must be at most {MAX_FIELD_LENGTH} characters."
    try:
        character = sanitize_and_validate(
            "character", character.strip(), MAX_FIELD_LENGTH
        )
    except ValueError as ve:
        return False, str(ve)

    # Check if character already exists (case-sensitive, sanitized)
    if _character_exists(user_id, character):
        return False, "A character with that name already exists for you."

    # Check character limit
    if _user_at_character_limit(user_id):
        # Use the dynamically patched value for error message
        import utils

        max_chars = getattr(utils, "MAX_USER_CHARACTERS", MAX_USER_CHARACTERS)
        return (
            False,
            f"You have reached the maximum number of characters ({max_chars}).",
        )

    # Create and insert the new character
    new_entry = _create_character_entry(user_id, character)
    CharacterRepository.insert_one(new_entry)
    return True, None


def get_character_id_by_user_and_name(user_id: str, character: str):
    """
    Return the character ID for a given user and character name.
    Returns None if not found.
    """
    doc = _find_character_doc_by_user_and_name(user_id, character)
    if doc:
        return str(doc["_id"])
    return None


def get_counters_for_character(character_id: str):
    """
    Return a list of Counter objects for the given character ID.
    """
    char_doc = _get_character_by_id(character_id)
    counters = char_doc.get("counters", []) if char_doc else []
    return [CounterFactory.from_dict(c) for c in counters]


def add_counter(
    character_id: str,
    counter_name: str,
    value: int,
    *,
    category: str = CategoryEnum.general.value,
    comment: str = None,
    counter_type: str = CounterTypeEnum.single_number.value,
    force_unpretty: bool = False,
    is_resettable: bool = None,
    is_exhaustible: bool = None,
):
    # Prevent empty or whitespace-only counter names
    if counter_name is None or str(counter_name).strip() == "":
        return False, "Counter name cannot be empty or whitespace only."
    # Allow alphanumeric, spaces, and underscores
    if not re.fullmatch(r"[A-Za-z0-9_ ]+", str(counter_name).strip()):
        return (
            False,
            "Counter name must only contain alphanumeric characters, spaces, and underscores.",
        )
    # Prevent negative values
    if value is not None and value < 0:
        return False, "Value cannot be below zero."
    # Validate counter_type
    valid_types = {ct.value for ct in CounterTypeEnum}
    if counter_type not in valid_types:
        return False, "Invalid counter type."
    # Validate inputs
    try:
        sanitized = sanitize_and_validate_fields(
            {
                "counter": (str(counter_name).strip(), MAX_FIELD_LENGTH),
                "category": (category, MAX_FIELD_LENGTH),
                "comment": (comment, MAX_COMMENT_LENGTH)
                if comment is not None
                else ("", MAX_COMMENT_LENGTH),
            }
        )
        counter_name_sanitized, category_sanitized, comment_sanitized = (
            sanitized["counter"],
            sanitized["category"],
            sanitized["comment"],
        )
    except ValueError as ve:
        return False, str(ve)

    # --- Robust character lookup: match by both escaped and unescaped name ---
    char_doc = None
    try:
        char_doc = _get_character_by_id(character_id)
    except Exception:
        pass
    if not char_doc:
        character_raw = str(character_id).strip()
        character_escaped = html.escape(character_raw)
        char_doc = CharacterRepository.find_one({"character": character_escaped})
        if not char_doc:
            char_doc = CharacterRepository.find_one({"character": character_raw})
        if not char_doc:
            return False, "Character not found."

    counters = char_doc.get("counters", [])

    # Check counter limit at the top
    if _character_at_counter_limit(counters):
        import utils

        max_counters = getattr(
            utils, "MAX_COUNTERS_PER_CHARACTER", MAX_COUNTERS_PER_CHARACTER
        )
        return (
            False,
            f"This character has reached the maximum number of counters ({max_counters}).",
        )

    sanitized_name = sanitize_string(counter_name_sanitized)
    if any(
        sanitize_string(c["counter"]).lower() == sanitized_name.lower()
        for c in counters
    ):
        return False, "A counter with that name exists for this character."

    # Set temp/perm/bedlam according to type and value
    temp, perm, bedlam = None, None, None
    if counter_type == CounterTypeEnum.single_number.value:
        temp = value
        perm = value
    elif counter_type == CounterTypeEnum.perm_is_maximum.value:
        temp = value
        perm = value
    elif counter_type == CounterTypeEnum.perm_is_maximum_bedlam.value:
        temp = value
        perm = value
        bedlam = 0
    elif counter_type == CounterTypeEnum.perm_not_maximum.value:
        # For rage and banality, temp and perm both set to value
        if counter_name_sanitized.lower() in ["rage", "banality"]:
            temp = value
            perm = value
        else:
            temp = 0
            perm = value
    else:
        temp = 0
        perm = value

    new_counter = Counter(
        counter_name_sanitized,
        temp,
        perm,
        category_sanitized,
        comment_sanitized,
        bedlam=bedlam if bedlam is not None else 0,
        counter_type=counter_type,
        force_unpretty=force_unpretty,
        is_resettable=is_resettable,
        is_exhaustible=is_exhaustible,
    ).__dict__
    counters.append(new_counter)
    CharacterRepository.update_one(
        {"_id": char_doc["_id"]}, {"$set": {"counters": counters}}
    )
    return True, None


def update_counter(character_id: str, counter_name: str, field: str, delta: int):
    """
    Update a counter's temp or perm value by delta.
    For single_number counters with is_exhaustible, remove if value would be 0.
    For single_number counters, always set perm to the same value as temp.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    for i, c in enumerate(counters):
        if sanitize_string(c["counter"]) == sanitize_string(counter_name):
            counter_type = c.get("counter_type", "single_number")
            is_exhaustible = c.get("is_exhaustible", False)
            # Handle single_number exhaustible removal
            if counter_type == "single_number" and is_exhaustible:
                new_value = c[field] + delta
                if new_value <= 0:
                    # Remove counter
                    counters.pop(i)
                    CharacterRepository.update_one(
                        {"_id": ObjectId(character_id)},
                        {"$set": {"counters": counters}},
                    )
                    return True, None
            # Normal update logic
            if field not in ("temp", "perm"):
                return False, "Invalid field."
            if field == "temp":
                new_temp = c["temp"] + delta
                if new_temp < 0:
                    return False, "Temp cannot be below zero."
                if counter_type == "perm_is_maximum":
                    c["temp"] = min(new_temp, c["perm"])
                elif counter_type == "single_number":
                    c["temp"] = new_temp
                    c["perm"] = (
                        new_temp  # Always set perm to match temp for single_number
                    )
                elif counter_type == "perm_is_maximum_bedlam":
                    c["temp"] = min(new_temp, c["perm"])
                else:
                    c["temp"] = new_temp
            elif field == "perm":
                new_perm = c["perm"] + delta
                if new_perm < 0:
                    return False, "Perm cannot be below zero."
                if counter_type == "perm_is_maximum":
                    c["perm"] = new_perm
                    c["temp"] = min(c["temp"], new_perm)
                elif counter_type == "single_number":
                    c["perm"] = new_perm
                    c["temp"] = (
                        new_perm  # Always set temp to match perm for single_number
                    )
                elif counter_type == "perm_is_maximum_bedlam":
                    c["perm"] = new_perm
                    c["temp"] = min(c["temp"], new_perm)
                else:
                    c["perm"] = new_perm
            CharacterRepository.update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
            )
            return True, None
    return False, "Counter not found."


def reset_if_eligible(character_id: str):
    """
    Reset all perm_is_maximum counters with is_resettable True: set temp to perm.
    Returns count of counters reset.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return 0
    counters = char_doc.get("counters", [])
    reset_count = 0
    for c in counters:
        if c.get("counter_type") == "perm_is_maximum" and c.get("is_resettable", False):
            c["temp"] = c["perm"]
            reset_count += 1
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return reset_count


def display_character_counters(character_id: str, unescape_func=None):
    """
    Return a formatted string of all counters for a character.
    """
    counters = get_counters_for_character(character_id)
    return generate_counters_output(counters, unescape_func)


def generate_counters_output(counters, unescape_func=None):
    """
    Generate a pretty formatted string for displaying counters grouped by category,
    with each category name in bold above its section, in the order defined by CategoryEnum.
    Uses DISPLAY_MODE from config.py for display_pretty.
    """
    if not counters:
        return "No counters found."
    unescape_func = unescape_func if unescape_func is not None else fully_unescape

    # Get category order from CategoryEnum definition
    category_order = [e.value for e in CategoryEnum]

    # Group counters by category
    category_map = {}
    for c in counters:
        cat = c.category if c.category else "general"
        category_map.setdefault(cat, []).append(c)

    lines = []
    # Add categories in CategoryEnum order first
    for cat in category_order:
        if cat in category_map:
            lines.append(f"**{cat.title()}**")
            for c in category_map[cat]:
                lines.append(c.generate_display(unescape_func, DISPLAY_MODE))
            lines.append("")  # Add a blank line between categories

    # Add any categories not in the CategoryEnum order
    for cat in category_map:
        if cat not in category_order:
            lines.append(f"**{cat.title()}**")
            for c in category_map[cat]:
                lines.append(c.generate_display(unescape_func, DISPLAY_MODE))
            lines.append("")

    return "\n".join(lines).strip()


def fully_unescape(s):
    """
    Unescape HTML entities in a string.
    """
    return html.unescape(s)


def rename_character(user_id: str, old_name: str, new_name: str):
    """
    Rename a character for a user.
    Matches both escaped and unescaped forms for old_name.
    Disallows non-alphanumeric characters except spaces in new_name.
    """
    if old_name is None or new_name is None:
        return False, "Character name cannot be empty or whitespace only."
    # Disallow any non-alphanumeric characters except spaces in new_name
    if not re.fullmatch(r"[A-Za-z0-9_ ]+", new_name.strip()):
        return (
            False,
            "Character name must only contain alphanumeric characters, spaces, and underscores.",
        )
    old_name_raw = old_name.strip()
    old_name_escaped = html.escape(old_name_raw)
    new_name_sanitized = sanitize_string(new_name.strip())

    # Validate new name
    if new_name.strip() == "":
        return False, "Character name cannot be empty or whitespace only."
    if len(new_name.strip()) > MAX_FIELD_LENGTH:
        return False, f"Character name must be at most {MAX_FIELD_LENGTH} characters."
    if len(new_name_sanitized) > MAX_FIELD_LENGTH:
        return False, f"Character name must be at most {MAX_FIELD_LENGTH} characters."

    # Check uniqueness for sanitized new name
    if _character_exists(user_id, new_name_sanitized):
        return False, "A character with that name already exists for you."

    # Try both escaped and raw for lookup
    char_doc = CharacterRepository.find_one(
        {"user": user_id, "character": old_name_escaped}
    )
    if not char_doc:
        char_doc = CharacterRepository.find_one(
            {"user": user_id, "character": old_name_raw}
        )
    if not char_doc:
        return False, "Character to rename not found."
    CharacterRepository.update_one(
        {"_id": char_doc["_id"]}, {"$set": {"character": new_name_sanitized}}
    )
    return True, None


def rename_counter(character_id: str, old_name: str, new_name: str):
    """
    Rename a counter for a character.
    Prevents renaming to a name that already exists (case-insensitive, sanitized).
    Disallows non-alphanumeric characters except spaces in new_name.
    """
    # Disallow any non-alphanumeric characters except spaces in new_name
    if new_name is None or new_name.strip() == "":
        return False, "Counter name cannot be empty or whitespace only."
    if not re.fullmatch(r"[A-Za-z0-9_ ]+", new_name.strip()):
        return (
            False,
            "Counter name must only contain alphanumeric characters, spaces, and underscores.",
        )
    char_doc = _get_character_by_id(character_id)
    counters = char_doc.get("counters", []) if char_doc else []
    old_name_sanitized = sanitize_string(old_name.strip())
    new_name_sanitized = sanitize_string(new_name.strip())

    # Validate new name
    if new_name.strip() == "":
        return False, "Counter name cannot be empty or whitespace only."
    if len(new_name.strip()) > MAX_FIELD_LENGTH:
        return False, f"Counter name must be at most {MAX_FIELD_LENGTH} characters."
    if len(new_name_sanitized) > MAX_FIELD_LENGTH:
        return False, f"Counter name must be at most {MAX_FIELD_LENGTH} characters."

    # Check uniqueness (case-insensitive, sanitized)
    if any(
        sanitize_string(c["counter"]).lower() == new_name_sanitized.lower()
        for c in counters
        if sanitize_string(c["counter"]).lower() != old_name_sanitized.lower()
    ):
        return False, "A counter with that name already exists for this character."

    for c in counters:
        if sanitize_string(c["counter"]) == old_name_sanitized:
            c["counter"] = new_name_sanitized
            CharacterRepository.update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
            )
            return True, None
    return False, "Counter to rename not found."


def add_health(character_id: str, level: int, damage: int):
    """
    Add a health entry to a character.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    health_list = char_doc.get("health", [])
    # Check for duplicate health level
    if any(h.get("level") == level for h in health_list):
        return False, "Health entry already exists."
    # Check for health limit
    from health import HEALTH_LEVELS

    if len(health_list) >= len(HEALTH_LEVELS):
        return False, "Reached maximum health level."
    health_list.append({"level": level, "damage": damage})
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
    )
    return True, None


def delete_health(character_id: str, level: int):
    """
    Delete a health entry from a character.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    health_list = char_doc.get("health", [])
    new_health_list = [h for h in health_list if h.get("level") != level]
    if len(new_health_list) == len(health_list):
        return False, "Health entry not found."
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"health": new_health_list}}
    )
    return True, None


def delete_user_character(character_id: str):
    """
    Delete a character by its ID.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    CharacterRepository.delete_one({"_id": ObjectId(character_id)})
    return True, None


def get_user_character_by_id(character_id: str):
    """
    Get a UserCharacter object by character ID.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return None
    return UserCharacter.from_dict(char_doc)


def get_user_character_health(character_id: str):
    """
    Get the health list for a character by ID.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return []
    return char_doc.get("health", [])


def get_all_user_characters_for_user(user_id: str):
    """
    Return a list of UserCharacter objects for a given user.
    """
    docs = CharacterRepository.find({"user": user_id})
    return [UserCharacter.from_dict(d) for d in docs]


# Shared async error handlers for commands
async def handle_character_not_found(interaction):
    await interaction.response.send_message(
        "Character not found for this user.", ephemeral=True
    )
    return False


async def handle_counter_not_found(interaction):
    await interaction.response.send_message("Counter not found.", ephemeral=True)
    return False


async def handle_invalid_health_type(interaction):
    await interaction.response.send_message("Invalid health type.", ephemeral=True)
    return False


async def handle_invalid_damage_type(interaction):
    await interaction.response.send_message(
        "Invalid health or damage type.", ephemeral=True
    )
    return False


async def handle_health_tracker_not_found(interaction):
    await interaction.response.send_message(
        "Health tracker not found for this character and type.", ephemeral=True
    )
    return False


def add_predefined_counter(
    character_id: str,
    counter_type: str,
    value: int = None,
    comment: str = None,
    name_override: str = None,
    force_unpretty: bool = False,
    is_resettable: bool = None,
    is_exhaustible: bool = None,
):
    """
    Add a predefined counter to a character.
    counter_type: PredefinedCounterEnum value (string)
    value: initial value for temp and perm (if applicable)
    comment: optional comment
    name_override: optional override for counter name
    """
    # Accept both enum values and strings for counter_type
    if isinstance(counter_type, PredefinedCounterEnum):
        counter_enum = counter_type
    else:
        try:
            counter_enum = PredefinedCounterEnum(counter_type)
        except ValueError:
            return False, "Invalid predefined counter type."

    perm = value if value is not None else 0

    # Use CounterFactory for correct type and structure
    try:
        counter_obj = CounterFactory.create(counter_enum, perm, comment, name_override)
        # Patch in extra options if allowed
        if force_unpretty:
            counter_obj.force_unpretty = True
        if (
            is_resettable is not None
            and counter_obj.counter_type == CounterTypeEnum.perm_is_maximum.value
        ):
            counter_obj.is_resettable = is_resettable
        if (
            is_exhaustible is not None
            and counter_obj.counter_type == CounterTypeEnum.single_number.value
        ):
            counter_obj.is_exhaustible = is_exhaustible
    except Exception as e:
        return False, str(e)

    # Get character document
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."

    counters = char_doc.get("counters", [])

    # --- FIX: Check for duplicate counter name (case-insensitive, sanitized) ---
    # Always check against the actual name used in the counter object (counter_obj.counter)
    sanitized_new_name = sanitize_string(counter_obj.counter)
    if any(
        sanitize_string(c["counter"]).lower() == sanitized_new_name.lower()
        for c in counters
    ):
        return False, "A counter with that name exists for this character."

    # Check counter limit
    if _character_at_counter_limit(counters):
        return (
            False,
            f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER}).",
        )

    # Add the counter
    counters.append(counter_obj.__dict__)
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return True, None


def toggle_counter_option(
    character_id: str, counter_name: str, option: str, value: bool
):
    """
    Toggle force_unpretty, is_resettable, or is_exhaustible for a counter.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    found = False
    for c in counters:
        if sanitize_string(c["counter"]) == sanitize_string(counter_name):
            if option == "force_unpretty":
                c["force_unpretty"] = value
                found = True
            elif (
                option == "is_resettable"
                and c.get("counter_type") == CounterTypeEnum.perm_is_maximum.value
            ):
                c["is_resettable"] = value
                found = True
            elif (
                option == "is_exhaustible"
                and c.get("counter_type") == CounterTypeEnum.single_number.value
            ):
                c["is_exhaustible"] = value
                found = True
            break
    if not found:
        return False, "Counter not found or option not allowed for this type."
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return True, None


def update_counter_comment(character_id: str, counter_name: str, comment: str):
    """
    Update the comment for a counter.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    found = False
    for c in counters:
        if sanitize_string(c["counter"]) == sanitize_string(counter_name):
            c["comment"] = comment
            found = True
            break
    if not found:
        return False, "Counter not found."
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return True, None


def set_counter_category(character_id: str, counter_name: str, category: str):
    """
    Set the category for a counter.
    Returns (success, error).
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    found = False
    for c in counters:
        if sanitize_string(c["counter"]) == sanitize_string(counter_name):
            c["category"] = category
            found = True
            break
    if not found:
        return False, "Counter not found."
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return True, None


def update_health_in_db(character_id: str, health_type: str, damage):
    """
    Update the health tracker in the database for a given health_type.
    """
    char_doc = _get_character_by_id(character_id)
    health_list = char_doc.get("health", [])
    for h in health_list:
        if h.get("health_type") == health_type:
            h["damage"] = damage
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
    )
    return health_list


def remove_character(user_id: str, character: str):
    """
    Remove a character and all its counters for a user.
    Returns (success, error, details) where details is a string of removed counters.
    Matches both escaped and unescaped forms for character name.
    """
    char_doc = _find_character_doc_by_user_and_name(user_id, character)
    if not char_doc:
        return False, "Character not found.", None

    counters = char_doc.get("counters", [])
    details = (
        "\n".join(
            [
                c.generate_display(fully_unescape, False)
                for c in [CounterFactory.from_dict(c) for c in counters]
            ]
        )
        if counters
        else None
    )

    CharacterRepository.delete_one({"_id": char_doc["_id"]})
    return True, None, details


def update_counter_in_db(character_id, counter_name, field, value, target=None):
    """
    Update a counter's field (perm, temp, or bedlam) directly in the database.
    If target is provided, updates temp, perm, and bedlam from the target object.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return []
    counters = char_doc.get("counters", [])
    for idx, c in enumerate(counters):
        if c["counter"] == counter_name:
            if target:
                c["perm"] = target.perm
                c["temp"] = target.temp
                c["bedlam"] = (
                    target.bedlam
                )  # Ensure bedlam is updated if target is provided
            else:
                c[field] = value
            counters[idx] = c
            break
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": counters}}
    )
    return [CounterFactory.from_dict(c) for c in counters]


def add_health_level(character_id: str, health_type: str, health_level_type: str):
    """
    Add a health level to a health tracker for a character.
    Returns (success, error).
    Allows adding more health levels of a type already in the list.
    """
    # Validate health_level_type
    if health_level_type not in [e.value for e in HealthLevelEnum]:
        return False, f"Invalid health level type: {health_level_type}"

    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found."
    health_list = char_doc.get("health", [])
    for h in health_list:
        if h.get("health_type") == health_type:
            levels = h.get("health_levels", [])
            # Allow duplicates, just append
            levels.append(health_level_type)

            # Sort the health levels based on the predefined order in HealthLevelEnum
            enum_order = [e.value for e in HealthLevelEnum]
            h["health_levels"] = sorted(
                levels,
                key=lambda x: (enum_order.index(x), levels.index(x))
                if x in enum_order
                else (len(enum_order), levels.index(x)),
            )

            CharacterRepository.update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
            )
            return True, None
    return False, "Health tracker not found."


def remove_counter(character_id: str, counter_name: str):
    """
    Remove a counter from a character.
    Returns (success, error, details) where details is a string of remaining counters.
    """
    char_doc = _get_character_by_id(character_id)
    if not char_doc:
        return False, "Character not found.", None
    counters = char_doc.get("counters", [])
    new_counters = [
        c
        for c in counters
        if sanitize_string(c["counter"]) != sanitize_string(counter_name)
    ]
    if len(new_counters) == len(counters):
        return False, "Counter not found.", None
    CharacterRepository.update_one(
        {"_id": ObjectId(character_id)}, {"$set": {"counters": new_counters}}
    )
    details = (
        "\n".join(
            [
                CounterFactory.from_dict(c).generate_display(fully_unescape, False)
                for c in new_counters
            ]
        )
        if new_counters
        else None
    )
    return True, None, details
