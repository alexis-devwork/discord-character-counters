import discord
from discord import app_commands
from utils import (
    get_character_id_by_user_and_name,
    get_counters_for_character,
    PredefinedCounterEnum,
    sanitize_string
)

async def predefined_counter_type_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=ct.value.title(), value=ct.value)
        for ct in PredefinedCounterEnum
        if current.lower() in ct.value.lower()
    ][:25]

async def counter_name_autocomplete_for_character(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    character = interaction.namespace.character
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        return []
    counters = get_counters_for_character(character_id)
    filtered = [
        c.counter for c in counters
        if current.lower() in c.counter.lower()
    ]
    unique_counters = list(dict.fromkeys(filtered))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

async def bedlam_counter_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    character = interaction.namespace.character
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        return []
    counters = get_counters_for_character(character_id)
    filtered = [
        c.counter for c in counters
        if c.counter_type == "perm_is_maximum_bedlam" and current.lower() in c.counter.lower()
    ]
    unique_counters = list(dict.fromkeys(filtered))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

async def health_type_autocomplete(interaction: discord.Interaction, current: str):
    from health import HealthTypeEnum
    return [
        discord.app_commands.Choice(name=ht.value, value=ht.value)
        for ht in HealthTypeEnum
        if current.lower() in ht.value.lower()
    ][:25]

async def damage_type_autocomplete(interaction: discord.Interaction, current: str):
    from health import DamageEnum
    return [
        discord.app_commands.Choice(name=dt.value, value=dt.value)
        for dt in DamageEnum
        if current.lower() in dt.value.lower()
    ][:25]

