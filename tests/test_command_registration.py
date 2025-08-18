import inspect

import commands.add_commands as add_commands
import commands.character_commands as character_commands
import commands.counter_commands as counter_commands
import commands.edit_commands as edit_commands
import commands.health_commands as health_commands
import commands.remove_commands as remove_commands
import commands.debug_commands as debug_commands

import pytest
import discord
from avct_cog import AvctCog

EXPECTED_COMMAND_REGISTRATION_SIGNATURES = {
    "commands.add_commands": {
        "register_add_commands": ["cog"],
    },
    "commands.character_commands": {
        "register_character_commands": ["cog"],
    },
    "commands.counter_commands": {
        "register_configav_commands": ["cog"],
    },
    "commands.edit_commands": {
        "register_edit_commands": ["cog"],
    },
    "commands.health_commands": {
        "register_health_commands": ["cog"],
        "register_configav_health_commands": ["cog"],
    },
    "commands.remove_commands": {
        "register_remove_commands": ["cog"],
    },
    "commands.debug_commands": {
        "register_debug_commands": ["cog"],
    },
}

# Expected commands and their argument names (and which ones have autocomplete)
EXPECTED_COMMANDS = [
    # configav_group subgroups
    {
        "group": "configav",
        "subgroup": "rename",
        "command": "character",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "new_name", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "rename",
        "command": "counter",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "new_name", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "add",
        "command": "character_sorc",
        "params": [
            {"name": "character", "autocomplete": False},
            {"name": "willpower", "autocomplete": False},
            {"name": "mana", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "add",
        "command": "customcounter",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter_name", "autocomplete": False},
            {"name": "counter_type", "autocomplete": True},
            {"name": "value", "autocomplete": False},
            {"name": "category", "autocomplete": True},
            {"name": "comment", "autocomplete": False},
            {"name": "force_unpretty", "autocomplete": False},
            {"name": "is_resettable", "autocomplete": False},
            {"name": "is_exhaustible", "autocomplete": False},
            {"name": "set_temp_nonzero", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "remove",
        "command": "character",
        "params": [
            {"name": "character", "autocomplete": True},
        ],
    },
    {
        "group": "configav",
        "subgroup": "remove",
        "command": "counter",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
        ],
    },
    {
        "group": "configav",
        "subgroup": "remove",
        "command": "health_tracker",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "health_type", "autocomplete": True},
        ],
    },
    {
        "group": "configav",
        "subgroup": "edit",
        "command": "counter",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "field", "autocomplete": False},
            {"name": "value", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "edit",
        "command": "comment",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "comment", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "edit",
        "command": "category",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "category", "autocomplete": True},
        ],
    },
    # configav_group character_group
    {
        "group": "configav",
        "subgroup": "character",
        "command": "list",
        "params": [],
    },
    {
        "group": "configav",
        "subgroup": "character",
        "command": "temp",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "new_value", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "character",
        "command": "perm",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "new_value", "autocomplete": False},
        ],
    },
    {
        "group": "configav",
        "subgroup": "character",
        "command": "bedlam",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "new_value", "autocomplete": False},
        ],
    },
    # configav_group add_group health_level
    {
        "group": "configav",
        "subgroup": "add",
        "command": "health_level",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "health_level_type", "autocomplete": True},
        ],
    },
    # configav_group configav_group toggle
    {
        "group": "configav",
        "subgroup": None,
        "command": "toggle",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "toggle", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "value", "autocomplete": False},
        ],
    },
    # avct_group commands
    {
        "group": "avct",
        "subgroup": None,
        "command": "show",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "public", "autocomplete": False},
        ],
    },
    {
        "group": "avct",
        "subgroup": None,
        "command": "reset_eligible",
        "params": [
            {"name": "character", "autocomplete": True},
        ],
    },
    {
        "group": "avct",
        "subgroup": None,
        "command": "damage",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "damage_type", "autocomplete": True},
            {"name": "levels", "autocomplete": False},
            {"name": "chimerical", "autocomplete": False},
        ],
    },
    {
        "group": "avct",
        "subgroup": None,
        "command": "heal",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "levels", "autocomplete": False},
            {"name": "chimerical", "autocomplete": False},
        ],
    },
    {
        "group": "avct",
        "subgroup": None,
        "command": "plus",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "points", "autocomplete": False},
        ],
    },
    {
        "group": "avct",
        "subgroup": None,
        "command": "minus",
        "params": [
            {"name": "character", "autocomplete": True},
            {"name": "counter", "autocomplete": True},
            {"name": "points", "autocomplete": False},
        ],
    },
]


