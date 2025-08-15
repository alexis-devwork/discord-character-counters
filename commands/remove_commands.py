import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    remove_character,
    remove_counter
)
from utils import characters_collection
from bson import ObjectId
from health import HealthTypeEnum
from .autocomplete import counter_name_autocomplete_for_character, health_type_autocomplete

def register_remove_commands(cog):
    @cog.remove_group.command(name="character", description="Remove a character and all its counters")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def remove_character_cmd(
        interaction: discord.Interaction,
        character: str
    ):
        user_id = str(interaction.user.id)
        character = sanitize_string(character)
        success, error, details = remove_character(user_id, character)
        if success:
            msg = f"Character '{character}' removed.\nCounters removed:\n{details}" if details else f"Character '{character}' removed."
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to remove character.", ephemeral=True)

    @cog.remove_group.command(name="counter", description="Remove a counter from a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def remove_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str
    ):
        user_id = str(interaction.user.id)
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        success, error, details = remove_counter(character_id, counter)
        if success:
            msg = f"Counter '{counter}' removed from character '{character}'.\nRemaining counters:\n{details}" if details else f"Counter '{counter}' removed from character '{character}'."
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to remove counter.", ephemeral=True)

    @cog.remove_group.command(name="health", description="Remove a health tracker from a character by type")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete)
    async def remove_health(
        interaction: discord.Interaction,
        character: str,
        health_type: str
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        try:
            ht_enum = HealthTypeEnum(health_type)
        except ValueError:
            await interaction.response.send_message("Invalid health type.", ephemeral=True)
            return
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        health_list = char_doc.get("health", [])
        new_health_list = [h for h in health_list if h.get("health_type") != ht_enum.value]
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": new_health_list}})
        await interaction.response.send_message(
            f"Health tracker ({health_type}) removed from character '{character}'.", ephemeral=True
        )
