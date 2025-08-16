import discord
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    get_counters_for_character,
    generate_counters_output,
    fully_unescape
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

    # Helper function to generate character counter display
    async def _display_character_counters(interaction, character, character_id):
        """Generate and display counters for a character after an action."""
        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)

        # Add health trackers to the output
        from bson import ObjectId
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []
        if health_entries:
            msg += "\n\n**Health Trackers:**"

            # Get normal health, simplified to get the first one where type is "normal"
            normal_health = None
            for h in health_entries:
                if h.get("health_type") == "normal":
                    normal_health = h
                    break

            if normal_health:
                health_obj = Health(
                    health_type=normal_health.get("health_type"),
                    damage=normal_health.get("damage", []),
                    health_levels=normal_health.get("health_levels", None)
                )
                msg += f"\n{health_obj.display(health_entries)}"

            # Display any other health types that aren't normal or chimerical
            for h in health_entries:
                if h.get("health_type") != "normal" and h.get("health_type") != "chimerical":
                    health_obj = Health(
                        health_type=h.get("health_type"),
                        damage=h.get("damage", []),
                        health_levels=h.get("health_levels", None)
                    )
                    msg += f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"

        return msg

    # Modified damage command moved directly to avct_group
    @cog.avct_group.command(name="damage", description="Add damage to a health tracker (defaults to normal health)")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, damage_type=damage_type_autocomplete)
    async def damage(
        interaction: discord.Interaction,
        character: str,
        damage_type: str,
        levels: int,
        chimerical: bool = False  # Optional boolean flag for chimerical damage
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Set health type based on chimerical flag
        health_type = HealthTypeEnum.chimerical.value if chimerical else HealthTypeEnum.normal.value

        # Validate damage type
        try:
            dt_enum = DamageEnum(damage_type)
        except ValueError:
            await _handle_invalid_damage_type(interaction)
            return

        # Get character document and health list
        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        # Find the specific health tracker
        health_obj_dict = _get_health_tracker(health_list, health_type)
        if not health_obj_dict:
            await interaction.response.send_message(
                f"No {health_type} health tracker found for this character. Add one with /configav add health first.",
                ephemeral=True
            )
            return

        # Create health object and add damage
        health_obj = _create_health_object(health_obj_dict)
        damage_msg = health_obj.add_damage(levels, dt_enum)

        # Update health in MongoDB
        _update_health_in_database(character_id, health_list, health_type, health_obj.damage)

        # Generate the same output as character counters
        msg = await _display_character_counters(interaction, character, character_id)

        health_type_display = "chimerical" if chimerical else "normal"
        if damage_msg:
            await interaction.response.send_message(
                f"{damage_msg}\n\nCounters for character '{character}':\n{msg}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Added {levels} levels of {damage_type} damage to {health_type_display} health.\n\n"
                f"Counters for character '{character}':\n{msg}",
                ephemeral=True
            )

    # Modified heal command to default to normal health type
    @cog.avct_group.command(name="heal", description="Heal damage from a health tracker (defaults to normal health)")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def heal(
        interaction: discord.Interaction,
        character: str,
        levels: int,
        chimerical: bool = False  # Optional boolean flag for chimerical healing
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Set health type based on chimerical flag
        health_type = HealthTypeEnum.chimerical.value if chimerical else HealthTypeEnum.normal.value

        # Get character document and health list
        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        # Find the specific health tracker
        health_obj_dict = _get_health_tracker(health_list, health_type)
        if not health_obj_dict:
            await interaction.response.send_message(
                f"No {health_type} health tracker found for this character. Add one with /configav add health first.",
                ephemeral=True
            )
            return

        # Create health object and remove damage
        health_obj = _create_health_object(health_obj_dict)
        health_obj.remove_damage(levels)

        # Update health in MongoDB
        _update_health_in_database(character_id, health_list, health_type, health_obj.damage)

        # Generate the same output as character counters
        msg = await _display_character_counters(interaction, character, character_id)

        health_type_display = "chimerical" if chimerical else "normal"
        await interaction.response.send_message(
            f"Healed {levels} levels of damage from {health_type_display} health.\n\n"
            f"Counters for character '{character}':\n{msg}",
            ephemeral=True
        )
