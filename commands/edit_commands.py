import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    get_counters_for_character,
    update_counter_comment,
    set_counter_category,
    generate_counters_output,
    fully_unescape,
    rename_counter,
    rename_character,
    update_counter,
    display_character_counters,
    handle_character_not_found,
    handle_counter_not_found,
    update_counter_in_db  # Add import
)
from utils import characters_collection, CharacterRepository
from bson import ObjectId
from health import Health
from .autocomplete import (
    character_name_autocomplete,
    counter_name_autocomplete_for_character,
    category_autocomplete
)
from avct_cog import register_command
from counter import CounterTypeEnum

@register_command("edit_group")
def register_edit_commands(cog):
    # Helper functions
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

    async def _update_temp_value(target, value, interaction):
        """Update the temp value with appropriate validations."""
        if value < 0:
            await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
            return None, False
        # For single_number type, set perm to same value
        if target.counter_type == CounterTypeEnum.single_number.value:
            target.perm = value
            return value, True
        if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
            if value > target.perm:
                return target.perm, True
            else:
                return value, True
        else:
            return value, True

    def _update_perm_value(target, value):
        """Update the perm value and adjust temp if necessary."""
        if value < 0:
            # If value < 0, set both temp and perm to zero for all types
            target.perm = 0
            target.temp = 0
            return target
        # For single_number type, set temp to same value
        if target.counter_type == CounterTypeEnum.single_number.value:
            target.temp = value
        target.perm = value
        # For perm_is_maximum types, adjust temp if perm is lowered below temp
        if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
            if target.temp > target.perm:
                target.temp = target.perm
        return target

    def _get_counter_by_name(counters, counter_name):
        """Get a counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name), None)

    def _update_counter_in_mongodb(character_id, counter, target):
        # Deprecated: use update_counter_in_db from utils
        # Only updates perm and temp fields
        return update_counter_in_db(character_id, counter, "perm", target.perm, target)

    def _build_full_character_output(character_id):
        from utils import CharacterRepository
        from bson import ObjectId
        from health import Health, HealthTypeEnum

        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []
        if health_entries:
            # Replicate _build_health_output logic from character_commands.py
            msg += "\n\n**Health Trackers:**"
            normal_health = next((h for h in health_entries if h.get("health_type") == HealthTypeEnum.normal.value), None)
            if normal_health:
                health_obj = Health(
                    health_type=normal_health.get("health_type"),
                    damage=normal_health.get("damage", []),
                    health_levels=normal_health.get("health_levels", None)
                )
                msg += f"\n{health_obj.display(health_entries)}"
            for h in health_entries:
                if h.get("health_type") != HealthTypeEnum.normal.value and h.get("health_type") != HealthTypeEnum.chimerical.value:
                    health_obj = Health(
                        health_type=h.get("health_type"),
                        damage=h.get("damage", []),
                        health_levels=h.get("health_levels", None)
                    )
                    msg += f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"
        return msg

    # These all stay in the configav edit group which was already defined in avct_cog.py

    @cog.edit_group.command(name="counter", description="Set temp or perm for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def set_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        field: str,
        value: int
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
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
            await handle_counter_not_found(interaction)
            return

        # Remove single_number counter with is_exhaustible if value would be 0
        if (
            target.counter_type == CounterTypeEnum.single_number.value
            and getattr(target, "is_exhaustible", False)
            and value == 0
        ):
            from utils import remove_counter
            success, error, details = remove_counter(character_id, counter)
            if success:
                msg = details if details else "No remaining counters."
                await interaction.response.send_message(
                    f"Counter '{counter}' was removed from character '{character}' because its value reached 0.\nRemaining counters:\n{msg}",
                    ephemeral=True
                )
            else:
                await handle_counter_not_found(interaction) if error == "Counter not found." else interaction.response.send_message(error or "Failed to remove counter.", ephemeral=True)
            return

        # Update the appropriate field
        if field == "temp":
            # If value < 0, set both temp and perm to zero
            if value < 0:
                target.temp = 0
                target.perm = 0
            else:
                new_value, is_valid = await _update_temp_value(target, value, interaction)
                if not is_valid:
                    return
                target.temp = new_value
        elif field == "perm":
            # If value < 0, set both temp and perm to zero
            if value < 0:
                target.perm = 0
                target.temp = 0
            else:
                # For perm_is_maximum types, check if temp would be greater than perm
                if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
                    if target.temp > value:
                        await interaction.response.send_message(
                            "Temp cannot be greater than perm for this counter type. No changes were saved.",
                            ephemeral=True
                        )
                        return
                target.perm = value
                # For perm_is_maximum types, adjust temp if perm is lowered below temp
                if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
                    if target.temp > target.perm:
                        target.temp = target.perm

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
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        success, error = set_counter_comment(character_id, counter, comment)

        if success:
            await interaction.response.send_message(
                f"Comment for counter '{counter}' on character '{character}' set.", ephemeral=True)
        else:
            await handle_counter_not_found(interaction) if error == "Counter not found." else interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

    # --- Edit category ---
    @cog.edit_group.command(name="category", description="Set the category for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character, category=category_autocomplete)
    async def edit_category_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        category: str
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        success, error = set_counter_category(character_id, counter, category)

        if success:
            await interaction.response.send_message(
                f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
        else:
            await handle_counter_not_found(interaction) if error == "Counter not found." else interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

    # --- Rename counter ---
    @cog.rename_group.command(name="counter", description="Rename a counter for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def rename_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        new_name: str
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        success, error = rename_counter(character_id, counter, new_name)

        if success:
            await interaction.response.send_message(
                f"Counter '{counter}' on character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            await handle_counter_not_found(interaction) if error == "Counter to rename not found." else interaction.response.send_message(error or "Failed to rename counter.", ephemeral=True)

    # --- Rename character ---
    @cog.rename_group.command(name="character", description="Rename a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def rename_character_cmd(
        interaction: discord.Interaction,
        character: str,
        new_name: str
    ):
        user_id = str(interaction.user.id)
        success, error = rename_character(user_id, character, new_name)

        if success:
            await interaction.response.send_message(
                f"Character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            # Always await the response, even for validation errors
            if error == "Character to rename not found.":
                await handle_character_not_found(interaction)
            else:
                await interaction.response.send_message(error or "Failed to rename character.", ephemeral=True)

    @cog.avct_group.command(name="plus", description="Add points to a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def plus_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        points: int = 1
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        # Get counter
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await handle_counter_not_found(interaction)
            return

        # If increment would result in temp < 0, set both temp and perm to zero
        if (target.temp + points) < 0:
            target.temp = 0
            target.perm = 0
            counters = _update_counter_in_mongodb(character_id, counter, target)
            msg = _build_full_character_output(character_id)
            await interaction.response.send_message(
                f"Added {points} point(s) to counter '{counter}' on character '{character}'.\n\n"
                f"{msg}", ephemeral=True)
            return

        success, error = update_counter(character_id, counter, "temp", points)

        if success:
            msg = _build_full_character_output(character_id)
            await interaction.response.send_message(
                f"Added {points} point(s) to counter '{counter}' on character '{character}'.\n\n"
                f"{msg}", ephemeral=True)
        else:
            if error == "Counter not found.":
                await handle_counter_not_found(interaction)
            else:
                await interaction.response.send_message(error or "Failed to add points to counter.", ephemeral=True)
