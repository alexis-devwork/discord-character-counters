# AVCT Discord Bot

A Discord bot for managing tabletop RPG characters, counters, and health/damage tracking for white wolf TTRPG games. This bot supports multiple splats (game types), custom counters, and health tracking. 

All commands support autocomplete.

![screenshot.png](media/screenshot.png)

---

## Getting Started

Begin by adding a character using one of the following commands:

- `/configav add character_sorc <character> <willpower> <mana>`  
  Add a Sorcerer character with willpower and mana counters, and a normal health tracker.
- `/configav add character_vampire <character> <blood_pool> <willpower>`  
  Add a Vampire character with blood pool and willpower counters, and a normal health tracker.
- `/configav add character_changeling <character> <willpower_fae> <glamour> <banality>`  
  Add a Changeling character with willpower_fae, glamour, nightmare (default 0), banality counters, and both normal and chimerical health trackers.
- `/configav add character_fera <character> <willpower> <gnosis> <rage> <glory> <honor> <wisdom> [honor_replacement] [glory_replacement] [wisdom_replacement]`  
  Add a Fera character with all relevant counters and a normal health tracker.

Once you have a character, use the essential `/avct` commands for gameplay:

- `/avct show <character> [public=False]`  
  Show all counters and health for a character. Set `public` to True to make visible to everyone.
- `/avct plus <character> <counter> [points=1]`  
  Add points to a counter.
- `/avct minus <character> <counter> [points=1]`  
  Remove points from a counter.
- `/avct damage <character> <damage_type> <levels> [chimerical=False]`  
  Add damage to a health tracker. Defaults to normal health, set `chimerical` to True for chimerical damage.
- `/avct heal <character> <levels> [chimerical=False]`  
  Heal damage from a health tracker. Defaults to normal health, set `chimerical` to True for chimerical healing.
- `/avct reset_eligible <character>`  
  Reset all eligible counters (with `is_resettable=True`) for a character.

### Adding Predefined Counters with `/configav add counter`

You can add predefined counters to your character using the following command:

```
/configav add counter <character> <counter_type> <value> [comment] [item_or_project_name]
```

**Predefined counter types you can pick from:**

- `item_with_charges` *(requires `item_or_project_name`)*
- `project_roll` *(requires `item_or_project_name`)*
- `Remove_When_Exhausted` *(requires `item_or_project_name`; counter is removed when value reaches 0)*
- `Reset_Eligible` *(requires `item_or_project_name`; counter can be reset to its perm value via `/avct reset_eligible`)*
- `willpower`
- `mana`
- `blood_pool`
- `willpower_fae`
- `glamour`
- `nightmare`
- `banality`
- `glory`
- `honor`
- `wisdom`
- `rage`
- `gnosis`

**Usage notes:**
- For `item_with_charges`, `project_roll`, `Remove_When_Exhausted`, and `Reset_Eligible`, you must provide a name for the counter in `item_or_project_name`.
- For `glory`, `honor`, `wisdom`, you can use `item_or_project_name` to override the counter name.
- `Remove_When_Exhausted` counters are automatically removed when their value reaches 0.
- `Reset_Eligible` counters can be reset to their perm value using `/avct reset_eligible`.

**Examples:**
```
/configav add counter MyCharacter willpower 5
/configav add counter MyCharacter item_with_charges 3 "Magic Sword"
/configav add counter MyCharacter Remove_When_Exhausted 1 "Potion"
/configav add counter MyCharacter Reset_Eligible 10 "Daily Power"
```

## Additional Configuration & Management

Commands are grouped as follows:
- `/configav` - Configuration and management commands
- `/configav add` - Add counters, health trackers, health levels
- `/configav edit` - Edit counter values, comments, categories
- `/configav rename` - Rename characters and counters
- `/configav remove` - Remove characters, counters, health trackers
- `/configav toggle` - Toggle counter options
- `/configav debug` - Debugging output

### Editing Content (`/configav edit`)
- `/configav edit comment <character> <counter> <comment>`  
  Set the comment for a counter.
- `/configav edit category <character> <counter> <category>`  
  Set the category for a counter.

### Renaming (`/configav rename`)
- `/configav rename character <character> <new_name>`  
  Rename a character.
- `/configav rename counter <character> <counter> <new_name>`  
  Rename a counter for a character.

### Removing Content (`/configav remove`)
- `/configav remove character <character>`  
  Remove a character and all its counters.
- `/configav remove counter <character> <counter>`  
  Remove a counter from a character.
- `/configav remove health_tracker <character> <health_type>`  
  Remove a health tracker from a character.

### Character Management
- `/configav character list`  
  List all your characters.
- `/configav character temp <character> <counter> <new_value>`  
  Set the temp value for a counter.
- `/configav character perm <character> <counter> <new_value>`  
  Set the perm value for a counter.
- `/configav character bedlam <character> <counter> <new_value>`  
  Set bedlam for a counter (only for counters of type `perm_is_maximum_bedlam`).

