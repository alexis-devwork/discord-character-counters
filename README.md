# AVCT Discord Bot

A flexible Discord bot for managing tabletop RPG characters, counters, and health/damage tracking. Built with `discord.py` and SQLAlchemy, this bot supports multiple splats (character types), custom counters, health systems, and advanced command autocompletion.

---

## Features

- **Character Management**: Add, list, rename, and remove characters.
- **Counter System**: Track willpower, mana, blood pool, glamour, rage, XP, items, projects, and more.
- **Health Tracking**: Add/remove health trackers (normal/chimerical), apply damage, heal, and display health status.
- **Splat Support**: Sorcerer, Changeling, Vampire, Fera, with splat-specific setup.
- **Autocomplete**: Fast dropdowns for character, counter, category, and splat selection.
- **Debugging**: Output all character/counter/health data for troubleshooting.
- **Permissions**: All commands are per-user; users only see and edit their own data.

---

## Setup

1. **Clone the repository**  
   `git clone https://github.com/yourusername/avct-discord-bot.git`

2. **Install dependencies**  
   `pip install -r requirements.txt`

3. **Configure environment**  
   Create a `.env` file with:
   ```
   DISCORD_TOKEN=your-bot-token
   MAX_USER_CHARACTERS=10
   MAX_COUNTERS_PER_CHARACTER=50
   MAX_FIELD_LENGTH=32
   MAX_COMMENT_LENGTH=128
   ```

4. **Run the bot**  
   ```
   python main.py
   ```

---

## Command Reference

### Character Commands

- `/avct character list`  
  List all your characters.

- `/avct add character_sorc <character> <willpower> <mana>`  
  Add a Sorcerer character with willpower and mana counters, and a normal health tracker.

- `/avct add character_vampire <character> <blood_pool> <willpower>`  
  Add a Vampire character with blood pool and willpower counters, and a normal health tracker.

- `/avct add character_changeling <character> <willpower_fae> <glamour> <nightmare> <banality>`  
  Add a Changeling character with willpower_fae, glamour, nightmare, banality counters, and both normal and chimerical health trackers.

- `/avct add character_fera <character> <willpower> <gnosis> <rage> <glory> <honor> <wisdom> [honor_replacement] [glory_replacement] [wisdom_replacement]`  
  Add a Fera character with all relevant counters and a normal health tracker.

- `/avct character counters <character>`  
  Show all counters for a character, grouped by category, with health trackers at the bottom.

- `/avct character temp <character> <counter> <new_value>`  
  Set the temp value for a counter.

- `/avct character perm <character> <counter> <new_value>`  
  Set the perm value for a counter.

- `/avct character bedlam <character> <counter> <new_value>`  
  Set bedlam for a counter (only for counters of type `perm_is_maximum_bedlam`).

---

### Counter Commands

- `/avct add counter <character> <counter_type> <value> [comment] [name_override]`  
  Add a predefined counter to a character.  
  - For `project_roll` and `item_with_charges`, `name_override` is required.
  - For `glory`, `honor`, `wisdom`, `name_override` can be used to override the counter name.

- `/avct add customcounter <character> <counter> <temp> <perm> [category] [comment]`  
  Add a custom counter to a character.

- `/avct edit counter <character> <counter> <field> <value>`  
  Set temp or perm for a counter.

- `/avct edit comment <character> <counter> <comment>`  
  Set the comment for a counter.

- `/avct edit category <character> <counter> <category>`  
  Set the category for a counter.

- `/avct remove counter <character> <counter>`  
  Remove a counter from a character.

- `/avct rename counter <character> <counter> <new_name>`  
  Rename a counter for a character.

- `/avct spend counter <character> <counter> [points=1]`  
  Decrement the temp value of a counter by `points`.

- `/avct gain counter <character> <counter> [points=1]`  
  Increment the temp value of a counter by `points`.

---

### Health & Damage Commands

- `/avct add health <character> <health_type>`  
  Add a health tracker (normal or chimerical) to a character. Only one tracker per type per character.

- `/avct remove health <character> <health_type>`  
  Remove a health tracker from a character.

- `/avct damage <character> <health_type> <damage_type> <levels>`  
  Add damage to a health tracker. Damage types: Bashing, Lethal, Aggravated.

- `/avct heal <character> <health_type> <levels>`  
  Heal (remove) damage from a health tracker.

---

### Debugging & Admin

- `/avct debug`  
  Output all properties of all counters and health trackers for all your characters.  
  - Shows raw health levels and damage lists, plus formatted health display.

---

## Categories

Counters are grouped by the following categories in output:

- **tempers**
- **reknown**
- **general**
- **health**
- **items**
- **other**
- **projects**
- **xp**

---

## Health System

- Health trackers store a list of health levels (Bruised, Hurt, Injured, Wounded, Mauled, Crippled, Incapacitated).
- Damage is tracked as a list of types (Bashing, Lethal, Aggravated).
- Damage and healing commands update the damage list, respecting health track limits.
- Health display uses symbols for each damage type and shows penalties.

---

## Autocomplete

All commands that take a character, counter, category, or splat use Discord dropdown/autocomplete for fast selection.

---

## Notes

- All data is per-user; users cannot see or edit other users' characters or counters.
- Removing a character also removes all associated counters and health trackers.
- All limits (max characters, counters, field lengths) are configurable in `.env`.

---

## License & Credits

This project is open source. Please keep credits and a link to this repository in all files containing code from this project.

---
