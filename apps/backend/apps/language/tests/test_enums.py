"""Test cases for language level enumeration system.

Tests the core language level progression logic, equivalency mappings,
and transfer capabilities between different language programs.
"""

from apps.language.enums import LanguageLevel


class TestLanguageLevelEnums:
    """Test language level enumeration and progression logic."""

    def test_language_level_initialization(self):
        """Test that all language levels are properly initialized."""
        # Test that levels are created
        assert LanguageLevel.EHSS_1 is not None
        assert LanguageLevel.GESL_1 is not None
        assert LanguageLevel.IEAP_1 is not None
        assert LanguageLevel.W_EXPR_1 is not None

        # Test level properties
        assert LanguageLevel.EHSS_1.level_num == 1
        assert LanguageLevel.EHSS_1.program == "EHSS"
        assert LanguageLevel.EHSS_1.display_name == "Level 1"

        # Test string representation
        assert str(LanguageLevel.EHSS_1) == "EHSS Level 1"

    def test_all_levels_list(self):
        """Test that ALL_LEVELS contains all expected levels."""
        assert len(LanguageLevel.ALL_LEVELS) > 0

        # Check that we have levels for each program
        programs = {level.program for level in LanguageLevel.ALL_LEVELS}
        expected_programs = {"EHSS", "GESL", "IEAP", "W_EXPR", "PT PRE-B"}
        assert programs == expected_programs

    def test_get_levels_for_program(self):
        """Test getting all levels for a specific program."""
        ehss_levels = LanguageLevel.get_levels_for_program("EHSS")
        assert len(ehss_levels) == 12  # EHSS has levels 1-12
        assert all(level.program == "EHSS" for level in ehss_levels)

        gesl_levels = LanguageLevel.get_levels_for_program("GESL")
        assert len(gesl_levels) == 12  # GESL has levels 1-12

        ieap_levels = LanguageLevel.get_levels_for_program("IEAP")
        assert len(ieap_levels) == 6  # IEAP has PRE, BEG, 1-4

    def test_get_level_by_program_and_num(self):
        """Test finding specific levels by program and number."""
        level = LanguageLevel.get_level_by_program_and_num("EHSS", 5)
        assert level is not None
        assert level.program == "EHSS"
        assert level.level_num == 5

        # Test non-existent level
        level = LanguageLevel.get_level_by_program_and_num("EHSS", 99)
        assert level is None

        # Test invalid program
        level = LanguageLevel.get_level_by_program_and_num("INVALID", 1)
        assert level is None

    def test_get_next_level(self):
        """Test getting the next level in progression."""
        current = LanguageLevel.EHSS_5
        next_level = LanguageLevel.get_next_level(current)
        assert next_level is not None
        assert next_level.level_num == 6
        assert next_level.program == "EHSS"

        # Test last level in program
        last_level = LanguageLevel.EHSS_12
        next_level = LanguageLevel.get_next_level(last_level)
        assert next_level is None

    def test_ieap_to_ehss_equivalency(self):
        """Test IEAP to EHSS level equivalency mappings."""
        # IEAP Beginner should map to EHSS 1-3
        ieap_beg = LanguageLevel.IEAP_BEG
        ehss_equivalents = LanguageLevel.get_equivalent_levels(ieap_beg, "EHSS")

        assert len(ehss_equivalents) == 3
        assert all(level.program == "EHSS" for level in ehss_equivalents)
        ehss_nums = [level.level_num for level in ehss_equivalents]
        assert sorted(ehss_nums) == [1, 2, 3]

        # IEAP 1 should map to EHSS 4-6
        ieap_1 = LanguageLevel.IEAP_1
        ehss_equivalents = LanguageLevel.get_equivalent_levels(ieap_1, "EHSS")

        assert len(ehss_equivalents) == 3
        ehss_nums = [level.level_num for level in ehss_equivalents]
        assert sorted(ehss_nums) == [4, 5, 6]

    def test_ieap_to_gesl_equivalency(self):
        """Test IEAP to GESL level equivalency mappings."""
        # IEAP 2 should map to GESL 7-8
        ieap_2 = LanguageLevel.IEAP_2
        gesl_equivalents = LanguageLevel.get_equivalent_levels(ieap_2, "GESL")

        assert len(gesl_equivalents) == 2
        assert all(level.program == "GESL" for level in gesl_equivalents)
        gesl_nums = [level.level_num for level in gesl_equivalents]
        assert sorted(gesl_nums) == [7, 8]

    def test_ehss_to_gesl_one_to_one_equivalency(self):
        """Test one-to-one equivalency between EHSS and GESL."""
        # EHSS 5 should map to GESL 5
        ehss_5 = LanguageLevel.EHSS_5
        gesl_equivalents = LanguageLevel.get_equivalent_levels(ehss_5, "GESL")

        assert len(gesl_equivalents) == 1
        assert gesl_equivalents[0].program == "GESL"
        assert gesl_equivalents[0].level_num == 5

        # Test reverse mapping
        gesl_5 = LanguageLevel.GESL_5
        ehss_equivalents = LanguageLevel.get_equivalent_levels(gesl_5, "EHSS")

        assert len(ehss_equivalents) == 1
        assert ehss_equivalents[0].program == "EHSS"
        assert ehss_equivalents[0].level_num == 5

    def test_bidirectional_equivalency(self):
        """Test that equivalency rules work bidirectionally."""
        # Test EHSS to GESL
        ehss_3 = LanguageLevel.EHSS_3
        gesl_from_ehss = LanguageLevel.get_equivalent_levels(ehss_3, "GESL")

        # Test GESL to EHSS (reverse)
        gesl_3 = LanguageLevel.GESL_3
        ehss_from_gesl = LanguageLevel.get_equivalent_levels(gesl_3, "EHSS")

        # Should be equivalent mappings
        assert len(gesl_from_ehss) == 1
        assert len(ehss_from_gesl) == 1
        assert gesl_from_ehss[0].level_num == 3
        assert ehss_from_gesl[0].level_num == 3

    def test_can_transfer_to(self):
        """Test transfer capability validation."""
        # IEAP 1 student should be able to transfer to EHSS 4, 5, 6
        ieap_1 = LanguageLevel.IEAP_1

        assert LanguageLevel.can_transfer_to(ieap_1, "EHSS", 4)
        assert LanguageLevel.can_transfer_to(ieap_1, "EHSS", 5)
        assert LanguageLevel.can_transfer_to(ieap_1, "EHSS", 6)

        # Should not be able to transfer to lower levels
        assert not LanguageLevel.can_transfer_to(ieap_1, "EHSS", 3)

        # Should not be able to transfer to much higher levels
        assert not LanguageLevel.can_transfer_to(ieap_1, "EHSS", 9)

    def test_course_code_generation(self):
        """Test course code generation for levels."""
        ehss_5 = LanguageLevel.EHSS_5
        course_code = LanguageLevel.get_course_code_for_level(ehss_5)
        assert course_code == "EHSS-05"

        ehss_12 = LanguageLevel.EHSS_12
        course_code = LanguageLevel.get_course_code_for_level(ehss_12)
        assert course_code == "EHSS-12"

        # Test pre-beginner level
        ieap_pre = LanguageLevel.IEAP_PRE
        course_code = LanguageLevel.get_course_code_for_level(ieap_pre)
        assert course_code == "IEAP-PRE"

    def test_no_equivalency_between_unrelated_programs(self):
        """Test that unrelated programs have no equivalency."""
        # Weekend Express should not have equivalency to EHSS
        w_expr_1 = LanguageLevel.W_EXPR_1
        ehss_equivalents = LanguageLevel.get_equivalent_levels(w_expr_1, "EHSS")
        assert len(ehss_equivalents) == 0

    def test_level_equality_and_hashing(self):
        """Test level equality and hashing for set operations."""
        level1 = LanguageLevel.EHSS_5
        level2 = LanguageLevel.get_level_by_program_and_num("EHSS", 5)

        assert level1 == level2
        assert hash(level1) == hash(level2)

        # Different levels should not be equal
        assert level1 != LanguageLevel.EHSS_6
        assert level1 != LanguageLevel.GESL_5

    def test_edge_cases(self):
        """Test edge cases in level operations."""
        # Test with negative level numbers (pre-beginner levels)
        ieap_pre = LanguageLevel.IEAP_PRE
        assert ieap_pre.level_num == -2

        ieap_beg = LanguageLevel.IEAP_BEG
        assert ieap_beg.level_num == -1

        # Test next level from pre-beginner
        next_from_pre = LanguageLevel.get_next_level(ieap_pre)
        assert next_from_pre == ieap_beg

        # Test get_equivalent_levels with empty result
        pt_level = LanguageLevel.PRE_B1
        equivalents = LanguageLevel.get_equivalent_levels(pt_level, "EHSS")
        assert len(equivalents) == 0

    def test_invalid_transfer_scenarios(self):
        """Test invalid transfer scenarios."""
        ieap_1 = LanguageLevel.IEAP_1

        # Invalid program
        assert not LanguageLevel.can_transfer_to(ieap_1, "INVALID_PROGRAM", 1)

        # Invalid target level
        assert not LanguageLevel.can_transfer_to(ieap_1, "EHSS", 99)

        # Same program transfer (should be False for this level)
        assert not LanguageLevel.can_transfer_to(ieap_1, "IEAP", 2)
