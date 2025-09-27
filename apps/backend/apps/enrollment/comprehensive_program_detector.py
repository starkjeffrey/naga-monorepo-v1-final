"""Comprehensive Program Detection Service

This service analyzes every term of a student's career to detect program periods for:
1. Academic Majors (TESOL, Business, Finance, Tourism, International Relations)
2. Language Programs (IEAP, GESL, EHSS)

PRINCIPLE: Each ProgramEnrollment record represents ONE continuous period in ONE specific program.

Examples:
- Academic: TESOL 2015T3→2015T3, then Business 2016T1→2021T2 (2 records)
- Language: IEAP 2009T1→2010T2, then GESL 2010T3→2012T1, then EHSS 2012T2→2013T1 (3 records)

This enables accurate program efficiency calculations and progression tracking.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProgramPeriod:
    """Represents a continuous period in a single specific program."""

    program_type: str  # 'academic' or 'language'
    program_name: str  # 'TESOL', 'BA_BUSINESS', 'IEAP', 'GESL', etc.
    start_term: str
    end_term: str
    start_term_number: int
    end_term_number: int
    signature_courses_found: list[str]
    total_terms: int
    entry_level: str | None = None  # For language programs
    finishing_level: str | None = None  # For language programs


@dataclass
class StudentProgramHistory:
    """Complete program history for a student (both academic and language)."""

    student_id: str
    academic_periods: list[ProgramPeriod]
    language_periods: list[ProgramPeriod]
    foundation_terms: int
    total_academic_switches: int
    total_language_switches: int
    final_academic_major: str | None
    final_language_program: str | None
    terms_analyzed: int


class ComprehensiveProgramConfiguration:
    """Configuration for both academic and language program detection."""

    # Academic Major Signature Courses
    ACADEMIC_SIGNATURE_COURSES = {
        "TESOL": {
            "ENGL-200A",
            "EDUC-400",
            "ENGL-302A",
            "EDUC-301",
            "EDUC-401",
            "EDUC-404",
            "EDUC-403",
            "EDUC-405",
            "ENGL-401A",
            "EDUC-408",
            "ENGL-140",
            "PHIL-213",
            "EDUC-407",
            "ENGL-130",
            "ENGL-403",
            "ENGL-306",
            "ENGL-301",
            "ENGL-303",
            "ENGL-200",
            "LIT-325",
            "ENGL-450",
            "EDUC-300",
            "PSYC-313",
            "ENGL-201A",
        },
        "BA_BUSINESS": {
            "BUS-464",
            "BUS-465",
            "BUS-425",
            "BUS-460",
            "BUS-463",
            "BUS-489",
            "ECON-212",
            "MGT-489",
            "BUS-360",
            "BUS-461",
            "MGT-467",
        },
        "BA_FINANCE": {
            "FIN-360",
            "ECON-425",
            "FIN-445",
            "FIN-444",
            "FIN-442",
            "FIN-443",
            "ECON-449",
            "ECON-456",
            "FIN-453",
            "FIN-489",
            "FIN-442A",
        },
        "BA_TOURISM": {
            "THM-431",
            "THM-323",
            "THM-321",
            "THM-411",
            "THM-322",
            "THM-332",
            "THM-413",
            "THM-312",
            "THM-324",
            "THM-422",
            "THM-215",
            "THM-314",
            "THM-225",
            "THM-331",
            "THM-313",
            "THM-421",
            "THM-423",
            "THM-412",
            "THM-333",
            "THM-424",
            "THM-414",
            "THM-432",
            "THM-433",
        },
        "BA_INTERNATIONAL_RELATIONS": {
            "PAD-110",
            "POL-405",
            "POL-413",
            "POL-302",
            "LAW-301",
            "SOC-429",
            "IR-480",
            "IR-485",
            "ECON-455",
            "POL-304",
            "ECON-368",
            "LAW-304",
            "ECON-310",
            "LAW-305",
            "ECON-459",
            "IR-479",
            "IR-481",
            "IR-489",
            "POL-305",
            "IR-482",
            "POL-306",
            "PA-110",
            "PHIL-210",
            "POL-120",
        },
    }

    # Language Program Course Patterns
    LANGUAGE_PROGRAM_PATTERNS = {
        "IEAP": r"^IEAP-\d+$",  # IEAP-01, IEAP-02, etc.
        "GESL": r"^GESL-\d+$",  # GESL-01, GESL-02, etc.
        "EHSS": r"^EHSS-\d+$",  # EHSS-01, EHSS-02, etc.
    }

    # Language Level Progressions
    LANGUAGE_LEVEL_PROGRESSIONS = {
        "IEAP": ["IEAP-01", "IEAP-02", "IEAP-03", "IEAP-04", "IEAP-05"],
        "GESL": ["GESL-01", "GESL-02", "GESL-03", "GESL-04", "GESL-05", "GESL-06"],
        "EHSS": ["EHSS-01", "EHSS-02", "EHSS-03"],
    }

    def __init__(self):
        self.academic_course_to_major = self._build_academic_course_map()
        self.all_academic_signature_courses = frozenset().union(*self.ACADEMIC_SIGNATURE_COURSES.values())
        self.all_language_levels = set()
        for levels in self.LANGUAGE_LEVEL_PROGRESSIONS.values():
            self.all_language_levels.update(levels)

    def _build_academic_course_map(self) -> dict[str, str]:
        """Build course-to-major lookup map for academic courses."""
        course_to_major: dict[str, str] = {}
        for major, courses in self.ACADEMIC_SIGNATURE_COURSES.items():
            for course in courses:
                if course in course_to_major:
                    logger.warning(
                        "Academic course %s appears in multiple majors: %s and %s",
                        course,
                        course_to_major[course],
                        major,
                    )
                course_to_major[course] = major
        return course_to_major

    def detect_academic_major(self, courses: list[str]) -> str | None:
        """Detect academic major from courses (single major or None)."""
        detected_majors = set()
        for course in courses:
            if course in self.academic_course_to_major:
                detected_majors.add(self.academic_course_to_major[course])

        if len(detected_majors) == 1:
            return detected_majors.pop()
        if len(detected_majors) > 1:
            logger.warning("Multiple academic majors detected: %s", detected_majors)
            return None
        return None

    def detect_language_program(self, courses: list[str]) -> str | None:
        """Detect language program from courses."""
        detected_programs = set()
        for course in courses:
            for program, levels in self.LANGUAGE_LEVEL_PROGRESSIONS.items():
                if course in levels:
                    detected_programs.add(program)
                    break

        if len(detected_programs) == 1:
            return detected_programs.pop()
        if len(detected_programs) > 1:
            logger.warning("Multiple language programs detected: %s", detected_programs)
            return None
        return None

    def get_language_levels_for_program(self, program: str, courses: list[str]) -> tuple[str | None, str | None]:
        """Get entry and finishing levels for a language program."""
        if program not in self.LANGUAGE_LEVEL_PROGRESSIONS:
            return None, None

        program_levels = self.LANGUAGE_LEVEL_PROGRESSIONS[program]
        found_levels = [course for course in courses if course in program_levels]

        if not found_levels:
            return None, None

        # Sort by level progression
        found_levels_sorted = sorted(
            found_levels,
            key=lambda x: program_levels.index(x) if x in program_levels else 999,
        )

        entry_level = found_levels_sorted[0]
        finishing_level = found_levels_sorted[-1]

        return entry_level, finishing_level


class TermByTermProgramAnalyzer:
    """Analyzes student enrollment data term by term for all program types."""

    def __init__(self, config: ComprehensiveProgramConfiguration):
        self.config = config

    def analyze_student_complete_history(self, student_id: str, enrollments) -> StudentProgramHistory:
        """Analyze complete program history (academic + language) for a student."""
        # Group enrollments by term
        term_data = self._group_enrollments_by_term(enrollments)
        if not term_data:
            return self._empty_history(student_id)

        # Build term-by-term timeline
        sorted_terms = sorted(term_data.keys())
        program_timeline = self._build_program_timeline(sorted_terms, term_data)

        # Extract academic major periods
        academic_periods = self._extract_academic_periods(program_timeline)

        # Extract language program periods
        language_periods = self._extract_language_periods(program_timeline, term_data)

        # Count foundation terms
        foundation_terms = self._count_foundation_terms(program_timeline)

        return StudentProgramHistory(
            student_id=student_id,
            academic_periods=academic_periods,
            language_periods=language_periods,
            foundation_terms=foundation_terms,
            total_academic_switches=(len(academic_periods) - 1 if len(academic_periods) > 1 else 0),
            total_language_switches=(len(language_periods) - 1 if len(language_periods) > 1 else 0),
            final_academic_major=(academic_periods[-1].program_name if academic_periods else None),
            final_language_program=(language_periods[-1].program_name if language_periods else None),
            terms_analyzed=len(program_timeline),
        )

    def _empty_history(self, student_id: str) -> StudentProgramHistory:
        """Return empty history for students with no data."""
        return StudentProgramHistory(
            student_id=student_id,
            academic_periods=[],
            language_periods=[],
            foundation_terms=0,
            total_academic_switches=0,
            total_language_switches=0,
            final_academic_major=None,
            final_language_program=None,
            terms_analyzed=0,
        )

    def _group_enrollments_by_term(self, enrollments) -> dict[str, list[str]]:
        """Group enrollments by term and extract course codes."""
        term_courses = defaultdict(list)

        for enrollment in enrollments:
            if (
                hasattr(enrollment.class_header, "course")
                and enrollment.class_header.course
                and hasattr(enrollment.class_header, "term")
            ):
                term_name = enrollment.class_header.term.code
                course_code = enrollment.class_header.course.code

                if course_code:  # Skip null courses
                    term_courses[term_name].append(course_code)

        # Remove duplicates
        return {term: list(set(courses)) for term, courses in term_courses.items()}

    def _build_program_timeline(self, sorted_terms: list[str], term_data: dict[str, list[str]]) -> list[dict]:
        """Build timeline of program detection for each term."""
        timeline = []

        for i, term in enumerate(sorted_terms):
            courses = term_data[term]
            academic_major = self.config.detect_academic_major(courses)
            language_program = self.config.detect_language_program(courses)

            # Get signature courses found
            academic_signature_courses = [
                course for course in courses if course in self.config.all_academic_signature_courses
            ]

            language_courses = [course for course in courses if course in self.config.all_language_levels]

            timeline.append(
                {
                    "term_number": i + 1,
                    "term_name": term,
                    "courses": courses,
                    "academic_major": academic_major,
                    "language_program": language_program,
                    "academic_signature_courses": academic_signature_courses,
                    "language_courses": language_courses,
                },
            )

        return timeline

    def _extract_academic_periods(self, timeline: list[dict]) -> list[ProgramPeriod]:
        """Extract continuous academic major periods."""
        periods = []
        current_period = None

        for entry in timeline:
            detected_major = entry["academic_major"]

            if detected_major:  # Academic major detected
                if current_period is None:
                    # Start new academic period
                    current_period = {
                        "major": detected_major,
                        "start_term": entry["term_name"],
                        "start_term_number": entry["term_number"],
                        "signature_courses": entry["academic_signature_courses"].copy(),
                        "term_count": 1,
                    }
                elif current_period["major"] == detected_major:
                    # Continue current academic period
                    current_period["term_count"] += 1
                    current_period["signature_courses"].extend(entry["academic_signature_courses"])
                else:
                    # Academic major switch - end current period
                    periods.append(self._create_academic_period(current_period, timeline, entry["term_number"] - 2))

                    # Start new academic period
                    current_period = {
                        "major": detected_major,
                        "start_term": entry["term_name"],
                        "start_term_number": entry["term_number"],
                        "signature_courses": entry["academic_signature_courses"].copy(),
                        "term_count": 1,
                    }
            # No academic major detected
            elif current_period is not None:
                current_period["term_count"] += 1

        # Close final academic period
        if current_period is not None:
            periods.append(self._create_academic_period(current_period, timeline, len(timeline) - 1))

        return periods

    def _extract_language_periods(self, timeline: list[dict], term_data: dict[str, list[str]]) -> list[ProgramPeriod]:
        """Extract continuous language program periods."""
        periods = []
        current_period = None

        for entry in timeline:
            detected_program = entry["language_program"]

            if detected_program:  # Language program detected
                if current_period is None:
                    # Start new language period
                    current_period = {
                        "program": detected_program,
                        "start_term": entry["term_name"],
                        "start_term_number": entry["term_number"],
                        "language_courses": entry["language_courses"].copy(),
                        "term_count": 1,
                    }
                elif current_period["program"] == detected_program:
                    # Continue current language period
                    current_period["term_count"] += 1
                    current_period["language_courses"].extend(entry["language_courses"])
                else:
                    # Language program switch - end current period
                    periods.append(self._create_language_period(current_period, timeline, entry["term_number"] - 2))

                    # Start new language period
                    current_period = {
                        "program": detected_program,
                        "start_term": entry["term_name"],
                        "start_term_number": entry["term_number"],
                        "language_courses": entry["language_courses"].copy(),
                        "term_count": 1,
                    }
            # No language program detected
            elif current_period is not None:
                current_period["term_count"] += 1

        # Close final language period
        if current_period is not None:
            periods.append(self._create_language_period(current_period, timeline, len(timeline) - 1))

        return periods

    def _create_academic_period(self, period_data: dict, timeline: list[dict], end_index: int) -> ProgramPeriod:
        """Create academic program period object."""
        return ProgramPeriod(
            program_type="academic",
            program_name=period_data["major"],
            start_term=period_data["start_term"],
            end_term=timeline[end_index]["term_name"],
            start_term_number=period_data["start_term_number"],
            end_term_number=end_index + 1,
            signature_courses_found=list(set(period_data["signature_courses"])),
            total_terms=period_data["term_count"],
        )

    def _create_language_period(self, period_data: dict, timeline: list[dict], end_index: int) -> ProgramPeriod:
        """Create language program period object."""
        all_language_courses = list(set(period_data["language_courses"]))
        entry_level, finishing_level = self.config.get_language_levels_for_program(
            period_data["program"],
            all_language_courses,
        )

        return ProgramPeriod(
            program_type="language",
            program_name=period_data["program"],
            start_term=period_data["start_term"],
            end_term=timeline[end_index]["term_name"],
            start_term_number=period_data["start_term_number"],
            end_term_number=end_index + 1,
            signature_courses_found=all_language_courses,
            total_terms=period_data["term_count"],
            entry_level=entry_level,
            finishing_level=finishing_level,
        )

    def _count_foundation_terms(self, timeline: list[dict]) -> int:
        """Count foundation terms before first major/program detection."""
        foundation_terms = 0
        for entry in timeline:
            if entry["academic_major"] or entry["language_program"]:
                break
            foundation_terms += 1
        return foundation_terms


class ComprehensiveProgramDetectionService:
    """Main service for comprehensive program detection (academic + language)."""

    def __init__(self) -> None:
        self.config = ComprehensiveProgramConfiguration()
        self.analyzer = TermByTermProgramAnalyzer(self.config)
        self.stats: dict[str, Any] = {
            "students_analyzed": 0,
            "students_with_academic_majors": 0,
            "students_with_language_programs": 0,
            "students_with_academic_switches": 0,
            "students_with_language_switches": 0,
            "academic_periods_created": 0,
            "language_periods_created": 0,
            "academic_major_distribution": defaultdict(int),
            "language_program_distribution": defaultdict(int),
            "academic_switch_patterns": defaultdict(int),
            "language_switch_patterns": defaultdict(int),
        }

    def analyze_student_programs(self, student_id: str, enrollments) -> StudentProgramHistory:
        """Analyze complete program history for a single student."""
        history = self.analyzer.analyze_student_complete_history(student_id, enrollments)

        # Update statistics
        self._update_stats(history)

        return history

    def bulk_analyze_student_programs(self, student_enrollments: dict[int, list]) -> dict[int, StudentProgramHistory]:
        """Bulk analyze program histories for multiple students."""
        results = {}

        for student_id, enrollments in student_enrollments.items():
            history = self.analyze_student_programs(str(student_id), enrollments)
            results[student_id] = history

        logger.info(
            "Bulk program analysis completed: %d students, %d with academic majors, %d with language programs",
            self.stats["students_analyzed"],
            self.stats["students_with_academic_majors"],
            self.stats["students_with_language_programs"],
        )

        return results

    def _update_stats(self, history: StudentProgramHistory):
        """Update detection statistics."""
        self.stats["students_analyzed"] += 1

        if history.academic_periods:
            self.stats["students_with_academic_majors"] += 1
            self.stats["academic_periods_created"] += len(history.academic_periods)

            if history.total_academic_switches > 0:
                self.stats["students_with_academic_switches"] += 1

            # Track academic distribution and patterns
            for period in history.academic_periods:
                self.stats["academic_major_distribution"][period.program_name] += 1

            if len(history.academic_periods) > 1:
                pattern = " → ".join([p.program_name for p in history.academic_periods])
                self.stats["academic_switch_patterns"][pattern] += 1

        if history.language_periods:
            self.stats["students_with_language_programs"] += 1
            self.stats["language_periods_created"] += len(history.language_periods)

            if history.total_language_switches > 0:
                self.stats["students_with_language_switches"] += 1

            # Track language distribution and patterns
            for period in history.language_periods:
                self.stats["language_program_distribution"][period.program_name] += 1

            if len(history.language_periods) > 1:
                pattern = " → ".join([p.program_name for p in history.language_periods])
                self.stats["language_switch_patterns"][pattern] += 1

    def get_comprehensive_stats(self) -> dict:
        """Get comprehensive detection statistics."""
        return {
            "students_analyzed": self.stats["students_analyzed"],
            "students_with_academic_majors": self.stats["students_with_academic_majors"],
            "students_with_language_programs": self.stats["students_with_language_programs"],
            "students_with_academic_switches": self.stats["students_with_academic_switches"],
            "students_with_language_switches": self.stats["students_with_language_switches"],
            "academic_periods_created": self.stats["academic_periods_created"],
            "language_periods_created": self.stats["language_periods_created"],
            "academic_switch_rate": (
                self.stats["students_with_academic_switches"] / self.stats["students_with_academic_majors"]
                if self.stats["students_with_academic_majors"] > 0
                else 0
            ),
            "language_switch_rate": (
                self.stats["students_with_language_switches"] / self.stats["students_with_language_programs"]
                if self.stats["students_with_language_programs"] > 0
                else 0
            ),
            "academic_major_distribution": dict(self.stats["academic_major_distribution"]),
            "language_program_distribution": dict(self.stats["language_program_distribution"]),
            "academic_switch_patterns": dict(self.stats["academic_switch_patterns"]),
            "language_switch_patterns": dict(self.stats["language_switch_patterns"]),
        }
