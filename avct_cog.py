import discord
from discord.ext import commands
from discord import app_commands
from config import MAX_FIELD_LENGTH
from utils import (
    sanitize_string,
    add_user_character,
    get_all_user_characters_for_user,
    add_counter,
    update_counter,
    set_counter_comment,
    get_counters_for_character,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    counter_name_autocomplete,
    category_autocomplete,
    remove_character,
    remove_counter,
    set_counter_category,
    CategoryEnum,
    fully_unescape,
    validate_length,
    rename_character,
    rename_counter,
    PredefinedCounterEnum,
    add_predefined_counter,
    SessionLocal,
    generate_counters_output,
    splat_autocomplete,  # Make sure this is imported
)
from counter import UserCharacter
from sqlalchemy.orm import joinedload  # <-- Add this import
from health import Health, HealthTypeEnum

class AvctCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.avct_group = discord.app_commands.Group(name="avct", description="AVCT commands")
        self.add_group = app_commands.Group(name="add", description="Add a character or counter")
        self.character_group = app_commands.Group(name="character", description="Character related commands")
        self.rename_group = app_commands.Group(name="rename", description="Rename a character or counter")
        self.remove_group = app_commands.Group(name="remove", description="Remove a character or counter")
        self.edit_group = app_commands.Group(name="edit", description="Edit or rename counter/category/comment")
        self.spend_group = app_commands.Group(name="spend", description="Spend from a counter")
        self.gain_group = app_commands.Group(name="gain", description="Gain to a counter")  # <-- new group
        self.register_commands()

    async def cog_load(self):
        self.avct_group.add_command(self.character_group)
        self.avct_group.add_command(self.add_group)
        self.avct_group.add_command(self.rename_group)
        self.avct_group.add_command(self.remove_group)
        self.avct_group.add_command(self.edit_group)
        self.avct_group.add_command(self.spend_group)
        self.avct_group.add_command(self.gain_group)  # <-- add new group to avct
        self.bot.tree.add_command(self.avct_group)

    def register_commands(self):
        # --- Add character for sorc ---
        @self.add_group.command(name="character_sorc", description="Add a Sorcerer character (requires willpower and mana)")
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
            splat_msg = f" (splat: sorc, willpower: {willpower}, mana: {mana})"
            await interaction.response.send_message(
                f"Character '{character}'{splat_msg} added for you.",
                ephemeral=True
            )

        # --- Add character for vampire ---
        @self.add_group.command(name="character_vampire", description="Add a Vampire character (requires blood_pool and willpower)")
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
            splat_msg = f" (splat: vampire, blood_pool: {blood_pool}, willpower: {willpower})"
            await interaction.response.send_message(
                f"Character '{character}'{splat_msg} added for you.",
                ephemeral=True
            )

        # --- Add character for changeling ---
        @self.add_group.command(
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
            splat_msg = (
                f" (splat: changeling, willpower_fae: {willpower_fae}, glamour: {glamour}, "
                f"nightmare: {nightmare}, banality: {banality})"
            )
            await interaction.response.send_message(
                f"Character '{character}'{splat_msg} added for you.",
                ephemeral=True
            )

        # --- Add character for fera ---
        @self.add_group.command(
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

        async def predefined_counter_type_autocomplete(interaction: discord.Interaction, current: str):
            return [
                discord.app_commands.Choice(name=ct.value.title(), value=ct.value)
                for ct in PredefinedCounterEnum
                if current.lower() in ct.value.lower()
            ][:25]

        @self.add_group.command(name="counter", description="Add a predefined counter to a character")
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

        # --- Character commands ---
        @self.character_group.command(name="list", description="List your characters")
        async def list_characters(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            entries = get_all_user_characters_for_user(user_id)
            if not entries:
                await interaction.response.send_message("No characters found.", ephemeral=True)
                return
            msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
            await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

        @self.character_group.command(name="counters", description="List counters for a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete)
        async def counters(interaction: discord.Interaction, character: str):
            user_id = str(interaction.user.id)
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

            msg = generate_counters_output(counters, fully_unescape)

            # Add health trackers to the bottom of the output
            session = SessionLocal()
            health_entries = session.query(Health).filter_by(character_id=character_id).all()
            if health_entries:
                msg += "\n\n**Health Trackers:**"
                for h in health_entries:
                    msg += f"\nHealth ({h.health_type.value}):\n{h.display()}"
            session.close()

            await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

        async def counter_name_autocomplete_for_character(interaction: discord.Interaction, current: str):
            user_id = str(interaction.user.id)
            character = interaction.namespace.character
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                return []
            counters = get_counters_for_character(character_id)
            filtered = [
                c.counter for c in counters
                if current.lower() in c.counter.lower()
            ]
            unique_counters = list(dict.fromkeys(filtered))
            return [
                discord.app_commands.Choice(name=name, value=name)
                for name in unique_counters
            ][:25]

        @self.character_group.command(name="temp", description="Set temp value for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def temp(interaction: discord.Interaction, character: str, counter: str, new_value: int):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            # Set temp directly to new_value
            session = SessionLocal()
            counter_obj = session.query(get_counters_for_character(character_id)[0].__class__).filter_by(character_id=character_id, counter=counter).first()
            if not counter_obj:
                session.close()
                await interaction.response.send_message("Counter not found.", ephemeral=True)
                return
            # For perm_is_maximum types, do not allow temp above perm or below zero
            if counter_obj.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                if new_value > counter_obj.perm:
                    counter_obj.temp = counter_obj.perm
                elif new_value < 0:
                    session.close()
                    await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                    return
                else:
                    counter_obj.temp = new_value
            else:
                if new_value < 0:
                    session.close()
                    await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                    return
                counter_obj.temp = new_value
            session.commit()
            session.close()
            counters = get_counters_for_character(character_id)
            msg = generate_counters_output(counters, fully_unescape)
            await interaction.response.send_message(
                f"Temp for counter '{counter}' on character '{character}' set to {new_value}.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True)

        @self.character_group.command(name="perm", description="Set perm value for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def perm(interaction: discord.Interaction, character: str, counter: str, new_value: int):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            # Set perm directly to new_value
            session = SessionLocal()
            counter_obj = session.query(get_counters_for_character(character_id)[0].__class__).filter_by(character_id=character_id, counter=counter).first()
            if not counter_obj:
                session.close()
                await interaction.response.send_message("Counter not found.", ephemeral=True)
                return
            if new_value < 0:
                session.close()
                await interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
                return
            counter_obj.perm = new_value
            # For perm_is_maximum types, adjust temp if perm is lowered below temp
            if counter_obj.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                if counter_obj.temp > counter_obj.perm:
                    counter_obj.temp = counter_obj.perm
            session.commit()
            session.close()
            counters = get_counters_for_character(character_id)
            msg = generate_counters_output(counters, fully_unescape)
            await interaction.response.send_message(
                f"Perm for counter '{counter}' on character '{character}' set to {new_value}.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True)

        async def bedlam_counter_autocomplete(interaction: discord.Interaction, current: str):
            user_id = str(interaction.user.id)
            character = interaction.namespace.character
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                return []
            counters = get_counters_for_character(character_id)
            filtered = [
                c.counter for c in counters
                if c.counter_type == "perm_is_maximum_bedlam" and current.lower() in c.counter.lower()
            ]
            unique_counters = list(dict.fromkeys(filtered))
            return [
                discord.app_commands.Choice(name=name, value=name)
                for name in unique_counters
            ][:25]

        @self.character_group.command(name="bedlam", description="Set bedlam for a counter (only perm_is_maximum_bedlam counters)")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=bedlam_counter_autocomplete)
        async def bedlam(interaction: discord.Interaction, character: str, counter: str, new_value: int):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            counters = get_counters_for_character(character_id)
            target = next((c for c in counters if c.counter == counter and c.counter_type == "perm_is_maximum_bedlam"), None)
            if not target:
                await interaction.response.send_message("Counter not found or not of type perm_is_maximum_bedlam.", ephemeral=True)
                return
            # Do not allow bedlam below zero or above perm
            if new_value < 0:
                await interaction.response.send_message("Bedlam cannot be negative.", ephemeral=True)
                return
            if new_value > target.perm:
                await interaction.response.send_message(f"Bedlam cannot exceed perm ({target.perm}).", ephemeral=True)
                return
            session = SessionLocal()
            db_counter = session.query(type(target)).filter_by(id=target.id).first()
            db_counter.bedlam = new_value
            session.commit()
            session.close()
            counters = get_counters_for_character(character_id)
            msg = generate_counters_output(counters, fully_unescape)
            await interaction.response.send_message(
                f"Bedlam for counter '{counter}' on character '{character}' set to {new_value}.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True)

        @self.spend_group.command(name="counter", description="Spend (decrement by points) from a counter for a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def spend_counter(interaction: discord.Interaction, character: str, counter: str, points: int = 1):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = update_counter(character_id, counter, "temp", -points)
            counters = get_counters_for_character(character_id)
            if success:
                msg = generate_counters_output(counters, fully_unescape)
                await interaction.response.send_message(
                    f"Spent {points} from counter '{counter}' on character '{character}'.\n"
                    f"Counters for character '{character}':\n{msg}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

        @self.gain_group.command(name="counter", description="Gain (increment by points) to a counter for a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def gain_counter(interaction: discord.Interaction, character: str, counter: str, points: int = 1):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = update_counter(character_id, counter, "temp", points)
            counters = get_counters_for_character(character_id)
            if success:
                msg = generate_counters_output(counters, fully_unescape)
                await interaction.response.send_message(
                    f"Gained {points} to counter '{counter}' on character '{character}'.\n"
                    f"Counters for character '{character}':\n{msg}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

        @self.add_group.command(name="customcounter", description="Add a custom counter to a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, category=category_autocomplete)
        async def add_custom_counter(
            interaction: discord.Interaction,
            character: str,
            counter: str,
            temp: int,
            perm: int,
            category: str = None,
            comment: str = None
        ):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            # Default category to general if not provided
            if not category:
                category = CategoryEnum.general.value
            success, error = add_counter(character_id, counter, temp, perm, category, comment)
            if success:
                await interaction.response.send_message(
                    f"Custom counter '{counter}' added to character '{character}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to add custom counter.", ephemeral=True)

        @self.remove_group.command(name="character", description="Remove a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete)
        async def remove_character_cmd(interaction: discord.Interaction, character: str):
            user_id = str(interaction.user.id)
            success, error, details = remove_character(user_id, character)
            if success:
                await interaction.response.send_message(
                    f"Character '{character}' removed.\nCounters removed:\n{details}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to remove character.", ephemeral=True)

        @self.remove_group.command(name="counter", description="Remove a counter from a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def remove_counter_cmd(interaction: discord.Interaction, character: str, counter: str):
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error, details = remove_counter(character_id, counter)
            if success:
                await interaction.response.send_message(
                    f"Counter '{counter}' removed from character '{character}'.\nCurrent counters:\n{details}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to remove counter.", ephemeral=True)

        @self.rename_group.command(name="character", description="Rename a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete)
        async def rename_character_cmd(interaction: discord.Interaction, character: str, new_name: str):
            user_id = str(interaction.user.id)
            success, error = rename_character(user_id, character, new_name)
            if success:
                await interaction.response.send_message(
                    f"Character '{character}' renamed to '{new_name}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to rename character.", ephemeral=True)

        @self.rename_group.command(name="counter", description="Rename a counter for a character")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def rename_counter_cmd(interaction: discord.Interaction, character: str, counter: str, new_name: str):
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = rename_counter(character_id, counter, new_name)
            if success:
                await interaction.response.send_message(
                    f"Counter '{counter}' renamed to '{new_name}' for character '{character}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to rename counter.", ephemeral=True)

        @self.edit_group.command(name="counter", description="Set temp or perm for a counter")
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
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            if field not in ["temp", "perm"]:
                await interaction.response.send_message("Field must be 'temp' or 'perm'.", ephemeral=True)
                return
            # Validate value
            if not isinstance(value, int) or value < 0:
                await interaction.response.send_message("Value must be a non-negative integer.", ephemeral=True)
                return
            session = SessionLocal()
            counter_obj = session.query(get_counters_for_character(character_id)[0].__class__).filter_by(character_id=character_id, counter=counter).first()
            if not counter_obj:
                session.close()
                await interaction.response.send_message("Counter not found.", ephemeral=True)
                return
            if field == "temp":
                # For perm_is_maximum types, do not allow temp above perm or below zero
                if counter_obj.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                    if value > counter_obj.perm:
                        counter_obj.temp = counter_obj.perm
                    elif value < 0:
                        session.close()
                        await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                        return
                    else:
                        counter_obj.temp = value
                else:
                    if value < 0:
                        session.close()
                        await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                        return
                    counter_obj.temp = value
            elif field == "perm":
                if value < 0:
                    session.close()
                    await interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
                    return
                counter_obj.perm = value
                # For perm_is_maximum types, adjust temp if perm is lowered below temp
                if counter_obj.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                    if counter_obj.temp > counter_obj.perm:
                        counter_obj.temp = counter_obj.perm
            session.commit()
            session.close()
            counters = get_counters_for_character(character_id)
            msg = generate_counters_output(counters, fully_unescape)
            await interaction.response.send_message(
                f"Set {field} for counter '{counter}' on character '{character}' to {value}.\n"
                f"Counters for character '{character}':\n{msg}", ephemeral=True)

        @self.edit_group.command(name="comment", description="Set comment for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def set_comment_cmd(
            interaction: discord.Interaction,
            character: str,
            counter: str,
            comment: str
        ):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            # Validate comment length
            from config import MAX_COMMENT_LENGTH
            if not validate_length("comment", comment, MAX_COMMENT_LENGTH):
                await interaction.response.send_message(
                    f"Comment must be at most {MAX_COMMENT_LENGTH} characters.", ephemeral=True)
                return
            success, error = set_counter_comment(character_id, counter, comment)
            if success:
                await interaction.response.send_message(
                    f"Comment for counter '{counter}' on character '{character}' set.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

        @self.edit_group.command(name="category", description="Set category for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character, category=category_autocomplete)
        async def set_category_cmd(
            interaction: discord.Interaction,
            character: str,
            counter: str,
            category: str
        ):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            # Validate category length
            from config import MAX_FIELD_LENGTH
            if not validate_length("category", category, MAX_FIELD_LENGTH):
                await interaction.response.send_message(
                    f"Category must be at most {MAX_FIELD_LENGTH} characters.", ephemeral=True)
                return
            success, error = set_counter_category(character_id, counter, category)
            if success:
                await interaction.response.send_message(
                    f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

        @self.avct_group.command(name="debug", description="Show all properties of all counters for all characters for the current user (visible to everyone)")
        async def debug(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            session = SessionLocal()
            chars = session.query(UserCharacter).options(joinedload(UserCharacter.counters)).filter_by(user=user_id).all()
            debug_lines = []
            for char in chars:
                debug_lines.append(f"Character: {char.character} (ID: {char.id})")
                for c in char.counters:
                    debug_lines.append(
                        f"  Counter: {c.counter} | temp: {c.temp} | perm: {c.perm} | type: {c.counter_type} | category: {c.category} | comment: {c.comment} | bedlam: {getattr(c, 'bedlam', None)}"
                    )
                # Add health details for this character
                health_entries = session.query(Health).filter_by(character_id=char.id).all()
                for h in health_entries:
                    debug_lines.append(f"  Health ({h.health_type.value}):")
                    # Raw values
                    import json
                    raw_levels = json.loads(h.health_levels)
                    debug_lines.append(f"    Raw health_levels: {raw_levels}")
                    raw_damage = json.loads(h.damage)
                    debug_lines.append(f"    Raw damage: {raw_damage}")
                    # Formatted display
                    debug_lines.append(h.display())
            session.close()
            debug_text = "\n".join(debug_lines) or "No data found."
            # Discord message limit is 2000 characters
            if len(debug_text) > 2000:
                chunks = [debug_text[i:i+1990] for i in range(0, len(debug_text), 1990)]
                for idx, chunk in enumerate(chunks):
                    if idx == 0:
                        await interaction.response.send_message(chunk, ephemeral=False)
                    else:
                        await interaction.followup.send(chunk, ephemeral=False)
            else:
                await interaction.response.send_message(debug_text, ephemeral=False)

        async def health_type_autocomplete(interaction: discord.Interaction, current: str):
            return [
                discord.app_commands.Choice(name=ht.value, value=ht.value)
                for ht in HealthTypeEnum
                if current.lower() in ht.value.lower()
            ][:25]

        async def damage_type_autocomplete(interaction: discord.Interaction, current: str):
            from health import DamageEnum
            return [
                discord.app_commands.Choice(name=dt.value, value=dt.value)
                for dt in DamageEnum
                if current.lower() in dt.value.lower()
            ][:25]

        # Remove health tracker
        @self.remove_group.command(name="health", description="Remove a health tracker from a character by type")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete)
        async def remove_health(
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
            session = SessionLocal()
            from health import HealthTypeEnum
            try:
                ht_enum = HealthTypeEnum(health_type)
            except ValueError:
                session.close()
                await interaction.response.send_message("Invalid health type.", ephemeral=True)
                return
            health_obj = session.query(Health).filter_by(character_id=character_id, health_type=ht_enum).first()
            if not health_obj:
                session.close()
                await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
                return
            session.delete(health_obj)
            session.commit()
            session.close()
            await interaction.response.send_message(
                f"Health tracker ({health_type}) removed from character '{character}'.", ephemeral=True
            )

        # Add damage to health tracker
        @self.avct_group.command(name="damage", description="Add damage to a health tracker")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete, damage_type=damage_type_autocomplete)
        async def damage(
            interaction: discord.Interaction,
            character: str,
            health_type: str,
            damage_type: str,
            levels: int
        ):
            character = sanitize_string(character)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            session = SessionLocal()
            from health import HealthTypeEnum, DamageEnum
            try:
                ht_enum = HealthTypeEnum(health_type)
                dt_enum = DamageEnum(damage_type)
            except ValueError:
                session.close()
                await interaction.response.send_message("Invalid health or damage type.", ephemeral=True)
                return
            health_obj = session.query(Health).filter_by(character_id=character_id, health_type=ht_enum).first()
            if not health_obj:
                session.close()
                await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
                return
            # Call add_damage while the instance is still attached to the session
            msg = health_obj.add_damage(levels, dt_enum)
            session.add(health_obj)  # Ensure changes are tracked
            session.commit()
            # Refresh the instance to get updated values
            session.refresh(health_obj)
            output = health_obj.display()
            session.close()
            if msg:
                await interaction.response.send_message(f"{msg}\n{output}", ephemeral=True)
            else:
                await interaction.response.send_message(output, ephemeral=True)

        # Heal damage from health tracker
        @self.avct_group.command(name="heal", description="Heal damage from a health tracker")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, health_type=health_type_autocomplete)
        async def heal(
            interaction: discord.Interaction,
            character: str,
            health_type: str,
            levels: int
        ):
            character = sanitize_string(character)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            session = SessionLocal()
            from health import HealthTypeEnum
            try:
                ht_enum = HealthTypeEnum(health_type)
            except ValueError:
                session.close()
                await interaction.response.send_message("Invalid health type.", ephemeral=True)
                return
            health_obj = session.query(Health).filter_by(character_id=character_id, health_type=ht_enum).first()
            if not health_obj:
                session.close()
                await interaction.response.send_message("Health tracker not found for this character and type.", ephemeral=True)
                return
            # Call remove_damage while the instance is still attached to the session
            health_obj.remove_damage(levels)
            session.add(health_obj)  # Ensure changes are tracked
            session.commit()
            session.refresh(health_obj)  # Refresh to get updated values
            output = health_obj.display()
            session.close()
            await interaction.response.send_message(output, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AvctCog(bot))
