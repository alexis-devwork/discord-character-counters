import enum

class UserCharacter:
    def __init__(self, user, character, counters=None, health=None, id=None):
        self.user = user
        self.character = character
        self.counters = counters if counters is not None else []
        self.health = health if health is not None else []
        self.id = id

    @classmethod
    def from_dict(cls, d):
        return cls(
            user=d.get("user"),
            character=d.get("character"),
            counters=[Counter.from_dict(c) for c in d.get("counters", [])],
            health=d.get("health", []),
            id=str(d.get("_id")) if d.get("_id") else None
        )

class CounterTypeEnum(enum.Enum):
    single_number = "single_number"
    perm_is_maximum = "perm_is_maximum"
    perm_is_maximum_bedlam = "perm_is_maximum_bedlam"
    perm_not_maximum = "perm_not_maximum"
    xp = "xp"
    health = "health"


class PredefinedCounterEnum(enum.Enum):
    willpower = "willpower"
    mana = "mana"
    blood_pool = "blood pool"
    willpower_fae = "willpower_fae"
    glamour = "glamour"
    nightmare = "nightmare"
    banality = "banality"
    glory = "glory"
    honor = "honor"
    wisdom = "wisdom"
    rage = "rage"
    gnosis = "gnosis"
    item_with_charges = "item_with_charges"
    project_roll = "project_roll"


class CategoryEnum(enum.Enum):
    tempers = "tempers"
    reknown = "reknown"
    general = "general"
    health = "health"
    items = "items"
    other = "other"
    projects = "projects"
    xp = "xp"

class Counter:
    def __init__(self, counter, temp, perm, category, comment=None, bedlam=0, counter_type="single_number"):
        # Prevent negative values
        if temp is not None and temp < 0:
            raise ValueError("temp cannot be below zero")
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        if bedlam is not None and bedlam < 0:
            raise ValueError("bedlam cannot be below zero")
        # For perm_is_maximum and perm_is_maximum_bedlam, temp cannot exceed perm
        if counter_type in ["perm_is_maximum", "perm_is_maximum_bedlam"]:
            if temp is not None and perm is not None and temp > perm:
                raise ValueError("temp cannot be greater than perm for this counter type")
        # For perm_is_maximum_bedlam, bedlam cannot exceed perm
        if counter_type == "perm_is_maximum_bedlam":
            if bedlam is not None and perm is not None and bedlam > perm:
                raise ValueError("bedlam cannot be greater than perm for this counter type")
        self.counter = counter
        self.temp = temp
        self.perm = perm
        self.category = category
        self.comment = comment
        self.bedlam = bedlam
        self.counter_type = counter_type

    @classmethod
    def from_dict(cls, d):
        return cls(
            counter=d.get("counter"),
            temp=d.get("temp", 0),
            perm=d.get("perm", 0),
            category=d.get("category", "general"),
            comment=d.get("comment", ""),
            bedlam=d.get("bedlam", 0),
            counter_type=d.get("counter_type", "single_number")
        )

    def generate_display(self, fully_unescape_func, display_pretty):
        if display_pretty:
            return self.generate_display_pretty(fully_unescape_func)
        return self.generate_display_basic(fully_unescape_func)

    def generate_display_basic(self, fully_unescape_func):
        base = f"{fully_unescape_func(self.counter)}:\n{self.temp}/{self.perm}"
        if self.counter_type == CounterTypeEnum.perm_is_maximum_bedlam.value:
            if not self.bedlam:
                self.bedlam = 0
            spent_pts = self.perm - self.temp
            unspent_bedlam = self.bedlam - spent_pts if spent_pts < self.bedlam else 0
            base = f"{base} (bedlam: {unspent_bedlam}/{self.bedlam})"
        # Add comment if present
        if self.comment:
            base = f"{base}\n-# {self.comment}"
        return base

    def generate_display_pretty(self, fully_unescape_func):
        """
        Generate a prettier display for counters with visual representations using emoji.

        Returns:
            str: A multi-line string with counter name and visual representation.
        """
        # Get the unescaped counter name for display
        counter_name = fully_unescape_func(self.counter)

        # Only handle counters with perm <= 15
        if self.perm > 15:
            pretty = self.generate_display_basic(fully_unescape_func)
        # Handle perm_not_maximum type counters
        elif self.counter_type == CounterTypeEnum.perm_not_maximum.value:
            stop_buttons = " ".join([":stop_button:"] * self.perm)
            negative_marks = " ".join([":asterisk:"] * self.temp)
            pretty = f"{counter_name}\n{stop_buttons}\n{negative_marks}"
        # Handle perm_is_maximum type counters
        elif self.counter_type == CounterTypeEnum.perm_is_maximum.value:
            # Calculate filled and unfilled squares
            filled = min(self.temp, self.perm)  # Ensure we don't exceed perm
            unfilled = self.perm - filled

            filled_squares = " ".join([":asterisk:"] * filled)
            unfilled_squares = " ".join([":stop_button:"] * unfilled)

            squares = f"{filled_squares}{' ' if filled > 0 and unfilled > 0 else ''}{unfilled_squares}"
            pretty = f"{counter_name}\n{squares}"
        # Handle perm_is_maximum_bedlam type counters
        elif self.counter_type == CounterTypeEnum.perm_is_maximum_bedlam.value:
            # Ensure bedlam value is valid
            if not hasattr(self, 'bedlam') or self.bedlam is None:
                self.bedlam = 0

            # Create the list of dictionaries representing each square
            status_list = []
            for i in range(self.perm):
                is_bedlam = i >= (self.perm - self.bedlam)
                is_spent = i >= self.temp
                status_list.append({"bedlam": is_bedlam, "spent": is_spent})

            # Map the statuses to emoji
            squares = []
            for status in status_list:
                if not status["spent"] and not status["bedlam"]:
                    squares.append(":asterisk:")
                elif status["spent"] and not status["bedlam"]:
                    squares.append(":stop_button:")
                elif not status["spent"] and status["bedlam"]:
                    squares.append(":b:")
                else:  # spent and bedlam
                    squares.append(":red_square:")

            pretty = f"{counter_name}\n{' '.join(squares)}"
        # Default case for other counter types
        else:
            pretty = self.generate_display(fully_unescape_func, False)
        # Add comment if present
        if self.comment:
            pretty = f"{pretty}\n-# {self.comment}"
        return pretty

