import discord
from utils import (
    sanitize_string,
    get_all_user_characters_for_user,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    get_counters_for_character,
    fully_unescape,
    generate_counters_output
)
from utils import characters_collection
from health import Health
from bson import ObjectId
from .autocomplete import counter_name_autocomplete_for_character, bedlam_counter_autocomplete

def register_character_commands(cog):
    # Helper functions
    async def _handle_character_not_found(interaction):
        """Handle the case when a character is not found."""
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return False

    async def _handle_counter_not_found(interaction):
        """Handle the case when a counter is not found."""
        await interaction.response.send_message("Counter not found.", ephemeral=True)
        return False

    def _get_counter_by_name(counters, counter_name):
        """Get a counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name), None)

    def _get_bedlam_counter(counters, counter_name):
        """Get a bedlam counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name and c.counter_type == "perm_is_maximum_bedlam"), None)

    def _validate_new_temp_value(target, new_value, interaction):
        """Validate and adjust a new temp value based on counter type."""
        if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if new_value > target.perm:
                return target.perm, True
            elif new_value < 0:
                interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            else:
                return new_value, True
        else:
            if new_value < 0:
                interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            return new_value, True

    def _validate_new_perm_value(target, new_value, interaction):
        """Validate a new perm value."""
        if new_value < 0:
            interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
            return None, False
        return new_value, True

    def _validate_new_bedlam_value(target, new_value, interaction):
        """Validate a new bedlam value."""
        if new_value < 0:
            interaction.response.send_message("Bedlam cannot be negative.", ephemeral=True)
            return None, False
        if new_value > target.perm:
            interaction.response.send_message(f"Bedlam cannot exceed perm ({target.perm}).", ephemeral=True)
            return None, False
        return new_value, True

    def _update_counter_in_mongodb(character_id, counter_name, field, value, target=None):
        """Update a counter field in MongoDB."""
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        counters_list = char_doc.get("counters", [])

        for c in counters_list:
            if c["counter"] == counter_name:
                c[field] = value
                # If we're updating perm, we might need to adjust temp too
                if field == "perm" and target and target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                    if target.temp > target.perm:
                        c["temp"] = target.temp = target.perm

        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters_list}})
        return get_counters_for_character(character_id)

    def _generate_health_trackers_output(character_id):
        """Generate output for health trackers."""
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []

        if not health_entries:
            return ""

        output = "\n\n**Health Trackers:**"
        for h in health_entries:
            health_obj = Health(
                health_type=h.get("health_type"),
                damage=h.get("damage", []),
                health_levels=h.get("health_levels", None)
            )
            output += f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"

        return output

    @cog.character_group.command(name="list", description="List your characters")
    async def list_characters(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        entries = get_all_user_characters_for_user(user_id)
        if not entries:
            await interaction.response.send_message("No characters found.", ephemeral=True)
            return
        msg = "\n".join([f"ID: {getattr(e, 'id', 'N/A')}, Character: {e.character}" for e in entries])
        await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

    @cog.character_group.command(name="counters", description="List counters for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def counters(interaction: discord.Interaction, character: str):
        user_id = str(interaction.user.id)
        character = sanitize_string(character)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await interaction.response.send_message(
                "Character not found for this user. Please select a character from the dropdown/autocomplete.",
                ephemeral=True
            )
            return

        counters = get_counters_for_character(character_id)
        if not counters:
            await interaction.response.send_message("No counters found for this character.", ephemeral=True)
            return

        # Generate counters output
        msg = generate_counters_output(counters, fully_unescape)

        # Add health trackers
        msg += _generate_health_trackers_output(character_id)

        await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="temp", description="Set temp value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def temp(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)

        # Get character
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Get counters
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await _handle_counter_not_found(interaction)
            return

        # Validate new value
        adjusted_value, is_valid = _validate_new_temp_value(target, new_value, interaction)
        if not is_valid:
            return

        # Set temp value
        target.temp = adjusted_value

        # Update in MongoDB
        updated_counters = _update_counter_in_mongodb(character_id, counter, "temp", target.temp)

        # Generate response
        msg = generate_counters_output(updated_counters, fully_unescape)
        await interaction.response.send_message(
            f"Temp for counter '{counter}' on character '{character}' set to {adjusted_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="perm", description="Set perm value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def perm(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)

        # Get character
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Get counters
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await _handle_counter_not_found(interaction)
            return

        # Validate new value
        adjusted_value, is_valid = _validate_new_perm_value(target, new_value, interaction)
        if not is_valid:
            return

        # Set perm value
        target.perm = adjusted_value

        # For perm_is_maximum types, adjust temp if perm is lowered below temp
        if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if target.temp > target.perm:
                target.temp = target.perm

        # Update in MongoDB
        updated_counters = _update_counter_in_mongodb(character_id, counter, "perm", target.perm, target)

        # Generate response
        msg = generate_counters_output(updated_counters, fully_unescape)
        await interaction.response.send_message(
            f"Perm for counter '{counter}' on character '{character}' set to {adjusted_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="bedlam", description="Set bedlam for a counter (only perm_is_maximum_bedlam counters)")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=bedlam_counter_autocomplete)
    async def bedlam(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)

        # Get character
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Get counters
        counters = get_counters_for_character(character_id)
        target = _get_bedlam_counter(counters, counter)
        if not target:
            await interaction.response.send_message(
                "Counter not found or not of type perm_is_maximum_bedlam.",
                ephemeral=True
            )
            return

        # Validate new value
        adjusted_value, is_valid = _validate_new_bedlam_value(target, new_value, interaction)
        if not is_valid:
            return

        # Set bedlam value
        target.bedlam = adjusted_value

        # Update in MongoDB
        updated_counters = _update_counter_in_mongodb(character_id, counter, "bedlam", target.bedlam)

        # Generate response
        msg = generate_counters_output(updated_counters, fully_unescape)
        await interaction.response.send_message(
            f"Bedlam for counter '{counter}' on character '{character}' set to {adjusted_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
