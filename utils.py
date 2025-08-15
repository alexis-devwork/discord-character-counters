import discord
from discord.ext import commands
import html
import re
from config import (
    MAX_USER_CHARACTERS,
    MAX_COUNTERS_PER_CHARACTER,
    MAX_FIELD_LENGTH,
    MAX_COMMENT_LENGTH,
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

client = MongoClient("mongodb+srv://theirony:K6vS6W5ZJrRr8cOR@avdiscord.3saqe9v.mongodb.net/?retryWrites=true&w=majority&appName=avdiscord")
db = client["avct_db"]
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
    try:
        character = sanitize_and_validate("character", character, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    # Always sanitize before lookup
    character = sanitize_string(character)
    if characters_collection.find_one({"user": user_id, "character": character}):
        return False, "A character with that name already exists for you."
    # Check character limit
    count = characters_collection.count_documents({"user": user_id})
    if count >= MAX_USER_CHARACTERS:
        return False, f"You have reached the maximum number of characters ({MAX_USER_CHARACTERS})."
    new_entry = {
        "user": user_id,
        "character": character,
        "counters": [],
        "health": [],
    }
    characters_collection.insert_one(new_entry)
    return True, None

def get_all_user_characters_for_user(user_id: str):
    chars = list(characters_collection.find({"user": user_id}))
    # Ensure character names are sanitized for consistency
    return [UserCharacter(c["user"], sanitize_string(c["character"]), c.get("counters", []), c.get("health", []), id=str(c["_id"])) for c in chars]

def add_counter(character_id: str, counter_name: str, temp: int, perm: int, category: str = CategoryEnum.general.value, comment: str = None):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
        if comment is not None:
            comment = sanitize_and_validate("comment", comment, MAX_COMMENT_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    # Convert character_id to ObjectId for MongoDB lookup
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    if any(c["counter"] == counter_name for c in counters):
        return False, "A counter with that name exists for this character."
    if len(counters) >= MAX_COUNTERS_PER_CHARACTER:
        return False, f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER})."
    new_counter = Counter(counter_name, temp, perm, category, comment).__dict__
    counters.append(new_counter)
    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
    return True, None

def update_counter(character_id: str, counter_name: str, field: str, delta: int):
    # Convert character_id to ObjectId for MongoDB lookup
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    for c in counters:
        if c["counter"] == counter_name:
            if field == "temp":
                new_value = c["temp"] + delta
                if c["counter_type"] in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                    if new_value > c["perm"]:
                        c["temp"] = c["perm"]
                    elif new_value < 0:
                        return False, "Cannot decrement temp below zero."
                    else:
                        c["temp"] = new_value
                else:
                    if new_value < 0:
                        return False, "Cannot decrement temp below zero."
                    c["temp"] = new_value
            elif field == "perm":
                new_value = c["perm"] + delta
                if new_value < 0:
                    return False, "Cannot decrement perm below zero."
                c["perm"] = new_value
                if c["counter_type"] in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                    if c["temp"] > c["perm"]:
                        c["temp"] = c["perm"]
            else:
                return False, "Invalid field."
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
            return True, None
    return False, "Counter not found."

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
    counters = char_doc.get("counters", [])
    details = "\n".join([f"{c['counter']}: {c['temp']}/{c['perm']}" for c in counters])
    characters_collection.delete_one({"_id": char_doc["_id"]})
    return True, None, details

def remove_counter(character_id: str, counter_name: str):
    if counter_name is None or not validate_length("counter", counter_name, MAX_FIELD_LENGTH):
        return False, "Invalid counter name.", None
    # Convert character_id to ObjectId for MongoDB lookup
    from bson import ObjectId
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found.", None
    counters = char_doc.get("counters", [])
    counters = [c for c in counters if c["counter"] != counter_name]
    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
    details = "\n".join([f"{c['counter']} [{c['category']}]: {c['temp']}/{c['perm']}" for c in counters])
    return True, None, details

def set_counter_category(character_id: str, counter_name: str, category: str):
    try:
        counter_name = sanitize_and_validate("counter", counter_name, MAX_FIELD_LENGTH)
        category = sanitize_and_validate("category", category, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    # Convert character_id to ObjectId for MongoDB lookup
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found."
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
    if not validate_length("character", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."
    try:
        new_name = sanitize_and_validate("character", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    old_name = sanitize_string(old_name)
    new_name = sanitize_string(new_name)
    char_doc = characters_collection.find_one({"user": user_id, "character": old_name})
    if not char_doc:
        return False, "Character to rename not found."
    if characters_collection.find_one({"user": user_id, "character": new_name}):
        return False, "A character with that name already exists for you."
    characters_collection.update_one({"_id": char_doc["_id"]}, {"$set": {"character": new_name}})
    return True, None

def rename_counter(character_id: str, old_name: str, new_name: str):
    if not validate_length("counter", old_name, MAX_FIELD_LENGTH):
        return False, f"Old name must be at most {MAX_FIELD_LENGTH} characters."
    try:
        new_name = sanitize_and_validate("counter", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    char_doc = characters_collection.find_one({"_id": character_id})
    if not char_doc:
        return False, "Character not found."
    counters = char_doc.get("counters", [])
    if any(c["counter"] == new_name for c in counters):
        return False, "A counter with that name already exists for this character."
    for c in counters:
        if c["counter"] == old_name:
            c["counter"] = new_name
            characters_collection.update_one({"_id": character_id}, {"$set": {"counters": counters}})
            return True, None
    return False, "Counter to rename not found."

def add_predefined_counter(character_id: str, counter_type: str, perm: int, comment: str = None, override_name: str = None):
    # Convert character_id to ObjectId for MongoDB lookup
    char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
    if not char_doc:
        return False, "Character not found."
    try:
        enum_type = PredefinedCounterEnum(counter_type)
    except ValueError:
        return False, "Invalid predefined counter type."
    name = sanitize_string(override_name if override_name else enum_type.value)
    counters = char_doc.get("counters", [])
    if any(sanitize_string(c["counter"]) == name for c in counters):
        return False, "A counter with that name exists for this character."
    if len(counters) >= MAX_COUNTERS_PER_CHARACTER:
        return False, f"This character has reached the maximum number of counters ({MAX_COUNTERS_PER_CHARACTER})."
    counter_obj = CounterFactory.create(enum_type, perm, comment, override_name).__dict__
    counter_obj["counter"] = name  # Ensure counter name is sanitized
    counters.append(counter_obj)
    characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters}})
    return True, None

def generate_counters_output(counters, fully_unescape_func):
    from collections import defaultdict
    grouped = defaultdict(list)
    for c in counters:
        grouped[c.category].append(c)
    msg_lines = []
    category_order = [c.value for c in CategoryEnum]
    shown = set()
    for cat in category_order:
        if cat in grouped:
            cat_title = f"**{cat.capitalize()}**"
            msg_lines.append(cat_title)
            for c in sorted(grouped[cat], key=lambda x: x.counter.lower()):
                line = c.generate_display(fully_unescape_func)
                msg_lines.append(line)
                if c.comment:
                    msg_lines.append(f"-# {fully_unescape_func(c.comment)}")
            shown.add(cat)
    for cat in grouped.keys():
        if cat not in shown:
            cat_title = f"**{cat.capitalize()}**"
            msg_lines.append(cat_title)
            for c in sorted(grouped[cat], key=lambda x: x.counter.lower()):
                line = c.generate_display(fully_unescape_func)
                msg_lines.append(line)
                if c.comment:
                    msg_lines.append(f"-# {fully_unescape_func(c.comment)}")
    return "\n".join(msg_lines).strip()
