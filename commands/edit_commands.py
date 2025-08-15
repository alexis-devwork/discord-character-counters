import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    get_counters_for_character,
    set_counter_comment,
    set_counter_category,
    generate_counters_output,
    fully_unescape,
    rename_counter,
    rename_character,
    category_autocomplete,
    update_counter
)
from utils import characters_collection
from bson import ObjectId
from .autocomplete import counter_name_autocomplete_for_character

def register_edit_commands(cog):
    @cog.edit_group.command(name="counter", description="Set temp or perm for a counter")
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
        counters = get_counters_for_character(character_id)
        target = next((c for c in counters if c.counter == counter), None)
        if not target:
            await interaction.response.send_message("Counter not found.", ephemeral=True)
            return
        if field == "temp":
            # For perm_is_maximum types, do not allow temp above perm or below zero
            if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                if value > target.perm:
                    target.temp = target.perm
                elif value < 0:
                    await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                    return
                else:
                    target.temp = value
            else:
                if value < 0:
                    await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                    return
                target.temp = value
        elif field == "perm":
            if value < 0:
                await interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
                return
            target.perm = value
            # For perm_is_maximum types, adjust temp if perm is lowered below temp
            if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
                if target.temp > target.perm:
                    target.temp = target.perm
        # Update in MongoDB
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        counters_list = char_doc.get("counters", [])
        for c in counters_list:
            if c["counter"] == counter:
                c["perm"] = target.perm
                c["temp"] = target.temp
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters_list}})
        counters = get_counters_for_character(character_id)
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
                f"Comment for counter '{counter}' on character '{character}' set.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to set comment.", ephemeral=True)

    # --- Edit category ---
    @cog.edit_group.command(name="category", description="Set the category for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character, category=category_autocomplete)
    async def edit_category_cmd(
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
        success, error = set_counter_category(character_id, counter, category)
        if success:
            await interaction.response.send_message(
                f"Category for counter '{counter}' on character '{character}' set to '{category}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to set category.", ephemeral=True)

    # --- Rename counter ---
    @cog.rename_group.command(name="counter", description="Rename a counter for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def rename_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        new_name: str
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        new_name = sanitize_string(new_name)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        success, error = rename_counter(character_id, counter, new_name)
        if success:
            await interaction.response.send_message(
                f"Counter '{counter}' on character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to rename counter.", ephemeral=True)

    # --- Rename character ---
    @cog.rename_group.command(name="character", description="Rename a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def rename_character_cmd(
        interaction: discord.Interaction,
        character: str,
        new_name: str
    ):
        character = sanitize_string(character)
        new_name = sanitize_string(new_name)
        user_id = str(interaction.user.id)
        success, error = rename_character(user_id, character, new_name)
        if success:
            await interaction.response.send_message(
                f"Character '{character}' renamed to '{new_name}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to rename character.", ephemeral=True)

    # --- Spend counter ---
    @cog.spend_group.command(name="counter", description="Decrement the temp value of a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def spend_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        points: int = 1
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        success, error = update_counter(character_id, counter, "temp", -points)
        if success:
            await interaction.response.send_message(
                f"Spent {points} point(s) from counter '{counter}' on character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to spend from counter.", ephemeral=True)

    # --- Gain counter ---
    @cog.gain_group.command(name="counter", description="Increment the temp value of a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def gain_counter_cmd(
        interaction: discord.Interaction,
        character: str,
        counter: str,
        points: int = 1
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        success, error = update_counter(character_id, counter, "temp", points)
        if success:
            await interaction.response.send_message(
                f"Gained {points} point(s) to counter '{counter}' on character '{character}'.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to add to counter.", ephemeral=True)

