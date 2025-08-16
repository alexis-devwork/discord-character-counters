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
)
from utils import characters_collection, CharacterRepository
from health import Health, HealthTypeEnum
from bson import ObjectId
from .autocomplete import (
    character_name_autocomplete,
    category_autocomplete,
    predefined_counter_type_autocomplete,
    health_type_autocomplete
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
            CharacterRepository.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
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
            CharacterRepository.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
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
    @cog.add_group.command(name="character_sorc", description="Add a Sorcerer character (requires willpower and mana)")
    async def add_character_sorc(
        interaction: discord.Interaction,
        character: str,
        willpower: int,
        mana: int
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(interaction, character, user_id)
        if not character_id:
            return

        # Add counters
        success, error = add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower.value,
            willpower,
            ""
        )
        if not success:
            await interaction.response.send_message(f"Failed to add willpower counter: {error}", ephemeral=True)
            return

        success, error = add_predefined_counter(
            character_id,
            PredefinedCounterEnum.mana.value,
            mana,
            ""
        )
        if not success:
            await interaction.response.send_message(f"Failed to add mana counter: {error}", ephemeral=True)
            return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Send confirmation
        splat_msg = f" (splat: sorc, willpower: {willpower}, mana: {mana})"
        await interaction.response.send_message(
            f"Character '{character}'{splat_msg} added for you.",
            ephemeral=True
        )

    # --- Add character for vampire ---
    @cog.add_group.command(name="character_vampire", description="Add a Vampire character (requires blood_pool and willpower)")
    async def add_character_vampire(
        interaction: discord.Interaction,
        character: str,
        blood_pool: int,
        willpower: int
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(interaction, character, user_id)
        if not character_id:
            return

        # Add counters
        success, error = add_predefined_counter(
            character_id,
            PredefinedCounterEnum.blood_pool.value,
            blood_pool,
            ""
        )
        if not success:
            await interaction.response.send_message(f"Failed to add blood_pool counter: {error}", ephemeral=True)
            return

        success, error = add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower.value,
            willpower,
            ""
        )
        if not success:
            await interaction.response.send_message(f"Failed to add willpower counter: {error}", ephemeral=True)
            return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Send confirmation
        splat_msg = f" (splat: vampire, blood_pool: {blood_pool}, willpower: {willpower})"
        await interaction.response.send_message(
            f"Character '{character}'{splat_msg} added for you.",
            ephemeral=True
        )

    # --- Add character for changeling ---
    @cog.add_group.command(
        name="character_changeling",
        description="Add a Changeling character (requires willpower_fae, glamour, nightmare, banality)"
    )
    async def add_character_changeling(
        interaction: discord.Interaction,
        character: str,
        willpower_fae: int,
        glamour: int,
        nightmare: int,
        banality: int
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(interaction, character, user_id)
        if not character_id:
            return

        # Add counters
        for enum_val, val, label in [
            (PredefinedCounterEnum.willpower_fae.value, willpower_fae, "willpower_fae"),
            (PredefinedCounterEnum.glamour.value, glamour, "glamour"),
            (PredefinedCounterEnum.nightmare.value, nightmare, "nightmare"),
            (PredefinedCounterEnum.banality.value, banality, "banality"),
        ]:
            success, error = add_predefined_counter(character_id, enum_val, val, "")
            if not success:
                await interaction.response.send_message(f"Failed to add {label} counter: {error}", ephemeral=True)
                return

        # Add health trackers
        _add_multiple_health_trackers(
            character_id,
            [HealthTypeEnum.normal.value, HealthTypeEnum.chimerical.value]
        )

        # Send confirmation
        splat_msg = (
            f" (splat: changeling, willpower_fae: {willpower_fae}, glamour: {glamour}, "
            f"nightmare: {nightmare}, banality: {banality})"
        )
        await interaction.response.send_message(
            f"Character '{character}'{splat_msg} added for you.",
            ephemeral=True
        )

    # --- Add character for fera ---
    @cog.add_group.command(
        name="character_fera",
        description="Add a Fera character (requires willpower, gnosis, rage, glory, honor, wisdom)"
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
        wisdom_replacement: str = None
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)

        # Create character
        character_id = await _process_character_creation(interaction, character, user_id)
        if not character_id:
            return

        # Add base counters
        for enum_val, val, label in [
            (PredefinedCounterEnum.willpower.value, willpower, "willpower"),
            (PredefinedCounterEnum.gnosis.value, gnosis, "gnosis"),
            (PredefinedCounterEnum.rage.value, rage, "rage"),
        ]:
            success, error = add_predefined_counter(character_id, enum_val, val, "")
            if not success:
                await interaction.response.send_message(f"Failed to add {label} counter: {error}", ephemeral=True)
                return

        # Add renown counters with possible replacements
        for enum_val, val, label, override in [
            (PredefinedCounterEnum.glory.value, glory, "glory", glory_replacement),
            (PredefinedCounterEnum.honor.value, honor, "honor", honor_replacement),
            (PredefinedCounterEnum.wisdom.value, wisdom, "wisdom", wisdom_replacement),
        ]:
            success, error = add_predefined_counter(character_id, enum_val, val, "", _get_replacement_value(override))
            if not success:
                await interaction.response.send_message(f"Failed to add {label} counter: {error}", ephemeral=True)
                return

        # Add health tracker
        _add_health_tracker(character_id, HealthTypeEnum.normal.value)

        # Generate replacement strings for display
        replacements = _generate_replacement_strings(
            glory_replacement, honor_replacement, wisdom_replacement
        )

        # Send confirmation
        splat_msg = (
            f" (splat: fera, willpower: {willpower}, gnosis: {gnosis}, rage: {rage}, "
            f"glory: {glory}, honor: {honor}, wisdom: {wisdom}{replacements})"
        )
        await interaction.response.send_message(
            f"Character '{character}'{splat_msg} added for you.",
            ephemeral=True
        )

    def _generate_replacement_strings(glory_replacement, honor_replacement, wisdom_replacement):
        """Generate replacement strings for the confirmation message."""
        replacements = ""
        if glory_replacement:
            replacements += f", glory_replacement: {glory_replacement}"
        if honor_replacement:
            replacements += f", honor_replacement: {honor_replacement}"
        if wisdom_replacement:
            replacements += f", wisdom_replacement: {wisdom_replacement}"
        return replacements

    @cog.add_group.command(name="counter", description="Add a predefined counter to a character")
    @app_commands.autocomplete(character=character_name_autocomplete, counter_type=predefined_counter_type_autocomplete)
    async def add_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter_type: str,
        value: int = None,
        comment: str = None,
        name_override: str = None  # Used for all override cases, required for project_roll and item_with_charges
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return

        # Validate counter type
        try:
            counter_enum = PredefinedCounterEnum(counter_type)
        except ValueError:
            await interaction.response.send_message("Invalid counter type selected.", ephemeral=True)
            return

        # Determine override name
        override_name = _determine_override_name(counter_enum, name_override)
        if override_name == "REQUIRED_BUT_MISSING":
            await interaction.response.send_message("You must specify a counter name for this type.", ephemeral=True)
            return

        # Add the counter
        success, error = add_predefined_counter(character_id, counter_enum.value, value, comment, override_name)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"{counter_type.title()} counter added to character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)

    def _determine_override_name(counter_enum, name_override):
        """Determine the override name for a counter based on its type."""
        # Require name_override for project_roll and item_with_charges
        if counter_enum in (PredefinedCounterEnum.project_roll, PredefinedCounterEnum.item_with_charges):
            if not name_override:
                return "REQUIRED_BUT_MISSING"
            return name_override

        # Use name_override for glory, honor, wisdom if provided
        if counter_enum in (
            PredefinedCounterEnum.glory,
            PredefinedCounterEnum.honor,
            PredefinedCounterEnum.wisdom
        ) and name_override:
            return name_override

        return None

    # --- Add health command ---
    @cog.add_group.command(name="health", description="Add a health tracker to a character")
    @app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete)
    async def add_health_cmd(
        interaction: discord.Interaction,
        character: str,
        health_type: str
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return

        # Validate health type
        try:
            ht_enum = HealthTypeEnum(health_type)
        except ValueError:
            await interaction.response.send_message("Invalid health type.", ephemeral=True)
            return

        # Get character document
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if not char_doc:
            await interaction.response.send_message("Character not found.", ephemeral=True)
            return

        # Check if health tracker already exists
        health_list = char_doc.get("health", [])
        if _health_tracker_exists(health_list, ht_enum.value):
            await interaction.response.send_message(
                f"A {health_type} health tracker already exists for this character.",
                ephemeral=True
            )
            return

        # Add health tracker
        _add_health_tracker_to_list(health_list, ht_enum.value, character_id)

        # Send confirmation
        await interaction.response.send_message(
            f"Health tracker ({health_type}) added to character '{character}'.",
            ephemeral=True
        )

    def _health_tracker_exists(health_list, health_type):
        """Check if a health tracker of the given type already exists."""
        return any(h.get("health_type") == health_type for h in health_list)

    def _add_health_tracker_to_list(health_list, health_type, character_id):
        """Add a health tracker to the health list and update the database."""
        health_obj = Health(health_type=health_type)
        health_list.append(health_obj.__dict__)
        CharacterRepository.update_one(
            {"_id": ObjectId(character_id)},
            {"$set": {"health": health_list}}
        )

    # --- Add custom counter ---
    @cog.add_group.command(name="customcounter", description="Add a custom counter to a character")
    @app_commands.autocomplete(character=character_name_autocomplete, category=category_autocomplete)
    async def add_customcounter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        temp: int,
        perm: int,
        category: str = CategoryEnum.general.value,
        comment: str = None
    ):
        character = sanitize_string(character)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return

        # Sanitize inputs
        counter = sanitize_string(counter)
        category = sanitize_string(category)
        if comment:
            comment = sanitize_string(comment)

        # Add the counter
        success, error = add_counter(character_id, counter, temp, perm, category, comment)

        # Handle result
        if success:
            await interaction.response.send_message(
                f"Counter '{counter}' added to character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)
