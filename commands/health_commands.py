import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
)
from utils import characters_collection
from health import Health, HealthTypeEnum, DamageEnum
from bson import ObjectId
from .autocomplete import health_type_autocomplete, damage_type_autocomplete

def register_health_commands(cog):
    # Remove this command as it's already defined in remove_commands.py
    # @cog.remove_group.command(name="health", description="Remove a health tracker from a character by type")
    # ...

    # Add damage to health tracker
    @cog.avct_group.command(name="damage", description="Add damage to a health tracker")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete, damage_type=damage_type_autocomplete)
    async def damage(
        interaction: discord.Interaction,
        character: str,
        health_type: str,
        damage_type: str,
        levels: int
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        try:
            ht_enum = HealthTypeEnum(health_type)
            dt_enum = DamageEnum(damage_type)
        except ValueError:
            await interaction.response.send_message("Invalid health or damage type.", ephemeral=True)
            return
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        health_list = char_doc.get("health", [])
        health_obj_dict = next((h for h in health_list if h.get("health_type") == ht_enum.value), None)
        if not health_obj_dict:
            await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
            return
        health_obj = Health(
            health_type=health_obj_dict.get("health_type"),
            damage=health_obj_dict.get("damage", []),
            health_levels=health_obj_dict.get("health_levels", None)
        )
        msg = health_obj.add_damage(levels, dt_enum)
        # Update health in MongoDB
        for h in health_list:
            if h.get("health_type") == ht_enum.value:
                h["damage"] = health_obj.damage
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
        output = health_obj.display()
        if msg:
            await interaction.response.send_message(f"{msg}\n{output}", ephemeral=True)
        else:
            await interaction.response.send_message(output, ephemeral=True)

    # Heal damage from health tracker
    @cog.avct_group.command(name="heal", description="Heal damage from a health tracker")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete)
    async def heal(
        interaction: discord.Interaction,
        character: str,
        health_type: str,
        levels: int
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
        health_obj_dict = next((h for h in health_list if h.get("health_type") == ht_enum.value), None)
        if not health_obj_dict:
            await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
            return
        health_obj = Health(
            health_type=health_obj_dict.get("health_type"),
            damage=health_obj_dict.get("damage", []),
            health_levels=health_obj_dict.get("health_levels", None)
        )
        health_obj.remove_damage(levels)
        # Update health in MongoDB
        for h in health_list:
            if h.get("health_type") == ht_enum.value:
                h["damage"] = health_obj.damage
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
        output = health_obj.display()
        await interaction.response.send_message(output, ephemeral=True)
