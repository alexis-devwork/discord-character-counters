import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_all_user_characters_for_user,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
    get_counters_for_character,
    fully_unescape,
    generate_counters_output
)
from utils import characters_collection
from health import Health
from bson import ObjectId
from .autocomplete import counter_name_autocomplete_for_character, bedlam_counter_autocomplete

def register_character_commands(cog):
    @cog.character_group.command(name="list", description="List your characters")
    async def list_characters(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        entries = get_all_user_characters_for_user(user_id)
        if not entries:
            await interaction.response.send_message("No characters found.", ephemeral=True)
            return
        msg = "\n".join([f"ID: {getattr(e, 'id', 'N/A')}, Character: {e.character}" for e in entries])
        await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

    @cog.character_group.command(name="counters", description="List counters for a character")
    @discord.app_commands.autocomplete(character=character_name_autocomplete)
    async def counters(interaction: discord.Interaction, character: str):
        user_id = str(interaction.user.id)
        character = sanitize_string(character)
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
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        health_entries = char_doc.get("health", []) if char_doc else []
        if health_entries:
            msg += "\n\n**Health Trackers:**"
            for h in health_entries:
                health_obj = Health(
                    health_type=h.get("health_type"),
                    damage=h.get("damage", []),
                    health_levels=h.get("health_levels", None)
                )
                msg += f"\nHealth ({health_obj.health_type}):\n{health_obj.display()}"
        await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="temp", description="Set temp value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def temp(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        counters = get_counters_for_character(character_id)
        target = next((c for c in counters if c.counter == counter), None)
        if not target:
            await interaction.response.send_message("Counter not found.", ephemeral=True)
            return
        # For perm_is_maximum types, do not allow temp above perm or below zero
        if target.counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if new_value > target.perm:
                target.temp = target.perm
            elif new_value < 0:
                await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return
            else:
                target.temp = new_value
        else:
            if new_value < 0:
                await interaction.response.send_message("Cannot set temp below zero.", ephemeral=True)
                return
            target.temp = new_value
        # Update in MongoDB
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        counters_list = char_doc.get("counters", [])
        for c in counters_list:
            if c["counter"] == counter:
                c["temp"] = target.temp
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters_list}})
        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)
        await interaction.response.send_message(
            f"Temp for counter '{counter}' on character '{character}' set to {new_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="perm", description="Set perm value for a counter")
    @discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete_for_character)
    async def perm(interaction: discord.Interaction, character: str, counter: str, new_value: int):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        counters = get_counters_for_character(character_id)
        target = next((c for c in counters if c.counter == counter), None)
        if not target:
            await interaction.response.send_message("Counter not found.", ephemeral=True)
            return
        if new_value < 0:
            await interaction.response.send_message("Cannot set perm below zero.", ephemeral=True)
            return
        target.perm = new_value
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
            f"Perm for counter '{counter}' on character '{character}' set to {new_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)

    @cog.character_group.command(name="bedlam", description="Set bedlam for a counter (only perm_is_maximum_bedlam counters)")
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
        target.bedlam = new_value
        # Update in MongoDB
        char_doc = characters_collection.find_one({"_id": ObjectId(character_id)})
        counters_list = char_doc.get("counters", [])
        for c in counters_list:
            if c["counter"] == counter:
                c["bedlam"] = target.bedlam
        characters_collection.update_one({"_id": ObjectId(character_id)}, {"$set": {"counters": counters_list}})
        counters = get_counters_for_character(character_id)
        msg = generate_counters_output(counters, fully_unescape)
        await interaction.response.send_message(
            f"Bedlam for counter '{counter}' on character '{character}' set to {new_value}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
