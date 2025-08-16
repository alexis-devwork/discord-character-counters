import discord
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
    # Helper functions
    async def _handle_character_not_found(interaction):
        """Handle the case when a character is not found."""
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return False

    async def _handle_invalid_health_type(interaction):
        """Handle the case when an invalid health type is provided."""
        await interaction.response.send_message("Invalid health type.", ephemeral=True)
        return False

    async def _handle_invalid_damage_type(interaction):
        """Handle the case when an invalid damage type is provided."""
        await interaction.response.send_message("Invalid health or damage type.", ephemeral=True)
        return False

    async def _handle_health_tracker_not_found(interaction):
        """Handle the case when a health tracker is not found."""
        await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
        return False

    def _get_character_document(character_id):
        """Get the character document from the database."""
        return characters_collection.find_one({"_id": ObjectId(character_id)})

    def _get_health_tracker(health_list, health_type):
        """Find and return a specific health tracker from the list."""
        return next((h for h in health_list if h.get("health_type") == health_type), None)

    def _create_health_object(health_dict):
        """Create a Health object from a dictionary."""
        return Health(
            health_type=health_dict.get("health_type"),
            damage=health_dict.get("damage", []),
            health_levels=health_dict.get("health_levels", None)
        )

    def _update_health_in_database(character_id, health_list, health_type, damage):
        """Update the health tracker in the database."""
        for h in health_list:
            if h.get("health_type") == health_type:
                h["damage"] = damage
        characters_collection.update_one(
            {"_id": ObjectId(character_id)},
            {"$set": {"health": health_list}}
        )

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

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Validate health and damage types
        try:
            ht_enum = HealthTypeEnum(health_type)
            dt_enum = DamageEnum(damage_type)
        except ValueError:
            await _handle_invalid_damage_type(interaction)
            return

        # Get character document and health list
        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        # Find the specific health tracker
        health_obj_dict = _get_health_tracker(health_list, ht_enum.value)
        if not health_obj_dict:
            await _handle_health_tracker_not_found(interaction)
            return

        # Create health object and add damage
        health_obj = _create_health_object(health_obj_dict)
        msg = health_obj.add_damage(levels, dt_enum)

        # Update health in MongoDB
        _update_health_in_database(character_id, health_list, ht_enum.value, health_obj.damage)

        # Generate and send response
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

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Validate health type
        try:
            ht_enum = HealthTypeEnum(health_type)
        except ValueError:
            await _handle_invalid_health_type(interaction)
            return

        # Get character document and health list
        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        # Find the specific health tracker
        health_obj_dict = _get_health_tracker(health_list, ht_enum.value)
        if not health_obj_dict:
            await _handle_health_tracker_not_found(interaction)
            return

        # Create health object and remove damage
        health_obj = _create_health_object(health_obj_dict)
        health_obj.remove_damage(levels)

        # Update health in MongoDB
        _update_health_in_database(character_id, health_list, ht_enum.value, health_obj.damage)

        # Generate and send response
        output = health_obj.display()
        await interaction.response.send_message(output, ephemeral=True)
