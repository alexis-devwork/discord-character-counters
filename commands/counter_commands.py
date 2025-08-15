import discord
from discord import app_commands
from utils import (
    sanitize_string,
    get_character_id_by_user_and_name,
    character_name_autocomplete,
)
from .autocomplete import counter_name_autocomplete_for_character

def register_counter_commands(cog):
    # This function needs to exist but doesn't need any specific counter commands
    # Counter commands are currently defined in other modules like edit_commands.py
    pass

