import discord
from discord.ext import commands
from discord import app_commands
import importlib
import pkgutil

# --- Command registry and decorator ---
COMMAND_REGISTRY = []

def register_command(group_name):
    """
    Decorator to register a command function to a specific group.
    Usage:
        @register_command("group_name")
        def register_my_commands(cog):
            ...
    """
    def decorator(command_func):
        COMMAND_REGISTRY.append((group_name, command_func))
        return command_func
    return decorator

def discover_and_register_commands(cog):
    """
    Discover all modules in the 'commands' package and register their commands.
    Each command module should use @register_command("group_name") on a function
    that takes the cog and registers commands to the appropriate group.
    """
    import commands
    # Dynamically import all modules in the 'commands' package
    for _, modname, _ in pkgutil.iter_modules(commands.__path__):
        module = importlib.import_module(f"commands.{modname}")
        # The module should call @register_command, so registry is populated

    # Register all commands to their groups
    for group_name, command_func in COMMAND_REGISTRY:
        group = getattr(cog, group_name, None)
        if group:
            # Remove any commands with duplicate names before registering
            # This prevents discord.app_commands.errors.CommandAlreadyRegistered
            seen = set()
            unique_cmds = []
            for cmd in group.commands:
                if cmd.name not in seen:
                    unique_cmds.append(cmd)
                    seen.add(cmd.name)
            group.commands.clear()
            group.commands.extend(unique_cmds)
            command_func(cog)  # Pass cog as positional argument

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

        # Do NOT register commands here to avoid double registration
        # discover_and_register_commands(self)  # <-- REMOVE from __init__

    async def cog_load(self):
        # Register all commands to their groups (only once, when cog is loaded)
        discover_and_register_commands(self)

        # Add subgroups to configav group
        self.configav_group.add_command(self.add_group)
        self.configav_group.add_command(self.rename_group)
        self.configav_group.add_command(self.remove_group)
        self.configav_group.add_command(self.edit_group)
        self.configav_group.add_command(self.character_group)

        # Add main groups to bot
        self.bot.tree.add_command(self.avct_group)
        self.bot.tree.add_command(self.configav_group)

async def setup(bot):
    await bot.add_cog(AvctCog(bot))

# Documentation:
# - To add a new command, create a function in a module under 'commands' and decorate it with @register_command("group_name").
# - The function should take the cog as an argument and register commands to the specified group.
# - Supported group names: avct_group, add_group, rename_group, remove_group, edit_group, character_group.

# No changes needed if you follow the existing registration pattern.
# The new command will be registered via @register_command("configav_group") in health_commands.py.
