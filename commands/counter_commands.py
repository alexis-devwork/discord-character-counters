import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
)
from .autocomplete import character_name_autocomplete, counter_name_autocomplete_for_character
from avct_cog import register_command

@register_command("counter_group")
def register_counter_commands(cog):
    # This function needs to exist but doesn't need any specific counter commands
    # Counter commands are currently defined in other modules like edit_commands.py
    pass
