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

        @self.character_group.command(name="temp", description="Change temp value for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def temp(interaction: discord.Interaction, character: str, counter: str, delta: int):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = update_counter(character_id, counter, "temp", delta)
            counters = get_counters_for_character(character_id)
            if success:
                msg = generate_counters_output(counters, fully_unescape)
                await interaction.response.send_message(
                    f"Temp for counter '{counter}' on character '{character}' changed by {delta}.\n"
                    f"Counters for character '{character}':\n{msg}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

        @self.character_group.command(name="perm", description="Change perm value for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
        async def perm(interaction: discord.Interaction, character: str, counter: str, delta: int):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = update_counter(character_id, counter, "perm", delta)
            counters = get_counters_for_character(character_id)
            if success:
                msg = generate_counters_output(counters, fully_unescape)
                await interaction.response.send_message(
                    f"Perm for counter '{counter}' on character '{character}' changed by {delta}.\n"
                    f"Counters for character '{character}':\n{msg}", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

        # --- Rename commands ---
        @self.rename_group.command(name="character", description="Rename a character (only if new name does not exist for you)")
        @app_commands.autocomplete(old_name=character_name_autocomplete)
        async def rename_character_cmd(interaction: discord.Interaction, old_name: str, new_name: str):
            new_name = sanitize_string(new_name)
            user_id = str(interaction.user.id)
            success, error = rename_character(user_id, old_name, new_name)
            if success:
                await interaction.response.send_message(f"Character '{old_name}' renamed to '{new_name}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        @self.rename_group.command(name="counter", description="Rename a counter (only if new name does not exist for this character)")
        @app_commands.autocomplete(character=character_name_autocomplete, old_name=counter_name_autocomplete)
        async def rename_counter_cmd(interaction: discord.Interaction, character: str, old_name: str, new_name: str):
            new_name = sanitize_string(new_name)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = rename_counter(character_id, old_name, new_name)
            if success:
                await interaction.response.send_message(f"Counter '{old_name}' renamed to '{new_name}' for character '{character}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        # --- Remove commands ---
        @self.remove_group.command(name="character", description="Remove a character and show its details to everyone")
        @app_commands.autocomplete(character=character_name_autocomplete)
        async def remove_character_cmd(interaction: discord.Interaction, character: str):
            user_id = str(interaction.user.id)
            success, error, details = remove_character(user_id, character)
            if success:
                msg = f"Character '{character}' was removed.\nDetails before removal:\n{details if details else 'No counters.'}"
                await interaction.response.send_message(msg, ephemeral=False)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        @self.remove_group.command(name="counter", description="Remove a counter and show character state to everyone")
        @app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
        async def remove_counter_cmd(interaction: discord.Interaction, character: str, counter: str):
            character = sanitize_string(character)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error, details = remove_counter(character_id, counter)
            if success:
                msg = (
                    f"Counter '{counter}' was removed from character '{character}'.\n"
                    f"Character state before removal:\n{details if details else 'No counters.'}"
                )
                await interaction.response.send_message(msg, ephemeral=False)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        # --- Edit commands ---
        @self.edit_group.command(name="setcountercategory", description="Set the category for an existing counter")
        @app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete, category=category_autocomplete)
        async def setcountercategory_cmd(
            interaction: discord.Interaction,
            character: str,
            counter: str,
            category: str
        ):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            category = sanitize_string(category)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            if category not in [c.value for c in CategoryEnum]:
                await interaction.response.send_message("Invalid category selected.", ephemeral=True)
                return
            success, error = set_counter_category(character_id, counter, category)
            if success:
                await interaction.response.send_message(
                    f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

        @self.edit_group.command(name="setcountercomment", description="Set the comment for an existing counter")
        @app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
        async def setcountercomment_cmd(
            interaction: discord.Interaction,
            character: str,
            counter: str,
            comment: str
        ):
            character = sanitize_string(character)
            counter = sanitize_string(counter)
            comment = sanitize_string(comment)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = set_counter_comment(character_id, counter, comment)
            if success:
                await interaction.response.send_message(
                    f"Comment for counter '{counter}' on character '{character}' set to '{comment}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

        @self.edit_group.command(name="renamecharacter", description="Rename a character (only if new name does not exist for you)")
        @app_commands.autocomplete(old_name=character_name_autocomplete)
        async def edit_rename_character_cmd(interaction: discord.Interaction, old_name: str, new_name: str):
            user_id = str(interaction.user.id)
            # old_name is already sanitized from autocomplete, only validate length

            if not validate_length("character", old_name, MAX_FIELD_LENGTH):
                await interaction.response.send_message(f"Old name must be at most {MAX_FIELD_LENGTH} characters.", ephemeral=True)
                return
            new_name_sanitized = sanitize_string(new_name)
            success, error = rename_character(user_id, old_name, new_name_sanitized)
            if success:
                await interaction.response.send_message(f"Character '{old_name}' renamed to '{new_name}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        @self.edit_group.command(name="renamecounter", description="Rename a counter (only if new name does not exist for this character)")
        @app_commands.autocomplete(character=character_name_autocomplete, old_name=counter_name_autocomplete)
        async def edit_rename_counter_cmd(interaction: discord.Interaction, character: str, old_name: str, new_name: str):
            new_name = sanitize_string(new_name)
            user_id = str(interaction.user.id)
            character_id = get_character_id_by_user_and_name(user_id, character)
            if character_id is None:
                await interaction.response.send_message("Character not found for this user.", ephemeral=True)
                return
            success, error = rename_counter(character_id, old_name, new_name)
            if success:
                await interaction.response.send_message(f"Counter '{old_name}' renamed to '{new_name}' for character '{character}'.", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

        @self.avct_group.command(name="debug", description="Show all properties of all counters for all your characters (visible to everyone)")
        async def debug(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            entries = get_all_user_characters_for_user(user_id)
            if not entries:
                await interaction.response.send_message("No characters found.", ephemeral=False)
                return
            msg_lines = []
            for char in entries:
                msg_lines.append(f"Character: {char.character} (ID: {char.id})")
                counters = char.counters
                if not counters:
                    msg_lines.append("  No counters.")
                else:
                    for c in counters:
                        props = [
                            f"counter={c.counter}",
                            f"temp={c.temp}",
                            f"perm={c.perm}",
                            f"category={c.category}",
                            f"comment={c.comment}",
                            f"bedlam={c.bedlam}",
                            f"counter_type={c.counter_type}",
                            f"display={c.generate_display(fully_unescape)}"
                        ]
                        msg_lines.append("  " + ", ".join(props))
            msg = "\n".join(msg_lines)
            # Use followup to avoid "Unknown interaction" if response already sent
            if interaction.response.is_done():
                await interaction.followup.send(f"Debug info for all your characters and counters:\n{msg}", ephemeral=False)
            else:
                await interaction.response.send_message(f"Debug info for all your characters and counters:\n{msg}", ephemeral=False)

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

        @self.character_group.command(name="bedlam", description="Increment or decrement bedlam for a counter (only perm_is_maximum_bedlam counters)")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=bedlam_counter_autocomplete)
        async def bedlam(interaction: discord.Interaction, character: str, counter: str, delta: int):
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
            new_bedlam = (target.bedlam or 0) + delta
            # Do not allow bedlam below zero or above perm
            if new_bedlam < 0:
                await interaction.response.send_message("Bedlam cannot be negative.", ephemeral=True)
                return
            if new_bedlam > target.perm:
                await interaction.response.send_message(f"Bedlam cannot exceed perm ({target.perm}).", ephemeral=True)
                return
            session = SessionLocal()
            db_counter = session.query(type(target)).filter_by(id=target.id).first()
            db_counter.bedlam = new_bedlam
            session.commit()
            session.close()
            await interaction.response.send_message(
                f"Bedlam for counter '{counter}' on character '{character}' changed by {delta}. New value: {new_bedlam}",
                ephemeral=True
            )

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

async def setup(bot):
    await bot.add_cog(AvctCog(bot))
