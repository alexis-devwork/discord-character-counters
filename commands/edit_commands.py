import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    get_counters_for_character,
    set_counter_comment,
    set_counter_category,
    generate_counters_output,
    fully_unescape,
    rename_counter,
    rename_character,
    category_autocomplete,
    update_counter
)
from utils import characters_collection
from bson import ObjectId
from .autocomplete import counter_name_autocomplete_for_character

def register_edit_commands(cog):
    # Helper functions
    async def _handle_character_not_found(interaction):
        """Handle the case when a character is not found."""
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return False

    async def _handle_counter_not_found(interaction):
        """Handle the case when a counter is not found."""
        await interaction.response.send_message("Counter not found.", ephemeral=True)
        return False

    async def _validate_field(interaction, field):
        """Validate that the field is 'temp' or 'perm'."""
        if field not in ["temp", "perm"]:
            await interaction.response.send_message("Field must be 'temp' or 'perm'.", ephemeral=True)
            return False
        return True

    async def _validate_value(interaction, value):
        """Validate that the value is a non-negative integer."""
        if not isinstance(value, int) or value < 0:
            await interaction.response.send_message("Value must be a non-negative integer.", ephemeral=True)
            return False
        return True

    def _get_counter_by_name(counters, counter_name):
        """Get a counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name), None)

    def _update_temp_value(target, value, interaction):
        """Update the temp value with appropriate validations."""
        if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if value > target.perm:
                return target.perm, True
            elif value < 0:
                interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            else:
                return value, True
        else:
            if value < 0:
                interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            return value, True

    def _update_perm_value(target, value):
        """Update the perm value and adjust temp if necessary."""
        target.perm = value
        # For perm_is_maximum types, adjust temp if perm is lowered below temp
        if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if target.temp > target.perm:
                target.temp = target.perm
        return target

    def _update_counter_in_mongodb(character_id, counter, target):
        """Update a counter in MongoDB."""
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        counters_list = char_doc.get("counters", [])
        for c in counters_list:
            if c["counter"] == counter:
                c["perm"] = target.perm
                c["temp"] = target.temp
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters_list}})
        return get_counters_for_character(character_id)

    @cog.edit_group.command(name="counter", description="Set temp or perm for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def set_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        field: str,
        value: int
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Validate field and value
        if not await _validate_field(interaction, field):
            return

        if not await _validate_value(interaction, value):
            return

        # Get counter
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await _handle_counter_not_found(interaction)
            return

        # Update the appropriate field
        if field == "temp":
            new_value, is_valid = _update_temp_value(target, value, interaction)
            if not is_valid:
                return
            target.temp = new_value
        elif field == "perm":
            target = _update_perm_value(target, value)

        # Update in MongoDB
        counters = _update_counter_in_mongodb(character_id, counter, target)

        # Generate response
        msg = generate_counters_output(counters, fully_unescape)
        await interaction.response.send_message(
            f"Set {field} for counter '{counter}' on character '{character}' to {value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)

    # --- Edit comment ---
    @cog.edit_group.command(name="comment", description="Set the comment for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def edit_comment_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        comment: str
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        comment = sanitize_string(comment)
        user_id = str(interaction.user.id)

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Update comment
        success, error = set_counter_comment(character_id, counter, comment)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"Comment for counter '{counter}' on character '{character}' set.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

    # --- Edit category ---
    @cog.edit_group.command(name="category", description="Set the category for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character, category=category_autocomplete)
    async def edit_category_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        category: str
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        category = sanitize_string(category)
        user_id = str(interaction.user.id)

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Update category
        success, error = set_counter_category(character_id, counter, category)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

    # --- Rename counter ---
    @cog.rename_group.command(name="counter", description="Rename a counter for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def rename_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        new_name: str
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        new_name = sanitize_string(new_name)
        user_id = str(interaction.user.id)

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Rename counter
        success, error = rename_counter(character_id, counter, new_name)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"Counter '{counter}' on character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to rename counter.", ephemeral=True)

    # --- Rename character ---
    @cog.rename_group.command(name="character", description="Rename a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def rename_character_cmd(
        interaction: discord.Interaction,
        character: str,
        new_name: str
    ):
        character = sanitize_string(character)
        new_name = sanitize_string(new_name)
        user_id = str(interaction.user.id)

        # Rename character
        success, error = rename_character(user_id, character, new_name)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"Character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to rename character.", ephemeral=True)

    # --- Spend counter ---
    @cog.spend_group.command(name="counter", description="Decrement the temp value of a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def spend_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        points: int = 1
    ):
        await _handle_counter_update(interaction, character, counter, "temp", -points, "Spent", "from")

    # --- Gain counter ---
    @cog.gain_group.command(name="counter", description="Increment the temp value of a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def gain_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        points: int = 1
    ):
        await _handle_counter_update(interaction, character, counter, "temp", points, "Gained", "to")

    async def _handle_counter_update(interaction, character, counter, field, delta, action_verb, preposition):
        """Handle the update of a counter with appropriate feedback messages."""
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)

        # Get character ID
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await _handle_character_not_found(interaction)
            return

        # Update counter
        success, error = update_counter(character_id, counter, field, delta)

        # Handle result
        points_abs = abs(delta)
        point_text = f"{points_abs} point(s)"

        if success:
            await interaction.response.send_message(
                f"{action_verb} {point_text} {preposition} counter '{counter}' on character '{character}'.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                error or f"Failed to update counter.",
                ephemeral=True
            )
