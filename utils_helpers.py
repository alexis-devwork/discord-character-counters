import html
from bson import ObjectId


def _character_exists(user_id: str, character: str) -> bool:
    from utils import CharacterRepository, sanitize_string

    character = sanitize_string(character)
    return (
        CharacterRepository.find_one({"user": user_id, "character": character})
        is not None
    )


def _find_character_doc_by_user_and_name(user_id: str, character: str):
    from utils import CharacterRepository

    if character is None:
        return None
    character_raw = character.strip()
    character_escaped = html.escape(character_raw)
    doc = CharacterRepository.find_one(
        {"user": user_id, "character": character_escaped}
    )
    if not doc:
        doc = CharacterRepository.find_one(
            {"user": user_id, "character": character_raw}
        )
    return doc


def _get_character_by_id(character_id: str):
    from utils import CharacterRepository

    return CharacterRepository.find_one({"_id": ObjectId(character_id)})


def _counter_exists(counters: list, counter_name: str) -> bool:
    return any(c["counter"] == counter_name for c in counters)


def _character_at_counter_limit(counters: list) -> bool:
    # Dynamically get config value so patching works in tests
    import utils

    max_counters = getattr(utils, "MAX_COUNTERS_PER_CHARACTER", 10)
    return len(counters) >= max_counters


def _user_at_character_limit(user_id: str) -> bool:
    from utils import CharacterRepository
    import utils

    max_chars = getattr(utils, "MAX_USER_CHARACTERS", 10)
    count = CharacterRepository.count_documents({"user": user_id})
    return count >= max_chars


def _create_character_entry(user_id: str, character: str) -> dict:
    return {"user": user_id, "character": character, "counters": [], "health": []}
