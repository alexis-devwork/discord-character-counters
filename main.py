import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True

Base = declarative_base()

class UserCharacter(Base):
    __tablename__ = "user_characters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False)
    character = Column(String, nullable=False)
    counters = relationship("Counter", back_populates="character", cascade="all, delete-orphan")

class Counter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    counter = Column(String, nullable=False)
    temp = Column(Integer, nullable=False)
    perm = Column(Integer, nullable=False)
    character_id = Column(Integer, ForeignKey("user_characters.id"), nullable=False)
    character = relationship("UserCharacter", back_populates="counters")

engine = create_engine("sqlite:///db.sqlite3")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def add_user_character(user_id: str, character: str):
    session = SessionLocal()
    new_entry = UserCharacter(user=user_id, character=character)
    session.add(new_entry)
    session.commit()
    session.close()

def get_all_user_characters_for_user(user_id: str):
    session = SessionLocal()
    results = session.query(UserCharacter).filter_by(user=user_id).all()
    session.close()
    return results

def add_counter(character_id: int, counter_name: str, temp: int, perm: int):
    session = SessionLocal()
    char = session.query(UserCharacter).filter_by(id=character_id).first()
    if not char:
        session.close()
        return False
    new_counter = Counter(counter=counter_name, temp=temp, perm=perm, character=char)
    session.add(new_counter)
    session.commit()
    session.close()
    return True

def update_counter(character_id: int, counter_name: str, field: str, delta: int):
    session = SessionLocal()
    counter = session.query(Counter).filter_by(character_id=character_id, counter=counter_name).first()
    if not counter:
        session.close()
        return False
    if field == "temp":
        counter.temp += delta
    elif field == "perm":
        counter.perm += delta
    else:
        session.close()
        return False
    session.commit()
    session.close()
    return True

def get_counters_for_character(character_id: int):
    session = SessionLocal()
    counters = session.query(Counter).filter_by(character_id=character_id).all()
    session.close()
    return counters

def get_character_id_by_user_and_name(user_id: str, character_name: str):
    session = SessionLocal()
    char = session.query(UserCharacter).filter_by(user=user_id, character=character_name).first()
    result = char.id if char else None
    session.close()
    return result

# --- Autocomplete helpers ---
async def character_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    session.close()
    return [
        discord.app_commands.Choice(name=char.character, value=char.character)
        for char in chars if current.lower() in char.character.lower()
    ][:25]

async def counter_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = str(interaction.user.id)
    session = SessionLocal()
    chars = session.query(UserCharacter).filter_by(user=user_id).all()
    counters = []
    for char in chars:
        for counter in char.counters:
            if current.lower() in counter.counter.lower():
                counters.append(counter.counter)
    session.close()
    unique_counters = list(dict.fromkeys(counters))
    return [
        discord.app_commands.Choice(name=name, value=name)
        for name in unique_counters
    ][:25]

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot(command_prefix="/", intents=intents)
tree = bot.tree