### Adding Content (`/configav add`)
- `/configav add counter <character> <counter_type> <value> [comment] [item_or_project_name]`  
  Add a predefined counter to a character.  
- `/configav add customcounter <character> <counter_name> <counter_type> <value> [category] [comment] [force_unpretty] [is_resettable] [is_exhaustible] [set_temp_nonzero]`  
  Add a custom counter to a character.  
  - `counter_type` can be: `single_number`, `perm_is_maximum`, `perm_is_maximum_bedlam`, `perm_not_maximum`.
  - Options:  
    - `force_unpretty`: disables emoji formatting for this counter  
    - `is_resettable`: enables reset via `/avct reset_eligible`  
    - `is_exhaustible`: counter is removed when value reaches 0  
    - `set_temp_nonzero`: for `perm_not_maximum`, sets temp to value instead of 0
- `/configav add health_tracker <character> [chimerical=False]`  
  Add a health tracker (normal or chimerical) to a character. Only one tracker per type per character.
- `/configav add health_level <character> <health_level_type>`  
  Add an extra health level to all health trackers for a character.


### Debugging (`/configav debug`)
- `/configav debug`  
  Output all properties of all counters and health trackers for all your characters.

### Counter Options (`/configav toggle`)
- `/configav toggle <character> <toggle> <counter> <value>`  
  Toggle options for a counter:
  - `force_unpretty`: disables emoji formatting for this counter
  - `is_resettable`: enables reset via `/avct reset_eligible`
  - `is_exhaustible`: counter is removed when value reaches 0

---

## Special Counter Types

- **Remove_When_Exhausted**: Counter is removed automatically when its value reaches 0.
- **Reset_Eligible**: Counter can be reset to its perm value via `/avct reset_eligible`.

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
- **You can now add custom health levels to a character's health tracker using `/configav add health_level`.**
- Damage is tracked as a list of types (Bashing, Lethal, Aggravated).
- Damage and healing commands update the damage list, respecting health track limits.
- Normal and chimerical health trackers are displayed side by side when both exist.

### Health Display

Health is displayed using emoji:
- ◼️ - Empty/undamaged health level
- 🇧 - Bashing damage
- 🇱 - Lethal damage
- 🇦 - Aggravated damage

When both normal and chimerical health are present, a header row with 🟦 🇨 indicates the columns.

---

## Counter Types

- **Single number**: Basic counter with temp and perm values
- **Perm is maximum**: Counter where temp can't exceed perm (used for willpower, etc.)
- **Perm is maximum with bedlam**: Counter with additional bedlam value (used for changeling willpower)
- **Perm not maximum**: Counter where temp and perm are tracked separately

### Counter Options

- `force_unpretty`: disables emoji formatting for this counter
- `is_resettable`: enables reset via `/avct reset_eligible`
- `is_exhaustible`: counter is removed when value reaches 0

---

## Autocomplete

All commands that take a character, counter, category, or splat use Discord dropdown/autocomplete for fast selection.

---

## Notes

- All data is per-user; users cannot see or edit other users' characters or counters.
- Removing a character also removes all associated counters and health trackers.
- All limits (max characters, counters, field lengths) are configurable in `.env`.
- Health display automatically pairs normal and chimerical health when both exist.

---

## License & Credits

This project is open source. Please keep credits and a link to this repository in all files containing code from this project.

---

## Testing

This project includes a comprehensive test suite covering character management, counter operations, health tracking, health level addition, and Discord commands.

### Setup for Testing

1. **Install test dependencies**  
   `pip install -r requirements-dev.txt`

2. **Run the tests**  
   ```
   pytest
   ```

3. **Run tests with coverage**  
   ```
   pytest --cov=.
   ```

### Test Structure

- `tests/test_character_management.py` - Tests for character CRUD operations
- `tests/test_counter_management.py` - Tests for counter operations
- `tests/test_health_system.py` - Tests for health tracking, damage system, and health level addition
- `tests/test_commands.py` - Tests for Discord commands

### Mock Objects

The test suite includes mock objects for Discord interactions, allowing tests to run without an actual Discord connection.

---

## Features

- **Character Management**: Add, list, rename, and remove characters.
- **Counter System**: Track willpower, mana, blood pool, glamour, rage, XP, items, projects, and more.
- **Health Tracking**: Add/remove health trackers (normal/chimerical), apply damage, heal, and display health status.
- **Splat Support**: Sorcerer, Changeling, Vampire, Fera, with splat-specific setup.
- **Autocomplete**: Fast dropdowns for character, counter, category, and splat selection.
- **Debugging**: Output all character/counter/health data for troubleshooting.
- **Permissions**: All commands are per-user; users only see and edit their own data.
- **Public/Private Display**: Option to show character information publicly or privately.

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
   MONGO_CONNECTION_STRING=your-mongodb-connection-string
   MONGO_DB_NAME=your-database-name
   ```

4. **Run the bot**  
   ```
   python main.py
   ```

---
