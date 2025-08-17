import discord
from discord import app_commands
from utils import (
    sanitize_string,
    add_user_character,
    get_character_id_by_user_and_name,
    add_counter,
    PredefinedCounterEnum,
    add_predefined_counter,
    CategoryEnum,
    display_character_counters,  # Import the display function
    fully_unescape,
)
from counter import CounterTypeEnum  # Ensure correct import
from utils import characters_collection, CharacterRepository
from health import Health, HealthTypeEnum, HealthLevelEnum
from bson import ObjectId
from .autocomplete import (
    character_name_autocomplete,
    category_autocomplete,
    predefined_counter_type_autocomplete,
    counter_type_autocomplete,
)
from avct_cog import register_command


@register_command("add_group")
def register_add_commands(cog):
    # --- Helper functions ---
    async def _handle_character_creation_failure(interaction, error):
        """Handle failure when creating a character."""
        await interaction.response.send_message(error, ephemeral=True)
        return False

    def _add_health_tracker(character_id, health_type):
        """Add a health tracker of the specified type to a character."""
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_obj = Health(health_type=health_type)
            health_list = char_doc.get("health", [])
            health_list.append(health_obj.__dict__)
            CharacterRepository.update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
            )
            return True
        return False

    def _add_multiple_health_trackers(character_id, health_types):
        """Add multiple health trackers to a character."""
        char_doc = CharacterRepository.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_list = char_doc.get("health", [])
            for health_type in health_types:
                health_obj = Health(health_type=health_type)
                health_list.append(health_obj.__dict__)
            CharacterRepository.update_one(
                {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
            )
            return True
        return False

    async def _process_character_creation(interaction, character, user_id):
        """Process character creation and return character_id if successful."""
        success, error = add_user_character(user_id, character)
        if not success:
            await _handle_character_creation_failure(interaction, error)
            return None
        return get_character_id_by_user_and_name(user_id, character)

    def _get_replacement_value(replacement):
        """Return the replacement value if provided, otherwise None."""
        return replacement if replacement else None

    # --- Add character for sorc ---
    @cog.add_group.command(
        name="character_sorc",
        description="Add a Sorcerer character (requires willpower and mana)",
    )
    async def add_character_sorc(
        interaction: discord.Interaction, character: str, willpower: int, mana: int
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(
            interaction, character, user_id
        )
        if not character_id:
            return

        # Add counters using add_predefined_counter
        for counter_type, value, label in [
            (PredefinedCounterEnum.willpower, willpower, "willpower"),
            (PredefinedCounterEnum.mana, mana, "mana"),
        ]:
            success, error = add_predefined_counter(
                character_id, counter_type.value, value
            )
            if not success:
                await interaction.response.send_message(
                    f"Failed to add {label} counter: {error}", ephemeral=True
                )
                return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Generate and display the character's counters and health
        msg = display_character_counters(character_id, fully_unescape)
        await interaction.response.send_message(
            f"Character '{character}' added successfully.\n\n{msg}", ephemeral=True
        )

    # --- Add character for vampire ---
    @cog.add_group.command(
        name="character_vampire",
        description="Add a Vampire character (requires blood_pool and willpower)",
    )
    async def add_character_vampire(
        interaction: discord.Interaction,
        character: str,
        blood_pool: int,
        willpower: int,
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(
            interaction, character, user_id
        )
        if not character_id:
            return

        # Add counters using add_predefined_counter
        for counter_type, value, label in [
            (PredefinedCounterEnum.blood_pool, blood_pool, "blood_pool"),
            (PredefinedCounterEnum.willpower, willpower, "willpower"),
        ]:
            success, error = add_predefined_counter(
                character_id, counter_type.value, value
            )
            if not success:
                await interaction.response.send_message(
                    f"Failed to add {label} counter: {error}", ephemeral=True
                )
                return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Generate and display the character's counters and health
        msg = display_character_counters(character_id, fully_unescape)
        await interaction.response.send_message(
            f"Character '{character}' added successfully.\n\n{msg}", ephemeral=True
        )

    # --- Add character for changeling ---
    @cog.add_group.command(
        name="character_changeling",
        description="Add a Changeling character (requires willpower_fae, glamour, and banality)",
    )
    async def add_character_changeling(
        interaction: discord.Interaction,
        character: str,
        willpower_fae: int,
        glamour: int,
        banality: int,
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(
            interaction, character, user_id
        )
        if not character_id:
            return

        # Add counters using add_predefined_counter
        for counter_type, value, label in [
            (PredefinedCounterEnum.willpower_fae, willpower_fae, "willpower_fae"),
            (PredefinedCounterEnum.glamour, glamour, "glamour"),
            (PredefinedCounterEnum.nightmare, 0, "nightmare"),  # Default nightmare to 0
            (PredefinedCounterEnum.banality, banality, "banality"),
        ]:
            success, error = add_predefined_counter(
                character_id, counter_type.value, value
            )
            if not success:
                await interaction.response.send_message(
                    f"Failed to add {label} counter: {error}", ephemeral=True
                )
                return

        # Add health trackers
        _add_multiple_health_trackers(
            character_id, [HealthTypeEnum.normal.value, HealthTypeEnum.chimerical.value]
        )

        # Generate and display the character's counters and health
        msg = display_character_counters(character_id, fully_unescape)
        await interaction.response.send_message(
            f"Character '{character}' added successfully.\n\n{msg}", ephemeral=True
        )

    # --- Add character for fera ---
    @cog.add_group.command(
        name="character_fera",
        description="Add a Fera character (requires willpower, gnosis, rage, glory, honor, wisdom)",
    )
    async def add_character_fera(
        interaction: discord.Interaction,
        character: str,
        willpower: int,
        gnosis: int,
        rage: int,
        glory: int,
        honor: int,
        wisdom: int,
        honor_replacement: str = None,
        glory_replacement: str = None,
        wisdom_replacement: str = None,
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(
            interaction, character, user_id
        )
        if not character_id:
            return

        # Add base counters using add_predefined_counter
        for counter_type, value, label in [
            (PredefinedCounterEnum.willpower, willpower, "willpower"),
            (PredefinedCounterEnum.gnosis, gnosis, "gnosis"),
            (PredefinedCounterEnum.rage, rage, "rage"),
        ]:
            success, error = add_predefined_counter(
                character_id, counter_type.value, value
            )
            if not success:
                await interaction.response.send_message(
                    f"Failed to add {label} counter: {error}", ephemeral=True
                )
                return

        # Add renown counters with possible replacements
        for counter_type, value, label, override in [
            (PredefinedCounterEnum.glory, glory, "glory", glory_replacement),
            (PredefinedCounterEnum.honor, honor, "honor", honor_replacement),
            (PredefinedCounterEnum.wisdom, wisdom, "wisdom", wisdom_replacement),
        ]:
            success, error = add_predefined_counter(
                character_id, counter_type.value, value, None, override
            )
            if not success:
                await interaction.response.send_message(
                    f"Failed to add {label} counter: {error}", ephemeral=True
                )
                return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Generate and display the character's counters and health
        msg = display_character_counters(character_id, fully_unescape)
        await interaction.response.send_message(
            f"Character '{character}' added successfully.\n\n{msg}", ephemeral=True
        )

    def _generate_replacement_strings(
        glory_replacement, honor_replacement, wisdom_replacement
    ):
        """Generate replacement strings for the confirmation message."""
        replacements = ""
        if glory_replacement:
            replacements += f", glory_replacement: {glory_replacement}"
        if honor_replacement:
            replacements += f", honor_replacement: {honor_replacement}"
        if wisdom_replacement:
            replacements += f", wisdom_replacement: {wisdom_replacement}"
        return replacements

    @cog.add_group.command(
        name="counter", description="Add a predefined counter to a character"
    )
    @app_commands.autocomplete(
        character=character_name_autocomplete,
        counter_type=predefined_counter_type_autocomplete,
        # item_or_project_name autocomplete is not needed; it's a free text field
    )
    async def add_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter_type: str,
        value: int = None,
        comment: str = None,
        item_or_project_name: str = None,  # Renamed from name_override
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message(
                "Character not found for this user.", ephemeral=True
            )
            return

        # Handle Remove_When_Exhausted special case
        if counter_type == "Remove_When_Exhausted":
            if not item_or_project_name:
                await interaction.response.send_message(
                    "You must specify a counter name for Remove_When_Exhausted.",
                    ephemeral=True,
                )
                return
            from utils import add_counter

            success, error = add_counter(
                character_id,
                item_or_project_name,
                value if value is not None else 0,
                category="other",
                comment=comment,
                counter_type=CounterTypeEnum.single_number.value,  # Use the string value
                is_exhaustible=True,
            )
            if success:
                # Show updated display after adding
                from utils import display_character_counters, fully_unescape
                msg = display_character_counters(character_id, fully_unescape)
                await interaction.response.send_message(
                    f"Remove_When_Exhausted counter '{item_or_project_name}' added to character '{character}'.\n\n{msg}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    error or "Failed to add counter.", ephemeral=True
                )
            return

        # Handle Reset_Eligible special case
        if counter_type == "Reset_Eligible":
            if not item_or_project_name:
                await interaction.response.send_message(
                    "You must specify a counter name for Reset_Eligible.",
                    ephemeral=True,
                )
                return
            from utils import add_counter

            success, error = add_counter(
                character_id,
                item_or_project_name,
                value if value is not None else 0,
                category="other",
                comment=comment,
                counter_type=CounterTypeEnum.perm_is_maximum.value,  # Use the string value
                is_resettable=True,
            )
            if success:
                # Show updated display after adding
                from utils import display_character_counters, fully_unescape

                msg = display_character_counters(character_id, fully_unescape)
                await interaction.response.send_message(
                    f"Reset_Eligible counter '{item_or_project_name}' added to character '{character}'.\n\n{msg}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    error or "Failed to add counter.", ephemeral=True
                )
            return

        # Validate counter type
        try:
            counter_enum = PredefinedCounterEnum(counter_type)
        except ValueError:
            await interaction.response.send_message(
                "Invalid counter type selected.", ephemeral=True
            )
            return

        # Only require item_or_project_name for item_with_charges and project_roll
        if counter_enum in (
            PredefinedCounterEnum.item_with_charges,
            PredefinedCounterEnum.project_roll,
        ):
            if not item_or_project_name:
                await interaction.response.send_message(
                    "You must specify a counter name for this type.", ephemeral=True
                )
                return
            override_name = item_or_project_name
        elif counter_enum == PredefinedCounterEnum.willpower_fae:
            override_name = "willpower"
        else:
            override_name = None

        # Add the counter
        success, error = add_predefined_counter(
            character_id, counter_enum.value, value, comment, override_name
        )

        # Handle result and display character counters
        from utils import display_character_counters, fully_unescape

        msg = display_character_counters(character_id, fully_unescape)
        if success:
            await interaction.response.send_message(
                f"{counter_type.title()} counter added to character '{character}'.\n\n{msg}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{error or 'Failed to add counter.'}\n\n{msg}",
                ephemeral=True,
            )

    # --- Add health command ---
    @cog.add_group.command(
        name="health_tracker",
        description="Add a health tracker to a character (normal or chimerical)",
    )
    @app_commands.autocomplete(character=character_name_autocomplete)
    async def add_health_tracker_cmd(
        interaction: discord.Interaction, character: str, chimerical: bool = False
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message(
                "Character not found for this user.", ephemeral=True
            )
            return

        # Get character document
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if not char_doc:
            await interaction.response.send_message(
                "Character not found.", ephemeral=True
            )
            return

        health_list = char_doc.get("health", [])

        # Determine health type based on the chimerical flag
        health_type = (
            HealthTypeEnum.chimerical.value
            if chimerical
            else HealthTypeEnum.normal.value
        )

        # Check if the tracker already exists
        if any(h.get("health_type") == health_type for h in health_list):
            await interaction.response.send_message(
                f"A {health_type} health tracker already exists for this character.",
                ephemeral=True,
            )
            return

        # Add the health tracker
        health_obj = Health(health_type=health_type)
        health_list.append(health_obj.__dict__)
        CharacterRepository.update_one(
            {"_id": ObjectId(character_id)}, {"$set": {"health": health_list}}
        )

        await interaction.response.send_message(
            f"{health_type.capitalize()} health tracker added to character '{character}'.",
            ephemeral=True,
        )

    # --- Add custom counter ---
    @cog.add_group.command(
        name="customcounter", description="Add a custom counter to a character"
    )
    @app_commands.autocomplete(
        character=character_name_autocomplete,
        counter_type=counter_type_autocomplete,
        category=category_autocomplete,
    )
    async def add_custom_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter_name: str,
        counter_type: str,
        value: int,
        category: str = CategoryEnum.general.value,
        comment: str = None,
        force_unpretty: bool = False,
        is_resettable: bool = None,
        is_exhaustible: bool = None,
        set_temp_nonzero: bool = False,
    ):
        character = sanitize_string(character)
        counter_name = sanitize_string(counter_name)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message(
                "Character not found for this user.", ephemeral=True
            )
            return

        success, error = add_counter(
            character_id,
            counter_name,
            value,
            category=category,
            comment=comment,
            counter_type=counter_type,
            force_unpretty=force_unpretty,
            is_resettable=is_resettable,
            is_exhaustible=is_exhaustible,
        )
        if success:
            await interaction.response.send_message(
                f"Custom counter '{counter_name}' added to character '{character}'.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                error or "Failed to add counter.", ephemeral=True
            )


async def health_level_type_autocomplete(
    interaction: discord.Interaction, current: str
):
    """Autocomplete health level types from HealthLevelEnum."""
    return [
        app_commands.Choice(name=e.value, value=e.value)
        for e in HealthLevelEnum
        if current.lower() in e.value.lower()
    ]