@tree.command(name="addcharacter", description="Add a character")
async def addcharacter(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    add_user_character(user_id, character)
    await interaction.response.send_message(f"Character '{character}' added for you.", ephemeral=True)

@tree.command(name="listcharacters", description="List your characters")
async def listcharacters(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await interaction.response.send_message("No characters found.", ephemeral=True)
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await interaction.response.send_message(f"Characters for you:\n{msg}", ephemeral=True)

@tree.command(name="addcounter", description="Add a counter to a character")
@discord.app_commands.autocomplete(character=character_name_autocomplete)
async def addcounter(interaction: discord.Interaction, character: str, counter: str, temp: int, perm: int):
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success = add_counter(character_id, counter, temp, perm)
    if success:
        await interaction.response.send_message(f"Counter '{counter}' added to character '{character}'.", ephemeral=True)
    else:
        await interaction.response.send_message("Failed to add counter.", ephemeral=True)

@tree.command(name="changetemp", description="Change temp value for a counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def changetemp(interaction: discord.Interaction, character: str, counter: str, delta: int):
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success = update_counter(character_id, counter, "temp", delta)
    if success:
        await interaction.response.send_message(f"Temp for counter '{counter}' on character '{character}' changed by {delta}.", ephemeral=True)
    else:
        await interaction.response.send_message("Counter or character not found.", ephemeral=True)

@tree.command(name="changeperm", description="Change perm value for a counter")
@discord.app_commands.autocomplete(character=character_name_autocomplete, counter=counter_name_autocomplete)
async def changeperm(interaction: discord.Interaction, character: str, counter: str, delta: int):
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    success = update_counter(character_id, counter, "perm", delta)
    if success:
        await interaction.response.send_message(f"Perm for counter '{counter}' on character '{character}' changed by {delta}.", ephemeral=True)
    else:
        await interaction.response.send_message("Counter or character not found.", ephemeral=True)

@tree.command(name="listcounters", description="List counters for a character")
@discord.app_commands.autocomplete(character=character_name_autocomplete)
async def listcounters(interaction: discord.Interaction, character: str):
    user_id = str(interaction.user.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await interaction.response.send_message("Character not found for this user.", ephemeral=True)
        return
    counters = get_counters_for_character(character_id)
    if not counters:
        await interaction.response.send_message("No counters found for this character.", ephemeral=True)
        return
    msg = "\n".join([f"Counter: {c.counter}, Temp: {c.temp}, Perm: {c.perm}" for c in counters])
    await interaction.response.send_message(f"Counters for character '{character}':\n{msg}", ephemeral=True)

@tree.command(name="hellobyname", description="Greet the user by display name and username")
async def hellobyname(interaction: discord.Interaction):
    display_name = interaction.user.display_name
    username = interaction.user.name
    await interaction.response.send_message(f"Hello, {display_name} (username: {username})! 👋", ephemeral=True)

# --- Prefix/Text commands for compatibility ---
@bot.command(name="addcharacter")
async def addcharacter_text(ctx, character: str):
    user_id = str(ctx.author.id)
    add_user_character(user_id, character)
    await ctx.send(f"Character '{character}' added for you.")

@bot.command(name="listcharacters")
async def listcharacters_text(ctx):
    user_id = str(ctx.author.id)
    entries = get_all_user_characters_for_user(user_id)
    if not entries:
        await ctx.send("No characters found.")
        return
    msg = "\n".join([f"ID: {e.id}, Character: {e.character}" for e in entries])
    await ctx.send(f"Characters for you:\n{msg}")

@bot.command(name="addcounter")
async def addcounter_text(ctx, character: str, counter: str, temp: int, perm: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success = add_counter(character_id, counter, temp, perm)
    if success:
        await ctx.send(f"Counter '{counter}' added to character '{character}'.")
    else:
        await ctx.send("Failed to add counter.")

@bot.command(name="changetemp")
async def changetemp_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success = update_counter(character_id, counter, "temp", delta)
    if success:
        await ctx.send(f"Temp for counter '{counter}' on character '{character}' changed by {delta}.")
    else:
        await ctx.send("Counter or character not found.")

@bot.command(name="changeperm")
async def changeperm_text(ctx, character: str, counter: str, delta: int):
    user_id = str(ctx.author.id)
    character_id = get_character_id_by_user_and_name(user_id, character)
    if character_id is None:
        await ctx.send("Character not found for this user.")
        return
    success = update_counter(character_id, counter, "perm", delta)
    if success:
        await ctx.send(f"Perm for counter '{counter}' on character '{character}' changed by {delta}.")
    else:
        await ctx.send("Counter or character not found.")

@bot.command(name="listcounters")
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
    msg = "\n".join([f"Counter: {c.counter}, Temp: {c.temp}, Perm: {c.perm}" for c in counters])
    await ctx.send(f"Counters for character '{character}':\n{msg}")

@bot.command(name="hellobyname")
async def hellobyname_text(ctx):
    display_name = ctx.author.display_name
    username = ctx.author.name
    await ctx.send(f"Hello, {display_name} (username: {username})! 👋")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(TOKEN)
