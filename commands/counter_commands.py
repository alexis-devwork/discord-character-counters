import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    toggle_counter_option,
)
from .autocomplete import (
    character_name_autocomplete,
    toggle_counter_autocomplete
)
from avct_cog import register_command

# FIX: Make toggle_option_autocomplete an async function
async def toggle_option_autocomplete(interaction: discord.Interaction, current: str):
    options = ["force_unpretty", "is_resettable", "is_exhaustible"]
    return [
        app_commands.Choice(name=opt, value=opt)
        for opt in options
        if current.lower() in opt.lower()
    ][:25]

@register_command("configav_group")
def register_configav_commands(cog):
    # This function needs to exist but doesn't need any specific counter commands
    # Counter commands are currently defined in other modules like edit_commands.py
    pass

    @cog.configav_group.command(
        name="toggle",
        description="Toggle force_unpretty, is_resettable, or is_exhaustible for a counter"
    )
    @app_commands.autocomplete(
        character=character_name_autocomplete,
        toggle=toggle_option_autocomplete,
        counter=toggle_counter_autocomplete
    )
    async def toggle_cmd(
        interaction: discord.Interaction,
        character: str,
        toggle: str,
        counter: str,
        value: bool
    ):
        character = sanitize_string(character)
        counter = sanitize_string(counter)
        user_id = str(interaction.user.id)
        character_id = get_character_id_by_user_and_name(user_id, character)
        if character_id is None:
            await interaction.response.send_message("Character not found for this user.", ephemeral=True)
            return
        success, error = toggle_counter_option(character_id, counter, toggle, value)
        if success:
            await interaction.response.send_message(
                f"Set {toggle} for counter '{counter}' on character '{character}' to {value}.", ephemeral=True)
        else:
            await interaction.response.send_message(error or "Failed to toggle option.", ephemeral=True)
