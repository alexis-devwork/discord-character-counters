import discord
from discord.ext import commands
from discord import app_commands

# Command modules
from commands.character_commands import register_character_commands
from commands.counter_commands import register_counter_commands
from commands.health_commands import register_health_commands
from commands.edit_commands import register_edit_commands
from commands.add_commands import register_add_commands
from commands.debug_commands import register_debug_commands
from commands.remove_commands import register_remove_commands

class AvctCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize command groups
        self.avct_group = discord.app_commands.Group(name="avct", description="AVCT essential commands")
        self.configav_group = discord.app_commands.Group(name="configav", description="AVCT configuration commands")

        # Define groups for configav
        self.add_group = app_commands.Group(name="add", description="Add a character or counter")
        self.rename_group = app_commands.Group(name="rename", description="Rename a character or counter")
        self.remove_group = app_commands.Group(name="remove", description="Remove a character or counter")
        self.edit_group = app_commands.Group(name="edit", description="Edit or rename counter/category/comment")
        self.character_group = app_commands.Group(name="character", description="Character related commands")

        # Register all commands
        self.register_commands()

    async def cog_load(self):
        # Add subgroups to configav group
        self.configav_group.add_command(self.add_group)
        self.configav_group.add_command(self.rename_group)
        self.configav_group.add_command(self.remove_group)
        self.configav_group.add_command(self.edit_group)
        self.configav_group.add_command(self.character_group)

        # Add main groups to bot
        self.bot.tree.add_command(self.avct_group)
        self.bot.tree.add_command(self.configav_group)

    def register_commands(self):
        # Register commands from each module
        register_character_commands(self)
        register_counter_commands(self)
        register_health_commands(self)
        register_edit_commands(self)
        register_add_commands(self)
        register_debug_commands(self)
        register_remove_commands(self)

async def setup(bot):
    await bot.add_cog(AvctCog(bot))
