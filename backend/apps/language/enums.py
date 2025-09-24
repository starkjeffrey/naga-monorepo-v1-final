"""Language level enums and progression logic for PUCSR language programs.

This module provides comprehensive language level progression for PUCSR's
language programs including EHSS, GESL, IEAP, Weekend Express, and Part-Time.
Includes equivalency rules for seamless student program transfers.

Based on version 0 enums.py with clean architecture principles.
Used by both language app and level_testing app.
"""

from typing import ClassVar, Optional

# Python 3.13+ Type Aliases
type LevelNumber = int
type ProgramCode = str
type DisplayName = str
type EquivalencyRule = tuple[ProgramCode, LevelNumber, LevelNumber, ProgramCode, LevelNumber, LevelNumber]


class LanguageLevel:
    """Language program levels with equivalency mapping for student transfers.

    This class provides comprehensive language level progression for PUCSR's
    language programs including EHSS, GESL, IEAP, Weekend Express, and Part-Time.
    Includes equivalency rules for seamless student program transfers.
    """

    def __init__(self, level_num: LevelNumber, display_name: DisplayName, program: ProgramCode):
        self.level_num = level_num
        self.display_name = display_name
        self.program = program

    def __str__(self) -> str:
        return f"{self.program} {self.display_name}"

    def __repr__(self) -> str:
        return f"LanguageLevel({self.level_num}, '{self.display_name}', '{self.program}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LanguageLevel):
            return False
        return self.level_num == other.level_num and self.program == other.program

    def __hash__(self) -> int:
        return hash((self.level_num, self.program))

    # Class attributes (initialized later)
    ALL_LEVELS: ClassVar[list["LanguageLevel"]]
    EQUIVALENCY_RULES: ClassVar[list[EquivalencyRule]]

    # Part-Time Levels
    PRE_B1 = None  # Will be initialized after class definition
    PRE_B2 = None

    # EHSS Levels
    EHSS_1 = None
    EHSS_2 = None
    EHSS_3 = None
    EHSS_4 = None
    EHSS_5 = None
    EHSS_6 = None
    EHSS_7 = None
    EHSS_8 = None
    EHSS_9 = None
    EHSS_10 = None
    EHSS_11 = None
    EHSS_12 = None

    # GESL Levels
    GESL_1 = None
    GESL_2 = None
    GESL_3 = None
    GESL_4 = None
    GESL_5 = None
    GESL_6 = None
    GESL_7 = None
    GESL_8 = None
    GESL_9 = None
    GESL_10 = None
    GESL_11 = None
    GESL_12 = None

    # IEAP Levels
    IEAP_PRE = None
    IEAP_BEG = None
    IEAP_1 = None
    IEAP_2 = None
    IEAP_3 = None
    IEAP_4 = None

    # Weekend Express Levels
    W_EXPR_BEG = None
    W_EXPR_1 = None
    W_EXPR_2 = None
    W_EXPR_3 = None
    W_EXPR_4 = None

    @classmethod
    def _initialize_levels(cls):
        """Initialize all language level instances."""
        # Part-Time Levels
        cls.PRE_B1 = cls(-2, "Part-Time Pre-Beginner", "PT PRE-B")
        cls.PRE_B2 = cls(-1, "Part-Time Beginner", "PT PRE-B")

        # EHSS Levels
        cls.EHSS_1 = cls(1, "Level 1", "EHSS")
        cls.EHSS_2 = cls(2, "Level 2", "EHSS")
        cls.EHSS_3 = cls(3, "Level 3", "EHSS")
        cls.EHSS_4 = cls(4, "Level 4", "EHSS")
        cls.EHSS_5 = cls(5, "Level 5", "EHSS")
        cls.EHSS_6 = cls(6, "Level 6", "EHSS")
        cls.EHSS_7 = cls(7, "Level 7", "EHSS")
        cls.EHSS_8 = cls(8, "Level 8", "EHSS")
        cls.EHSS_9 = cls(9, "Level 9", "EHSS")
        cls.EHSS_10 = cls(10, "Level 10", "EHSS")
        cls.EHSS_11 = cls(11, "Level 11", "EHSS")
        cls.EHSS_12 = cls(12, "Level 12", "EHSS")

        # GESL Levels
        cls.GESL_1 = cls(1, "Level 1", "GESL")
        cls.GESL_2 = cls(2, "Level 2", "GESL")
        cls.GESL_3 = cls(3, "Level 3", "GESL")
        cls.GESL_4 = cls(4, "Level 4", "GESL")
        cls.GESL_5 = cls(5, "Level 5", "GESL")
        cls.GESL_6 = cls(6, "Level 6", "GESL")
        cls.GESL_7 = cls(7, "Level 7", "GESL")
        cls.GESL_8 = cls(8, "Level 8", "GESL")
        cls.GESL_9 = cls(9, "Level 9", "GESL")
        cls.GESL_10 = cls(10, "Level 10", "GESL")
        cls.GESL_11 = cls(11, "Level 11", "GESL")
        cls.GESL_12 = cls(12, "Level 12", "GESL")

        # IEAP Levels
        cls.IEAP_PRE = cls(-2, "Pre-Beginner", "IEAP")
        cls.IEAP_BEG = cls(-1, "Beginner", "IEAP")
        cls.IEAP_1 = cls(1, "Level 1", "IEAP")
        cls.IEAP_2 = cls(2, "Level 2", "IEAP")
        cls.IEAP_3 = cls(3, "Level 3", "IEAP")
        cls.IEAP_4 = cls(4, "Level 4", "IEAP")

        # Weekend Express Levels
        cls.W_EXPR_BEG = cls(-1, "Weekend Express Beginner", "W_EXPR")
        cls.W_EXPR_1 = cls(1, "Weekend Express Level 1", "W_EXPR")
        cls.W_EXPR_2 = cls(2, "Weekend Express Level 2", "W_EXPR")
        cls.W_EXPR_3 = cls(3, "Weekend Express Level 3", "W_EXPR")
        cls.W_EXPR_4 = cls(4, "Weekend Express Level 4", "W_EXPR")

        # Store all levels for iteration
        cls.ALL_LEVELS = [
            cls.PRE_B1,
            cls.PRE_B2,
            cls.EHSS_1,
            cls.EHSS_2,
            cls.EHSS_3,
            cls.EHSS_4,
            cls.EHSS_5,
            cls.EHSS_6,
            cls.EHSS_7,
            cls.EHSS_8,
            cls.EHSS_9,
            cls.EHSS_10,
            cls.EHSS_11,
            cls.EHSS_12,
            cls.GESL_1,
            cls.GESL_2,
            cls.GESL_3,
            cls.GESL_4,
            cls.GESL_5,
            cls.GESL_6,
            cls.GESL_7,
            cls.GESL_8,
            cls.GESL_9,
            cls.GESL_10,
            cls.GESL_11,
            cls.GESL_12,
            cls.IEAP_PRE,
            cls.IEAP_BEG,
            cls.IEAP_1,
            cls.IEAP_2,
            cls.IEAP_3,
            cls.IEAP_4,
            cls.W_EXPR_BEG,
            cls.W_EXPR_1,
            cls.W_EXPR_2,
            cls.W_EXPR_3,
            cls.W_EXPR_4,
        ]

        # Initialize equivalency rules
        cls.EQUIVALENCY_RULES = [
            # IEAP to EHSS/GESL
            ("IEAP", -1, -1, "EHSS", 1, 3),  # IEAP Beginner -> EHSS 1-3
            ("IEAP", 1, 1, "EHSS", 4, 6),  # IEAP 1 -> EHSS 4-6
            ("IEAP", 2, 2, "EHSS", 7, 8),  # IEAP 2 -> EHSS 7-8
            ("IEAP", 3, 3, "EHSS", 9, 10),  # IEAP 3 -> EHSS 9-10
            ("IEAP", 4, 4, "EHSS", 11, 12),  # IEAP 4 -> EHSS 11-12
            ("IEAP", -1, -1, "GESL", 1, 3),  # IEAP Beginner -> GESL 1-3
            ("IEAP", 1, 1, "GESL", 4, 6),  # IEAP 1 -> GESL 4-6
            ("IEAP", 2, 2, "GESL", 7, 8),  # IEAP 2 -> GESL 7-8
            ("IEAP", 3, 3, "GESL", 9, 10),  # IEAP 3 -> GESL 9-10
            ("IEAP", 4, 4, "GESL", 11, 12),  # IEAP 4 -> GESL 11-12
        ]

        # Add one-to-one EHSS to GESL equivalencies
        cls.EQUIVALENCY_RULES.extend(cls._generate_one_to_one_rules("EHSS", "GESL", 1, 12))

    @classmethod
    def _generate_one_to_one_rules(
        cls,
        program1: str,
        program2: str,
        start_level: int,
        end_level: int,
    ) -> list[tuple[str, int, int, str, int, int]]:
        """Generate one-to-one level mapping rules between programs for a range."""
        rules = []
        for level_num in range(start_level, end_level + 1):
            rules.append((program1, level_num, level_num, program2, level_num, level_num))
        return rules

    @classmethod
    def get_levels_for_program(cls, program: str) -> list["LanguageLevel"]:
        """Retrieve all levels associated with a specific program."""
        return [level for level in cls.ALL_LEVELS if level.program == program]

    @classmethod
    def get_level_by_program_and_num(cls, program: str, level_num: int) -> Optional["LanguageLevel"]:
        """Find a level by its program and level number."""
        for level in cls.ALL_LEVELS:
            if level.program == program and level.level_num == level_num:
                return level
        return None

    @classmethod
    def _get_levels_in_range(cls, program: str, start_num: int, end_num: int) -> list["LanguageLevel"]:
        """Get all levels within a specific program and level number range."""
        return [
            level for level in cls.ALL_LEVELS if level.program == program and start_num <= level.level_num <= end_num
        ]

    @classmethod
    def get_next_level(cls, current_level: "LanguageLevel") -> Optional["LanguageLevel"]:
        """Get the next level for the current program. Return None if at the highest level."""
        levels = sorted(cls.get_levels_for_program(current_level.program), key=lambda x: x.level_num)

        for i, level in enumerate(levels):
            if level == current_level and i + 1 < len(levels):
                return levels[i + 1]

        return None  # No next level

    @classmethod
    def get_equivalent_levels(cls, level: "LanguageLevel", target_program: str) -> list["LanguageLevel"]:
        """Find equivalent levels in the target program for the given level."""
        equivalent_levels_set = set()

        for p1_name, s1, e1, p2_name, s2, e2 in cls.EQUIVALENCY_RULES:
            # Check if the current level falls into the first program's range
            if level.program == p1_name and s1 <= level.level_num <= e1:
                if target_program == p2_name:
                    equivalent_levels_set.update(cls._get_levels_in_range(p2_name, s2, e2))

            # Check if the current level falls into the second program's range
            elif level.program == p2_name and s2 <= level.level_num <= e2:
                if target_program == p1_name:
                    equivalent_levels_set.update(cls._get_levels_in_range(p1_name, s1, e1))

        return sorted(equivalent_levels_set, key=lambda x: x.level_num)

    @classmethod
    def can_transfer_to(cls, current_level: "LanguageLevel", target_program: str, target_level_num: int) -> bool:
        """Determine if a student can transfer from current level to a specific level in target program."""
        equivalent_levels = cls.get_equivalent_levels(current_level, target_program)

        if not equivalent_levels:
            return False

        target_level_instance = cls.get_level_by_program_and_num(target_program, target_level_num)

        if target_level_instance is None:
            return False

        return any(equiv.level_num >= target_level_num for equiv in equivalent_levels)

    @classmethod
    def get_course_code_for_level(cls, level: "LanguageLevel") -> str:
        """Generate course code for a language level (e.g., EHSS-05, GESL-12, EXPRESS-BEG)."""
        # Handle Weekend Express (W_EXPR) program specially
        if level.program == "W_EXPR":
            if level.level_num == -1:
                return "EXPRESS-BEG"
            else:
                return f"EXPRESS-{level.level_num:02d}"

        # Handle all other programs
        level_str = f"{level.level_num:02d}" if level.level_num > 0 else "PRE"
        return f"{level.program}-{level_str}"


# Initialize language levels after class definition
LanguageLevel._initialize_levels()


# Django choices for language levels
LANGUAGE_LEVEL_CHOICES = [(f"{level.program}_{level.level_num}", str(level)) for level in LanguageLevel.ALL_LEVELS]


def get_language_level_display_name(level_key: str) -> str:
    """Get the display name for a language level key.

    Args:
        level_key: The level key in format "PROGRAM_LEVELNUM"

    Returns:
        The display name for the level
    """
    level_dict = dict(LANGUAGE_LEVEL_CHOICES)
    return level_dict.get(level_key, level_key)
