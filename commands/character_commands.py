import discord
from utils import (
    sanitize_string,
    get_all_user_characters_for_user,
    get_character_id_by_user_and_name,
    get_counters_for_character,
    fully_unescape,
    generate_counters_output,
    handle_character_not_found,
    handle_counter_not_found,
    update_counter_in_db,  # Add import
)
from utils import characters_collection, CharacterRepository
from health import Health, HealthTypeEnum
from bson import ObjectId
from .autocomplete import (
    character_name_autocomplete,
    counter_name_autocomplete_for_character,
    bedlam_counter_autocomplete
)
from avct_cog import register_command
from counter import CounterTypeEnum

@register_command("character_group")
def register_character_commands(cog):
    # Helper functions
    def _get_counter_by_name(counters, counter_name):
        """Get a counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name), None)

    def _get_bedlam_counter(counters, counter_name):
        """Get a bedlam counter by its name from a list of counters."""
        return next((c for c in counters if c.counter == counter_name and c.counter_type == CounterTypeEnum.perm_is_maximum_bedlam.value), None)

    async def _validate_new_temp_value(target, new_value, interaction):
        """Validate and adjust a new temp value based on counter type."""
        if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
            if new_value > target.perm:
                return target.perm, True
            elif new_value < 0:
                await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            else:
                return new_value, True
        else:
            if new_value < 0:
                await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return None, False
            return new_value, True

    async def _validate_new_perm_value(target, new_value, interaction):
        """Validate a new perm value."""
        if new_value < 0:
            await interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
            return None, False
        return new_value, True

    async def _validate_new_bedlam_value(target, new_value, interaction):
        """Validate a new bedlam value."""
        if new_value < 0:
            await interaction.response.send_message("Bedlam cannot be negative.", ephemeral=True)
            return None, False
        if new_value > target.perm:
            await interaction.response.send_message(f"Bedlam cannot exceed perm ({target.perm}).", ephemeral=True)
            return None, False
        return new_value, True

    def _update_counter_in_mongodb(character_id, counter_name, field, value, target=None):
        # Deprecated: use update_counter_in_db from utils
        return update_counter_in_db(character_id, counter_name, field, value, target)

    def _build_health_output(health_entries):
        msg = "\n\n**Health Trackers:**"
        # Get normal health
        normal_health = next((h for h in health_entries if h.get("health_type") == HealthTypeEnum.normal.value), None)
        if normal_health:
            health_obj = Health(
                health_type=normal_health.get("health_type"),
                damage=normal_health.get("damage", []),
                health_levels=normal_health.get("health_levels", None)
            )
            msg += f"\n{health_obj.display(health_entries)}"
        # Display other health types
        for h in health_entries:
            if h.get("health_type") != HealthTypeEnum.normal.value and h.get("health_type") != HealthTypeEnum.chimerical.value:
                health_obj = Health(
                    health_type=h.get("health_type"),
                    damage=h.get("damage", []),
                    health_levels=h.get("health_levels", None)
                )
                msg += f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"
        return msg

    async def _send_counter_response(interaction, character, msg, public=False):
        await interaction.response.send_message(
            f"Counters for character '{character}':\n{msg}",
            ephemeral=not public
        )

    async def _handle_counter_update(interaction, character, counter, target, field, value, update_func, public=False):
        # Validate new value
        if field == "temp":
            adjusted_value, is_valid = await _validate_new_temp_value(target, value, interaction)
            if not is_valid:
                return
            target.temp = adjusted_value
        elif field == "perm":
            adjusted_value, is_valid = await _validate_new_perm_value(target, value, interaction)
            if not is_valid:
                return
            target.perm = adjusted_value
            if target.counter_type in [CounterTypeEnum.perm_is_maximum.value, CounterTypeEnum.perm_is_maximum_bedlam.value]:
                if target.temp > target.perm:
                    target.temp = target.perm
        elif field == "bedlam":
            adjusted_value, is_valid = await _validate_new_bedlam_value(target, value, interaction)
            if not is_valid:
                return
            target.bedlam = adjusted_value

        # Update in MongoDB
        updated_counters = update_func()
        msg = generate_counters_output(updated_counters, fully_unescape)
        await interaction.response.send_message(
            f"{field.capitalize()} for counter '{counter}' on character '{character}' set to {value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True
        )

    # Add show command directly to avct_group
    @cog.avct_group.command(name="show", description="Show all counters and health for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def show_character(
        interaction: discord.Interaction,
        character: str,
        public: bool = False  # Optional boolean flag to make response visible to everyone
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await handle_character_not_found(interaction)
            return

        counters = get_counters_for_character(character_id)
        if not counters:
            await handle_counter_not_found(interaction)
            return

        # Generate counters output
        msg = generate_counters_output(counters, fully_unescape)

        # Add health trackers to the bottom of the output
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []
        if health_entries:
            msg += _build_health_output(health_entries)

        # Set ephemeral based on the public flag (ephemeral=True when public=False)
        await _send_counter_response(interaction, character, msg, public)

    # Other character commands moved to configav_group's character_group
    @cog.character_group.command(name="list", description="List your characters")
    async def list_characters(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        entries = get_all_user_characters_for_user(user_id)
        if not entries:
            await interaction.response.send_message("No characters found.", ephemeral=True)
            return
        msg = "\n".join([f"ID: {getattr(e, 'id', 'N/A')}, Character: {e.character}" for e in entries])
        await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

    @cog.character_group.command(name="temp", description="Set temp value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def temp(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await handle_counter_not_found(interaction)
            return

        # Remove single_number counter with is_exhaustible if value would be 0
        if (
            target.counter_type == CounterTypeEnum.single_number.value
            and getattr(target, "is_exhaustible", False)
            and new_value == 0
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

        await _handle_counter_update(
            interaction, character, counter, target, "temp", new_value,
            lambda: _update_counter_in_mongodb(character_id, counter, "temp", target.temp)
        )

    @cog.character_group.command(name="perm", description="Set perm value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def perm(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return
        counters = get_counters_for_character(character_id)
        target = _get_counter_by_name(counters, counter)
        if not target:
            await handle_counter_not_found(interaction)
            return

        # Remove single_number counter with is_exhaustible if value would be 0
        if (
            target.counter_type == CounterTypeEnum.single_number.value
            and getattr(target, "is_exhaustible", False)
            and new_value == 0
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

        await _handle_counter_update(
            interaction, character, counter, target, "perm", new_value,
            lambda: _update_counter_in_mongodb(character_id, counter, "perm", target.perm, target)
        )

    # Register minus_cmd ONLY in avct_group (not in character_group or edit_group)
    @cog.avct_group.command(name="minus", description="Remove points from a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def minus_cmd(
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

        # Remove single_number counter with is_exhaustible if value would be 0 after decrement
        if (
            target.counter_type == CounterTypeEnum.single_number.value
            and getattr(target, "is_exhaustible", False)
            and (target.temp - points) == 0
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

        # --- FIX: Handle Reset_Eligible (perm_is_maximum with is_resettable) ---
        if (
            target.counter_type == CounterTypeEnum.perm_is_maximum.value
            and getattr(target, "is_resettable", False)
        ):
            # Decrement temp, but do not allow below zero
            new_temp = max(target.temp - points, 0)
            target.temp = new_temp
            # Save to DB
            from utils import update_counter_in_db
            counters = update_counter_in_db(character_id, counter, "temp", target.temp, target)
            msg = generate_counters_output(counters, fully_unescape)
            await interaction.response.send_message(
                f"Removed {points} point(s) from counter '{counter}' on character '{character}'.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True
            )
            return

        # Default: update temp
        from utils import update_counter
        success, error = update_counter(character_id, counter, "temp", -points)
        if success:
            msg = generate_counters_output(get_counters_for_character(character_id), fully_unescape)
            await interaction.response.send_message(
                f"Removed {points} point(s) from counter '{counter}' on character '{character}'.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True
            )
        else:
            if error == "Counter not found.":
                await handle_counter_not_found(interaction)
            else:
                await interaction.response.send_message(error or "Failed to remove points from counter.", ephemeral=True)

    @cog.avct_group.command(name="reset_eligible", description="Reset all eligible counters for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def reset_eligible_cmd(
        interaction: discord.Interaction,
        character: str
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        from utils import reset_if_eligible, get_counters_for_character, fully_unescape, generate_counters_output
        reset_count = reset_if_eligible(character_id)
        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)
        if reset_count > 0:
            await interaction.response.send_message(
                f"Reset {reset_count} eligible counters for character '{character}'.\n\n{msg}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"No eligible counters to reset for character '{character}'.\n\n{msg}",
                ephemeral=True
            )
