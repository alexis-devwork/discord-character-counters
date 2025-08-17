import discord
from utils import (
    get_character_id_by_user_and_name,
    get_counters_for_character,
    generate_counters_output,
    fully_unescape,
    handle_character_not_found,
    handle_invalid_damage_type,
    handle_health_tracker_not_found,
    update_health_in_db,  # Add import
    add_health_level,  # Add import
)
from utils import CharacterRepository
from health import Health, HealthTypeEnum, DamageEnum, HealthLevelEnum
from bson import ObjectId
from .autocomplete import (
    character_name_autocomplete,
    damage_type_autocomplete,
)
from avct_cog import register_command


@register_command("avct_group")
def register_health_commands(cog):
    # Helper functions
    def _get_character_document(character_id):
        """Get the character document from the database."""
        return CharacterRepository.find_one({"_id": ObjectId(character_id)})

    def _get_health_tracker(health_list, health_type):
        """Find and return a specific health tracker from the list."""
        return next(
            (h for h in health_list if h.get("health_type") == health_type), None
        )

    def _create_health_object(health_dict):
        """Create a Health object from a dictionary."""
        return Health(
            health_type=health_dict.get("health_type"),
            damage=health_dict.get("damage", []),
            health_levels=health_dict.get("health_levels", None),
        )

    # Deprecated: use update_health_in_db from utils
    def _update_health_in_database(character_id, health_list, health_type, damage):
        """Update the health tracker in the database."""
        update_health_in_db(character_id, health_type, damage)

    def _health_type_display(chimerical):
        return "chimerical" if chimerical else "normal"

    async def _send_health_response(interaction, character, msg, action_msg):
        await interaction.response.send_message(
            f"{action_msg}\n\nCounters for character '{character}':\n{msg}",
            ephemeral=True,
        )

    def _build_full_character_output(character_id):
        from utils import CharacterRepository
        from bson import ObjectId
        from health import Health, HealthTypeEnum

        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []
        if health_entries:
            msg += "\n\n**Health Trackers:**"
            normal_health = next(
                (
                    h
                    for h in health_entries
                    if h.get("health_type") == HealthTypeEnum.normal.value
                ),
                None,
            )
            if normal_health:
                health_obj = Health(
                    health_type=normal_health.get("health_type"),
                    damage=normal_health.get("damage", []),
                    health_levels=normal_health.get("health_levels", None),
                )
                msg += f"\n{health_obj.display(health_entries)}"
            for h in health_entries:
                if (
                    h.get("health_type") != HealthTypeEnum.normal.value
                    and h.get("health_type") != HealthTypeEnum.chimerical.value
                ):
                    health_obj = Health(
                        health_type=h.get("health_type"),
                        damage=h.get("damage", []),
                        health_levels=h.get("health_levels", None),
                    )
                    msg += (
                        f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"
                    )
        return msg

    # Modified damage command moved directly to avct_group
    @cog.avct_group.command(
        name="damage",
        description="Add damage to a health tracker (defaults to normal health)",
    )
    @discord.app_commands.autocomplete(
        character=character_name_autocomplete, damage_type=damage_type_autocomplete
    )
    async def damage(
        interaction: discord.Interaction,
        character: str,
        damage_type: str,
        levels: int,
        chimerical: bool = False,  # Optional boolean flag for chimerical damage
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await handle_character_not_found(interaction)
            return

        health_type = (
            HealthTypeEnum.chimerical.value
            if chimerical
            else HealthTypeEnum.normal.value
        )

        try:
            dt_enum = DamageEnum(damage_type)
        except ValueError:
            await handle_invalid_damage_type(interaction)
            return

        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        health_obj_dict = _get_health_tracker(health_list, health_type)
        if not health_obj_dict:
            await handle_health_tracker_not_found(interaction)
            return

        # Create health object and add damage
        health_obj = _create_health_object(health_obj_dict)
        damage_msg = health_obj.add_damage(levels, dt_enum)

        # Update health in MongoDB
        _update_health_in_database(
            character_id, health_list, health_type, health_obj.damage
        )

        # Generate the same output as character counters
        msg = _build_full_character_output(character_id)

        action_msg = (
            damage_msg
            if damage_msg
            else (
                f"Added {levels} levels of {damage_type} damage to {_health_type_display(chimerical)} health."
            )
        )
        await _send_health_response(interaction, character, msg, action_msg)

    # Modified heal command to default to normal health type
    @cog.avct_group.command(
        name="heal",
        description="Heal damage from a health tracker (defaults to normal health)",
    )
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def heal(
        interaction: discord.Interaction,
        character: str,
        levels: int,
        chimerical: bool = False,  # Optional boolean flag for chimerical healing
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)

        if character_id is None:
            await handle_character_not_found(interaction)
            return

        health_type = (
            HealthTypeEnum.chimerical.value
            if chimerical
            else HealthTypeEnum.normal.value
        )

        char_doc = _get_character_document(character_id)
        health_list = char_doc.get("health", [])

        health_obj_dict = _get_health_tracker(health_list, health_type)
        if not health_obj_dict:
            await handle_health_tracker_not_found(interaction)
            return

        # Create health object and remove damage
        health_obj = _create_health_object(health_obj_dict)
        health_obj.remove_damage(levels)

        # Update health in MongoDB
        _update_health_in_database(
            character_id, health_list, health_type, health_obj.damage
        )

        # Generate the same output as character counters
        msg = _build_full_character_output(character_id)

        action_msg = f"Healed {levels} levels of damage from {_health_type_display(chimerical)} health."
        await _send_health_response(interaction, character, msg, action_msg)


async def health_level_type_autocomplete(
    interaction: discord.Interaction, current: str
):
    """Autocomplete health level types from HealthLevelEnum."""
    return [
        discord.app_commands.Choice(name=e.value, value=e.value)
        for e in HealthLevelEnum
        if current.lower() in e.value.lower()
    ]


@register_command("configav_group")
def register_configav_health_commands(cog):
    # Get the existing add group that was created in avct_cog.py
    add_group = cog.add_group

    # Modify the command to add health levels to all health trackers
    @add_group.command(
        name="health_level",
        description="Add an extra health level to all health trackers for a character",
    )
    @discord.app_commands.autocomplete(
        character=character_name_autocomplete,
        health_level_type=health_level_type_autocomplete,
    )
    async def add_health_level_cmd(
        interaction: discord.Interaction,
        character: str,
        health_level_type: str,
    ):
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await handle_character_not_found(interaction)
            return

        # Retrieve the character's health trackers
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        if not char_doc:
            await interaction.response.send_message(
                "Character not found.", ephemeral=True
            )
            return

        health_list = char_doc.get("health", [])
        if not health_list:
            await interaction.response.send_message(
                f"No health trackers found for character '{character}'.", ephemeral=True
            )
            return

        # Add the health level to all health trackers
        success = False
        for tracker in health_list:
            tracker_type = tracker.get("health_type")
            levels = tracker.get("health_levels", [])
            levels.append(health_level_type)

            # Sort the health levels based on the predefined order in HealthLevelEnum
            enum_order = [e.value for e in HealthLevelEnum]
            tracker["health_levels"] = sorted(
                levels,
                key=lambda x: enum_order.index(x) if x in enum_order else len(enum_order),
            )

            tracker_success, error = add_health_level(
                character_id, tracker_type, health_level_type
            )
            if tracker_success:
                success = True
            else:
                await interaction.response.send_message(
                    f"Failed to add health level to {tracker_type} tracker: {error}",
                    ephemeral=True,
                )
                return

        if success:
            await interaction.response.send_message(
                f"Added health level '{health_level_type}' to all health trackers for character '{character}'.",
                ephemeral=True,
            )
