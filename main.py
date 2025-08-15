import discord
from discord import app_commands
from utils import (
    MyBot,
    sanitize_string,
    validate_length,
    sanitize_and_validate,
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
    UserCharacter,
    Counter,
    SessionLocal,
    fully_unescape,  # <-- Add this import
)
from config import (
    TOKEN,
    MAX_FIELD_LENGTH,
)

intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True
bot = MyBot(command_prefix="/avct", intents=intents)
tree = bot.tree

avct_group = discord.app_commands.Group(name="avct", description="AVCT commands")

add_group = app_commands.Group(name="add", description="Add a character or counter", parent=avct_group)

@add_group.command(name="character", description="Add a character")
async def add_character(interaction: discord.Interaction, character: str):
    character = sanitize_string(character)
    user_id = str(interaction.user.id)
    success, error = add_user_character(user_id, character)
    if success:
        await interaction.response.send_message(f"Character '{character}' added for you.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@add_group.command(name="counter", description="Add a counter to a character")
@app_commands.autocomplete(character=character_name_autocomplete, category=category_autocomplete)
async def add_counter_cmd(
    interaction: discord.Interaction,
    character: str,
    counter: str,
    temp: int,
    perm: int,
    category: str,
    comment: str = None
):
    character = sanitize_string(character)
    counter = sanitize_string(counter)
    category = sanitize_string(category)
    comment = sanitize_string(comment)
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    if category not in [c.value for c in CategoryEnum]:
        await interaction.response.send_message("Invalid category selected.", ephemeral=True)
        return
    success, error = add_counter(character_id, counter, temp, perm, category, comment)
    if success:
        await interaction.response.send_message(
            f"Counter '{counter}' (category: {category}) added to character '{character}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Failed to add counter.", ephemeral=True)

character_group = discord.app_commands.Group(name="character", description="Character related commands")

@character_group.command(name="list", description="List your characters")
async def list_characters(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await interaction.response.send_message("No characters found.", ephemeral=True)
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

@character_group.command(name="counters", description="List counters for a character")
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
            line = f"{fully_unescape(c.counter)}: {c.temp}/{c.perm}"
            msg_lines.append(line)
            if c.comment:
                msg_lines.append(f"-# {fully_unescape(c.comment)}")

    msg = "\n".join(msg_lines).strip()
    await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

@character_group.command(name="temp", description="Change temp value for a counter")
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
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await interaction.response.send_message(
            f"Temp for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

@character_group.command(name="perm", description="Change perm value for a counter")
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
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await interaction.response.send_message(
            f"Perm for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}", ephemeral=True)
    else:
        await interaction.response.send_message(error or "Counter or character not found.", ephemeral=True)

# Register the character group as a subcommand of avct_group
avct_group.add_command(character_group)

tree.add_command(avct_group)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# --- Prefix/Text commands for compatibility ---
@bot.command(name="avctaddcharacter")
async def addcharacter_text(ctx, character: str):
    user_id = str(ctx.author.id)
    success, error = add_user_character(user_id, character)
    if success:
        await ctx.send(f"Character '{character}' added for you.")
    else:
        await ctx.send(error)

@bot.command(name="avctlistcharacters")
async def listcharacters_text(ctx):
    user_id = str(ctx.author.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await ctx.send("No characters found.")
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await ctx.send(f"Characters for you:\n{msg}")

@bot.command(name="avctaddcounter")
async def addcounter_text(ctx, character: str, counter: str, temp: int, perm: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = add_counter(character_id, counter, temp, perm)
    if success:
        await ctx.send(f"Counter '{counter}' added to character '{character}'.")
    else:
        await ctx.send(error or "Failed to add counter.")

@bot.command(name="avcttemp")
async def temp_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = update_counter(character_id, counter, "temp", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await ctx.send(
            f"Temp for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}")
    else:
        await ctx.send(error or "Counter or character not found.")

@bot.command(name="avctperm")
async def perm_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error = update_counter(character_id, counter, "perm", delta)
    counters = get_counters_for_character(character_id)
    if success:
        msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
        await ctx.send(
            f"Perm for counter '{counter}' on character '{character}' changed by {delta}.\n"
            f"Counters for character '{character}':\n{msg}")
    else:
        await ctx.send(error or "Counter or character not found.")

@bot.command(name="avctlistcounters")
async def listcounters_text(ctx, character: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await ctx.send("No counters found for this character.")
        return
    msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
    await ctx.send(f"Counters for character '{character}':\n{msg}")

@bot.command(name="avcthellobyname")
async def hellobyname_text(ctx):
    display_name = ctx.author.display_name
    username = ctx.author.name
    await ctx.send(f"Hello, {display_name} (username: {username})! 👋")

@bot.command(name="avctcharacter")
async def character_text(ctx, character: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await ctx.send("No counters found for this character.")
        return
    msg = "\n".join([f"{c.counter}: {c.temp}/{c.perm}" for c in counters])
    await ctx.send(f"Counters for character '{character}':\n{msg}")

def rename_character(user_id: str, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    try:
        if not validate_length("character", old_name, MAX_FIELD_LENGTH):
            raise ValueError(f"Character must be at most {MAX_FIELD_LENGTH} characters.")
        new_name = sanitize_and_validate("character", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    existing = session.query(UserCharacter).filter_by(user=user_id, character=new_name).first()
    if existing:
        session.close()
        return False, "A character with that name already exists for you."
    char = session.query(UserCharacter).filter_by(user=user_id, character=old_name).first()
    if not char:
        session.close()
        return False, "Character to rename not found."
    char.character = new_name
    session.commit()
    session.close()
    return True, None

# --- Rename subcommand group ---
rename_group = app_commands.Group(name="rename", description="Rename a character or counter", parent=avct_group)

@rename_group.command(name="character", description="Rename a character (only if new name does not exist for you)")
@app_commands.autocomplete(old_name=character_name_autocomplete)
async def rename_character_cmd(interaction: discord.Interaction, old_name: str, new_name: str):
    new_name = sanitize_string(new_name)
    user_id = str(interaction.user.id)
    success, error = rename_character(user_id, old_name, new_name)
    if success:
        await interaction.response.send_message(f"Character '{old_name}' renamed to '{new_name}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@rename_group.command(name="counter", description="Rename a counter (only if new name does not exist for this character)")
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

# Remove the old renamecharacter and renamecounter commands from avct_group
# ...existing code (remove @avct_group.command(name="renamecharacter", ...) and @avct_group.command(name="renamecounter", ...)

# Register the rename group
# (avct_group already added to tree, so nothing else needed)

@bot.command(name="avctrenamecharacter")
async def renamecharacter_text(ctx, old_name: str, new_name: str):
    user_id = str(ctx.author.id)
    success, error = rename_character(user_id, old_name, new_name)
    if success:
        await ctx.send(f"Character '{old_name}' renamed to '{new_name}'.")
    else:
        await ctx.send(error)

def rename_counter(character_id: int, old_name: str, new_name: str):
    # old_name is already sanitized from autocomplete, only validate length
    try:
        if not validate_length("counter", old_name, MAX_FIELD_LENGTH):
            raise ValueError(f"Counter must be at most {MAX_FIELD_LENGTH} characters.")
        new_name = sanitize_and_validate("counter", new_name, MAX_FIELD_LENGTH)
    except ValueError as ve:
        return False, str(ve)
    session = SessionLocal()
    existing = session.query(Counter).filter_by(character_id=character_id, counter=new_name).first()
    if existing:
        session.close()
        return False, "A counter with that name already exists for this character."
    counter_obj = session.query(Counter).filter_by(character_id=character_id, counter=old_name).first()
    if not counter_obj:
        session.close()
        return False, "Counter to rename not found."
    counter_obj.counter = new_name
    session.commit()
    session.close()
    return True, None

# --- Remove subcommand group ---
remove_group = app_commands.Group(name="remove", description="Remove a character or counter", parent=avct_group)

@remove_group.command(name="character", description="Remove a character and show its details to everyone")
@app_commands.autocomplete(character=character_name_autocomplete)
async def remove_character_cmd(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    success, error, details = remove_character(user_id, character)
    if success:
        msg = f"Character '{character}' was removed.\nDetails before removal:\n{details if details else 'No counters.'}"
        await interaction.response.send_message(msg, ephemeral=False)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@remove_group.command(name="counter", description="Remove a counter and show character state to everyone")
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

# Remove the old removecharacter and removecounter commands from avct_group
# ...existing code (remove @avct_group.command(name="removecharacter", ...) and @avct_group.command(name="removecounter", ...)

# Register the remove group
# (avct_group already added to tree, so nothing else needed)

@bot.command(name="avctremovecharacter")
async def removecharacter_text(ctx, character: str):
    user_id = str(ctx.author.id)
    success, error, details = remove_character(user_id, character)
    if success:
        msg = f"Character '{character}' was removed.\nDetails before removal:\n{details if details else 'No counters.'}"
        await ctx.send(msg)
    else:
        await ctx.send(error)

@bot.command(name="avctremovecounter")
async def removecounter_text(ctx, character: str, counter: str):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success, error, details = remove_counter(character_id, counter)
    if success:
        msg = (
            f"Counter '{counter}' was removed from character '{character}'.\n"
            f"Character state before removal:\n{details if details else 'No counters.'}"
        )
        await ctx.send(msg)
    else:
        await ctx.send(error)


# --- Edit subcommand group ---
edit_group = app_commands.Group(name="edit", description="Edit or rename counter/category/comment", parent=avct_group)

@edit_group.command(name="setcountercategory", description="Set the category for an existing counter")
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

@edit_group.command(name="setcountercomment", description="Set the comment for an existing counter")
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

@edit_group.command(name="renamecharacter", description="Rename a character (only if new name does not exist for you)")
@app_commands.autocomplete(old_name=character_name_autocomplete)
async def edit_rename_character_cmd(interaction: discord.Interaction, old_name: str, new_name: str):
    new_name = sanitize_string(new_name)
    user_id = str(interaction.user.id)
    success, error = rename_character(user_id, old_name, new_name)
    if success:
        await interaction.response.send_message(f"Character '{old_name}' renamed to '{new_name}'.", ephemeral=True)
    else:
        await interaction.response.send_message(error, ephemeral=True)

@edit_group.command(name="renamecounter", description="Rename a counter (only if new name does not exist for this character)")
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


bot.run(TOKEN)
