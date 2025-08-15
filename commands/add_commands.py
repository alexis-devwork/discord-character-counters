import discord
from discord import app_commands
from utils import (
    sanitize_string,
    add_user_character,
    get_character_id_by_user_and_name,
    add_counter,
    character_name_autocomplete,
    category_autocomplete,
    PredefinedCounterEnum,
    add_predefined_counter,
    CategoryEnum,
)
from utils import characters_collection
from health import Health, HealthTypeEnum
from bson import ObjectId
from .autocomplete import (
    predefined_counter_type_autocomplete,
    health_type_autocomplete
)

def register_add_commands(cog):
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

        # Save character
        success, error = add_user_character(user_id, character)
        if not success:
            await interaction.response.send_message(error, ephemeral=True)
            return

        character_id = get_character_id_by_user_and_name(user_id, character)
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower.value,
            willpower,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.mana.value,
            mana,
            ""
        )
        # Add normal health tracker (MongoDB version)
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_obj = Health(health_type=HealthTypeEnum.normal.value)
            health_list = char_doc.get("health", [])
            health_list.append(health_obj.__dict__)
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
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

        # Save character
        success, error = add_user_character(user_id, character)
        if not success:
            await interaction.response.send_message(error, ephemeral=True)
            return

        character_id = get_character_id_by_user_and_name(user_id, character)
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.blood_pool.value,
            blood_pool,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower.value,
            willpower,
            ""
        )
        # Add normal health tracker (MongoDB version)
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_obj = Health(health_type=HealthTypeEnum.normal.value)
            health_list = char_doc.get("health", [])
            health_list.append(health_obj.__dict__)
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
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
        success, error = add_user_character(user_id, character)
        if not success:
            await interaction.response.send_message(error, ephemeral=True)
            return

        character_id = get_character_id_by_user_and_name(user_id, character)
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower_fae.value,
            willpower_fae,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.glamour.value,
            glamour,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.nightmare.value,
            nightmare,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.banality.value,
            banality,
            ""
        )
        # Add normal and chimerical health trackers (MongoDB version)
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_list = char_doc.get("health", [])
            health_normal = Health(health_type=HealthTypeEnum.normal.value)
            health_chimerical = Health(health_type=HealthTypeEnum.chimerical.value)
            health_list.append(health_normal.__dict__)
            health_list.append(health_chimerical.__dict__)
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
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
        success, error = add_user_character(user_id, character)
        if not success:
            await interaction.response.send_message(error, ephemeral=True)
            return

        character_id = get_character_id_by_user_and_name(user_id, character)
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.willpower.value,
            willpower,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.gnosis.value,
            gnosis,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.rage.value,
            rage,
            ""
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.glory.value,
            glory,
            "",
            glory_replacement if glory_replacement else None
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.honor.value,
            honor,
            "",
            honor_replacement if honor_replacement else None
        )
        add_predefined_counter(
            character_id,
            PredefinedCounterEnum.wisdom.value,
            wisdom,
            "",
            wisdom_replacement if wisdom_replacement else None
        )
        # Add normal health tracker (MongoDB version)
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if char_doc:
            health_obj = Health(health_type=HealthTypeEnum.normal.value)
            health_list = char_doc.get("health", [])
            health_list.append(health_obj.__dict__)
            characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})
        splat_msg = (
            f" (splat: fera, willpower: {willpower}, gnosis: {gnosis}, rage: {rage}, "
            f"glory: {glory}, honor: {honor}, wisdom: {wisdom}"
            f"{', glory_replacement: ' + glory_replacement if glory_replacement else ''}"
            f"{', honor_replacement: ' + honor_replacement if honor_replacement else ''}"
            f"{', wisdom_replacement: ' + wisdom_replacement if wisdom_replacement else ''})"
        )
        await interaction.response.send_message(
            f"Character '{character}'{splat_msg} added for you.",
            ephemeral=True
        )

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

        try:
            counter_enum = PredefinedCounterEnum(counter_type)
        except ValueError:
            await interaction.response.send_message("Invalid counter type selected.", ephemeral=True)
            return

        # Require name_override for project_roll and item_with_charges
        if counter_enum in (PredefinedCounterEnum.project_roll, PredefinedCounterEnum.item_with_charges):
            if not name_override:
                await interaction.response.send_message("You must specify a counter name for this type.", ephemeral=True)
                return
            override_name = name_override
        else:
            # Use name_override for glory, honor, wisdom if provided
            override_name = None
            if counter_enum in (
                PredefinedCounterEnum.glory,
                PredefinedCounterEnum.honor,
                PredefinedCounterEnum.wisdom
            ) and name_override:
                override_name = name_override

        perm_value = value

        success, error = add_predefined_counter(character_id, counter_enum.value, perm_value, comment, override_name)
        if success:
            await interaction.response.send_message(
                f"{counter_type.title()} counter added to character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)

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

        try:
            ht_enum = HealthTypeEnum(health_type)
        except ValueError:
            await interaction.response.send_message("Invalid health type.", ephemeral=True)
            return

        # Convert character_id to ObjectId for MongoDB lookup
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        if not char_doc:
            await interaction.response.send_message("Character not found.", ephemeral=True)
            return

        health_list = char_doc.get("health", [])
        if any(h.get("health_type") == ht_enum.value for h in health_list):
            await interaction.response.send_message(f"A {health_type} health tracker already exists for this character.", ephemeral=True)
            return

        health_obj = Health(health_type=ht_enum.value)
        health_list.append(health_obj.__dict__)
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"health": health_list}})

        await interaction.response.send_message(
            f"Health tracker ({health_type}) added to character '{character}'.", ephemeral=True
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

        counter = sanitize_string(counter)
        category = sanitize_string(category)
        if comment:
            comment = sanitize_string(comment)

        success, error = add_counter(character_id, counter, temp, perm, category, comment)
        if success:
            await interaction.response.send_message(
                f"Counter '{counter}' added to character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)

