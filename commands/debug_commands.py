import discord
from utils import characters_collection
from health import Health
from avct_cog import register_command

@register_command("configav_group")
def register_debug_commands(cog):
    # Move to configav group
    @cog.configav_group.command(
        name="debug",
        description="Show all properties of all counters for all characters for the current user (visible to everyone)"
    )
    async def debug(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        chars = list(characters_collection.find({"user": user_id}))
        debug_lines = []
        for char in chars:
            char_id = str(char["_id"])
            debug_lines.append(f"Character: {char['character']} (ID: {char_id})")
            for c in char.get("counters", []):
                debug_lines.append(
                    f"  Counter: {c.get('counter')} | temp: {c.get('temp')} | perm: {c.get('perm')} | type: {c.get('counter_type')} | category: {c.get('category')} | comment: {c.get('comment', None)} | bedlam: {c.get('bedlam', None)}"
                )
            for h in char.get("health", []):
                debug_lines.append(f"  Health ({h.get('health_type', None)}):")
                raw_levels = h.get('health_levels', [])
                debug_lines.append(f"    Raw health_levels: {raw_levels}")
                raw_damage = h.get('damage', [])
                debug_lines.append(f"    Raw damage: {raw_damage}")
                health_obj = Health(
                    health_type=h.get("health_type"),
                    damage=h.get("damage", []),
                    health_levels=h.get("health_levels", None)
                )
                debug_lines.append(health_obj.display())
        debug_text = "\n".join(debug_lines) or "No data found."
        # Discord message limit is 2000 characters
        if len(debug_text) > 2000:
            chunks = [debug_text[i:i+1990] for i in range(0, len(debug_text), 1990)]
            for idx, chunk in enumerate(chunks):
                if idx == 0:
                    await interaction.response.send_message(chunk, ephemeral=False)
                else:
                    await interaction.followup.send(chunk, ephemeral=False)
        else:
            await interaction.response.send_message(debug_text, ephemeral=False)
