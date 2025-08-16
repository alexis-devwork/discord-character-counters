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
        await _handle_counter_update(
            interaction, character, counter, target, "perm", new_value,
            lambda: _update_counter_in_mongodb(character_id, counter, "perm", target.perm, target)
        )

    @cog.character_group.command(name="bedlam", description="Set bedlam for a counter (only perm_is_maximum_bedlam counters)")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=bedlam_counter_autocomplete)
    async def bedlam(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return
        counters = get_counters_for_character(character_id)
        target = _get_bedlam_counter(counters, counter)
        if not target:
            await handle_counter_not_found(interaction)
            return
        await _handle_counter_update(
            interaction, character, counter, target, "bedlam", new_value,
            lambda: _update_counter_in_mongodb(character_id, counter, "bedlam", target.bedlam)
        )