@pytest.mark.parametrize("module, module_name", [
    (add_commands, "commands.add_commands"),
    (character_commands, "commands.character_commands"),
    (counter_commands, "commands.counter_commands"),
    (edit_commands, "commands.edit_commands"),
    (health_commands, "commands.health_commands"),
    (remove_commands, "commands.remove_commands"),
    (debug_commands, "commands.debug_commands"),
])
def test_command_registration_signatures(module, module_name):
    expected_funcs = EXPECTED_COMMAND_REGISTRATION_SIGNATURES[module_name]
    for func_name, expected_params in expected_funcs.items():
        assert hasattr(module, func_name), f"{module_name} missing {func_name}"
        func = getattr(module, func_name)
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        assert param_names == expected_params, (
            f"{module_name}.{func_name} signature changed: expected {expected_params}, got {param_names}"
        )


def get_command_tree():
    class DummyTree:
        def add_command(self, cmd):
            pass  # Do nothing

    class BotMock:
        def __init__(self):
            self.tree = DummyTree()

    cog = AvctCog(BotMock())
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(cog.cog_load())
    return cog


@pytest.mark.parametrize("cmd_spec", EXPECTED_COMMANDS)
def test_command_signature_and_autocomplete(cmd_spec):
    cog = get_command_tree()
    # Find the top-level group
    group = getattr(cog, f"{cmd_spec['group']}_group", None)
    assert group is not None, f"Group '{cmd_spec['group']}_group' not found"
    # If subgroup is specified, find it
    subgroup = group
    if cmd_spec["subgroup"]:
        # Try as attribute first
        subgroup = getattr(group, f"{cmd_spec['subgroup']}_group", None)
        if subgroup is None:
            subgroup = getattr(group, cmd_spec["subgroup"], None)
        # If still not found, search in group's commands for a matching subgroup
        if subgroup is None:
            for cmd in getattr(group, "commands", []):
                if (
                    cmd.name == cmd_spec["subgroup"]
                    and isinstance(cmd, discord.app_commands.Group)
                ):
                    subgroup = cmd
                    break
        # Special case: look for subgroup in configav_group.commands if subgroup is "configav"
        if subgroup is None and cmd_spec["group"] == "configav" and cmd_spec["subgroup"] == "configav":
            for cmd in getattr(group, "commands", []):
                if cmd.name == "configav" and isinstance(cmd, discord.app_commands.Group):
                    subgroup = cmd
                    break
        # Special case: for configav/edit/character, look in edit_group for the command
        if subgroup is None and cmd_spec["group"] == "configav" and cmd_spec["subgroup"] == "edit":
            subgroup = getattr(group, "edit_group", None)
        assert subgroup is not None, f"Subgroup '{cmd_spec['subgroup']}' not found in '{cmd_spec['group']}_group'"
    # Find the command
    command = None
    for cmd in getattr(subgroup, "commands", []):
        if cmd.name == cmd_spec["command"]:
            command = cmd
            break
    # Special case: look for command in configav_group.edit_group.commands if not found in configav_group.edit_group
    if command is None and cmd_spec["group"] == "configav" and cmd_spec["subgroup"] == "edit":
        edit_group = getattr(group, "edit_group", None)
        if edit_group:
            for cmd in getattr(edit_group, "commands", []):
                if cmd.name == cmd_spec["command"]:
                    command = cmd
                    break
    assert command is not None, f"Command '{cmd_spec['command']}' not found in group '{cmd_spec['group']}' subgroup '{cmd_spec['subgroup']}'"
    # Check parameter names and autocomplete
    params_obj = getattr(command, "parameters", None)
    if isinstance(params_obj, dict):
        actual_params = list(params_obj.values())
    elif isinstance(params_obj, list):
        actual_params = params_obj
    else:
        raise TypeError(f"Command '{cmd_spec['command']}' parameters are not a dict or list")
    expected_params = cmd_spec["params"]
    assert len(actual_params) == len(expected_params), f"Command '{cmd_spec['command']}' parameter count mismatch: expected {len(expected_params)}, got {len(actual_params)}"
    for actual, expected in zip(actual_params, expected_params):
        assert actual.name == expected["name"], f"Command '{cmd_spec['command']}' parameter name mismatch: expected '{expected['name']}', got '{actual.name}'"
        if expected["autocomplete"]:
            assert getattr(actual, "autocomplete", None) is not None, f"Command '{cmd_spec['command']}' parameter '{actual.name}' missing autocomplete"
