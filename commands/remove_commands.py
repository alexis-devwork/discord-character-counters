import discord
from utils import (
    get_character_id_by_user_and_name,
    remove_character,
    remove_counter,
    handle_character_not_found,
    handle_invalid_health_type,  # Add this import
    handle_counter_not_found,  # Add this import
)
from utils import CharacterRepository
from bson import ObjectId
from health import HealthTypeEnum
from .autocomplete import (
    character_name_autocomplete,
    counter_name_autocomplete_for_character,
    health_type_autocomplete,
)
from avct_cog import register_command


@register_command("remove_group")
def register_remove_commands(cog):
    # All of these stay in the configav remove group which was already defined in avct_cog.py

    @cog.remove_group.command(
        name="character", description="Remove a character and all its counters"
    )
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def remove_character_cmd(interaction: discord.Interaction, character: str):
        user_id = str(interaction.user.id)
        success, error, details = remove_character(user_id, character)
        if success:
            msg = (
                f"Character '{character}' removed.\nCounters removed:\n{details}"
                if details
                else f"Character '{character}' removed."
            )
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await handle_character_not_found(
                interaction
            ) if error == "Character not found." else interaction.response.send_message(
                error or "Failed to remove character.", ephemeral=True
            )

    @cog.remove_group.command(
        name="counter", description="Remove a counter from a character"
    )
    @discord.app_commands.autocomplete(
        character=character_name_autocomplete,
        counter=counter_name_autocomplete_for_character,
    )
    async def remove_counter_cmd(
        interaction: discord.Interaction, character: str, counter: str
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return
        success, error, details = remove_counter(character_id, counter)
        if success:
            msg = (
                f"Counter '{counter}' removed from character '{character}'.\nRemaining counters:\n{details}"
                if details
                else f"Counter '{counter}' removed from character '{character}'."
            )
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await handle_counter_not_found(
                interaction
            ) if error == "Counter not found." else interaction.response.send_message(
                error or "Failed to remove counter.", ephemeral=True
            )

    @cog.remove_group.command(
        name="health_tracker",  # Renamed from "health"
        description="Remove a health tracker from a character by type",
    )
    @discord.app_commands.autocomplete(
        character=character_name_autocomplete, health_type=health_type_autocomplete
    )
    async def remove_health_tracker(  # Renamed from remove_health
        interaction: discord.Interaction, character: str, health_type: str
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return
        try:
            ht_enum = HealthTypeEnum(health_type)
        except ValueError:
            await handle_invalid_health_type(interaction)
            return
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        health_list = char_doc.get("health", [])
        new_health_list = [
            h for h in health_list if h.get("health_type") != ht_enum.value
        ]
        CharacterRepository.update_one(
            {"_id": ObjectId(character_id)}, {"$set": {"health": new_health_list}}
        )
        await interaction.response.send_message(
            f"Health tracker ({health_type}) removed from character '{character}'.",
            ephemeral=True,
        )