class CounterFactory:
    @staticmethod
    def from_dict(data):
        """
        Create a Counter object from a dictionary.
        """
        return Counter.from_dict(data)

    @staticmethod
    def create(counter_type, perm, comment=None, override_name=None):
        # Ensure counter_type is a PredefinedCounterEnum
        if not isinstance(counter_type, PredefinedCounterEnum):
            raise ValueError("counter_type must be a PredefinedCounterEnum")
        # Prevent negative perm
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        name = override_name if override_name else counter_type.value
        # Require name for project_roll and item_with_charges
        if counter_type in (PredefinedCounterEnum.project_roll, PredefinedCounterEnum.item_with_charges):
            if not override_name:
                raise ValueError("A name must be provided for project_roll and item_with_charges counters.")
        match counter_type:
            case PredefinedCounterEnum.glory:
                return CounterFactory.create_glory(perm, comment, name)
            case PredefinedCounterEnum.honor:
                return CounterFactory.create_honor(perm, comment, name)
            case PredefinedCounterEnum.wisdom:
                return CounterFactory.create_wisdom(perm, comment, name)
            case PredefinedCounterEnum.willpower:
                return CounterFactory.create_willpower(perm, comment, name)
            case PredefinedCounterEnum.mana:
                return CounterFactory.create_mana(perm, comment, name)
            case PredefinedCounterEnum.blood_pool:
                return CounterFactory.create_blood_pool(perm, comment, name)
            case PredefinedCounterEnum.willpower_fae:
                return CounterFactory.create_willpower_fae(perm, comment, "willpower")
            case PredefinedCounterEnum.glamour:
                return CounterFactory.create_glamour(perm, comment, name)
            case PredefinedCounterEnum.nightmare:
                # Nightmare always has temp=0, perm=10
                return CounterFactory.create_nightmare(comment, name)
            case PredefinedCounterEnum.banality:
                return CounterFactory.create_banality(perm, comment, name)
            case PredefinedCounterEnum.rage:
                return CounterFactory.create_rage(perm, comment, name)
            case PredefinedCounterEnum.gnosis:
                return CounterFactory.create_gnosis(perm, comment, name)
            case PredefinedCounterEnum.item_with_charges:
                return CounterFactory.create_item_with_charges(perm, comment, name)
            case PredefinedCounterEnum.project_roll:
                return CounterFactory.create_project_roll(perm, comment, name)
            case _:
                raise ValueError("Unknown counter type")

    @staticmethod
    def create_willpower(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "willpower",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_mana(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "mana",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.general.value,
            comment=comment
        )

    @staticmethod
    def create_blood_pool(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "blood pool",
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.general.value,
            comment=comment
        )

    @staticmethod
    def create_willpower_fae(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter="willpower",
            temp=perm,
            perm=perm,
            bedlam=0,
            counter_type=CounterTypeEnum.perm_is_maximum_bedlam.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_glamour(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter="glamour" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_nightmare(comment=None, name=None):
        # Nightmare always has temp=0, perm=10
        return Counter(
            counter="nightmare" if not name else name,
            temp=0,
            perm=10,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_banality(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter="banality" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_glory(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "glory",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment
        )

    @staticmethod
    def create_honor(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "honor",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment
        )

    @staticmethod
    def create_wisdom(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name if name else "wisdom",
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.reknown.value,
            comment=comment
        )

    @staticmethod
    def create_rage(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter="rage" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_gnosis(perm, comment=None, name=None):
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter="gnosis" if not name else name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.tempers.value,
            comment=comment
        )

    @staticmethod
    def create_item_with_charges(perm, comment=None, name=None):
        if not name:
            raise ValueError("A name must be provided for item_with_charges counters.")
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name,
            temp=perm,
            perm=perm,
            counter_type=CounterTypeEnum.perm_is_maximum.value,
            category=CategoryEnum.items.value,
            comment=comment
        )

    @staticmethod
    def create_project_roll(perm, comment=None, name=None):
        if not name:
            raise ValueError("A name must be provided for project_roll counters.")
        if perm is not None and perm < 0:
            raise ValueError("perm cannot be below zero")
        return Counter(
            counter=name,
            temp=0,
            perm=perm,
            counter_type=CounterTypeEnum.perm_not_maximum.value,
            category=CategoryEnum.projects.value,
            comment=comment
        )


class SplatEnum(enum.Enum):
    sorc = "sorc"
    changeling = "changeling"
    vampire = "vampire"
    fera = "fera"
