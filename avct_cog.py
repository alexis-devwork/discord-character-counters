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
)

class AvctCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.avct_group = discord.app_commands.Group(name="avct", description="AVCT commands")
        self.add_group = app_commands.Group(name="add", description="Add a character or counter")
        self.character_group = discord.app_commands.Group(name="character", description="Character related commands")
        self.rename_group = app_commands.Group(name="rename", description="Rename a character or counter")
        self.remove_group = app_commands.Group(name="remove", description="Remove a character or counter")
        self.edit_group = app_commands.Group(name="edit", description="Edit or rename counter/category/comment")
        self.register_commands()

    async def cog_load(self):
        self.avct_group.add_command(self.character_group)
        self.avct_group.add_command(self.add_group)
        self.avct_group.add_command(self.rename_group)
        self.avct_group.add_command(self.remove_group)
        self.avct_group.add_command(self.edit_group)
        self.bot.tree.add_command(self.avct_group)

    def register_commands(self):
        @self.add_group.command(name="character", description="Add a character")
        async def add_character(interaction: discord.Interaction, character: str):
            character = sanitize_string(character)
            user_id = str(interaction.user.id)
            success, error = add_user_character(user_id, character)
            if success:
                await interaction.response.send_message(f"Character '{character}' added for you.", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

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
            starting: int,
            comment: str = None
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

            # Pass the string value, not the Enum, to add_predefined_counter
            success, error = add_predefined_counter(character_id, counter_enum.value, starting, comment)
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

            from collections import defaultdict
            grouped = defaultdict(list)
            for c in counters:
                grouped[c.category].append(c)

            msg_lines = []
            for cat in sorted(grouped.keys(), key=lambda x: x.lower()):
                cat_title = f"**{cat.capitalize()}**"
                msg_lines.append(cat_title)
                for c in grouped[cat]:
                    line = c.generate_display(fully_unescape)
                    msg_lines.append(line)
                    if c.comment:
                        msg_lines.append(f"-# {fully_unescape(c.comment)}")

            msg = "\n".join(msg_lines).strip()
            await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

        @self.character_group.command(name="temp", description="Change temp value for a counter")
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
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
        @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
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

async def setup(bot):
    await bot.add_cog(AvctCog(bot))
