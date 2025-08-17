import discord
from utils import (
    get_character_id_by_user_and_name,
    get_counters_for_character,
    PredefinedCounterEnum,
    get_all_user_characters_for_user,
)
from counter import CategoryEnum, CounterTypeEnum


def enum_autocomplete(enum_cls, current: str, title_case=False):
    """Generalized autocomplete for enums."""
    return [
        discord.app_commands.Choice(
            name=e.value.title() if title_case else e.value, value=e.value
        )
        for e in enum_cls
        if current.lower() in e.value.lower()
    ][:25]


def counter_name_autocomplete_helper(interaction, current, filter_func=None):
    """Generalized autocomplete for counter names for a character."""
    user_id = str(interaction.user.id)
    character = interaction.namespace.character
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        return []
    counters = get_counters_for_character(character_id)
    filtered = [
        c.counter
        for c in counters
        if (filter_func(c) if filter_func else True)
        and current.lower() in c.counter.lower()
    ]
    unique_counters = list(dict.fromkeys(filtered))
    return [
        discord.app_commands.Choice(name=name, value=name) for name in unique_counters
    ][:25]


async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    chars = get_all_user_characters_for_user(user_id)
    # Always show all characters if current is empty, otherwise filter
    if not current:
        names = [c.character for c in chars]
    else:
        names = [c.character for c in chars if current.lower() in c.character.lower()]
    unique_names = list(dict.fromkeys(names))[:25]
    return [discord.app_commands.Choice(name=name, value=name) for name in unique_names]


async def category_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=e.value.title(), value=e.value)
        for e in CategoryEnum
        if current.lower() in e.value.lower()
    ][:25]


async def predefined_counter_type_autocomplete(
    interaction: discord.Interaction, current: str
):
    # Add custom options for Remove_When_Exhausted and Reset_Eligible
    custom_types = [
        ("Remove_When_Exhausted", "Remove_When_Exhausted"),
        ("Reset_Eligible", "Reset_Eligible"),
    ]
    enum_choices = [
        discord.app_commands.Choice(name=e.value.title(), value=e.value)
        for e in PredefinedCounterEnum
        if current.lower() in e.value.lower()
    ]
    custom_choices = [
        discord.app_commands.Choice(name=name, value=value)
        for name, value in custom_types
        if current.lower() in value.lower() or current.lower() in name.lower()
    ]
    return (custom_choices + enum_choices)[:25]


async def counter_name_autocomplete_for_character(
    interaction: discord.Interaction, current: str
):
    return counter_name_autocomplete_helper(interaction, current)


async def bedlam_counter_autocomplete(interaction: discord.Interaction, current: str):
    return counter_name_autocomplete_helper(
        interaction,
        current,
        filter_func=lambda c: c.counter_type == "perm_is_maximum_bedlam",
    )


async def health_type_autocomplete(interaction: discord.Interaction, current: str):
    from health import HealthTypeEnum

    return enum_autocomplete(HealthTypeEnum, current)


async def damage_type_autocomplete(interaction: discord.Interaction, current: str):
    from health import DamageEnum

    return enum_autocomplete(DamageEnum, current)


async def counter_type_autocomplete(interaction: discord.Interaction, current: str):
    # Only show name_override input if item_with_charges or project_roll is selected
    getattr(interaction.namespace, "counter_type", None)
    # This function controls the autocomplete for counter_type, not name_override.
    # UI logic should only show the name_override field if selected_type is in allowed_types.
    return enum_autocomplete(CounterTypeEnum, current)


async def toggle_counter_autocomplete(interaction: discord.Interaction, current: str):
    # Autocomplete counters for toggling options
    user_id = str(interaction.user.id)
    character = interaction.namespace.character
    toggle = getattr(interaction.namespace, "toggle", None)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        return []
    counters = get_counters_for_character(character_id)
    # Filter by toggle type
    if toggle == "force_unpretty":
        filtered = [c.counter for c in counters if current.lower() in c.counter.lower()]
    elif toggle == "is_resettable":
        filtered = [
            c.counter
            for c in counters
            if c.counter_type == "perm_is_maximum"
            and current.lower() in c.counter.lower()
        ]
    elif toggle == "is_exhaustible":
        filtered = [
            c.counter
            for c in counters
            if c.counter_type == "single_number"
            and current.lower() in c.counter.lower()
        ]
    else:
        filtered = []
    unique_counters = list(dict.fromkeys(filtered))
    return [
        discord.app_commands.Choice(name=name, value=name) for name in unique_counters
    ][:25]
