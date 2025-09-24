"""Management command to load ProgramEnrollment data from course enrollment CSV.

This command analyzes historical course enrollments to create ProgramEnrollment
records, deducing majors and tracking program transitions.
"""

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Cycle, Division, Major, Term
from apps.enrollment.models import ProgramEnrollment
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Load program enrollments from course enrollment data."""

    help = "Load ProgramEnrollment records by analyzing course enrollment patterns"

    # Section to program mapping
    SECTION_PROGRAM_MAP = {
        "87": {"division": "ACADEMIC", "cycle": "BA", "name_pattern": "Bachelor of %s"},
        "147": {"division": "ACADEMIC", "cycle": "MA", "name_pattern": "Master of %s"},
        "632": {
            "division": "LANGUAGE",
            "cycle": "HS",
            "name_pattern": "EHSS High School",
        },
        "688": {
            "division": "LANGUAGE",
            "cycle": "CERT",
            "name_pattern": "Adult English Program",
        },
        "582": {
            "division": "LANGUAGE",
            "cycle": "PREP",
            "name_pattern": "IEAP - Academic English",
        },
    }

    # Legacy major code mapping (SelMajor values)
    LEGACY_MAJOR_CODES = {
        "540": "International Relations",
        "2400": "TESOL",
        "2301": "Business Administration",
        "4060": "Finance & Banking",  # 7 students
        "4316": "Hospitality and Tourism",  # 2 students
        "4584": "Hospitality and Tourism",  # 1 student - might be same as 4316
        "0": None,  # No major selected
    }

    # BatchIdForMaster prefix mapping (left 3 characters)
    BATCHID_MAJOR_CODES = {
        "BAD": "Business Administration",
        "TES": "TESOL",
        "FIN": "Finance & Banking",
        "TOU": "Hospitality and Tourism",
        "INT": "International Relations",
    }

    # SIGNATURE COURSE MAPPINGS - Specific courses that definitively indicate a major
    # Based on comprehensive analysis of course requirements and unique course offerings
    SIGNATURE_COURSE_MAPPINGS = {
        # International Relations signature courses (high confidence)
        "SOC-429": "IR",  # Research Methods - IR signature course
        "IR-480": "IR",
        "IR-485": "IR",
        "IR-479": "IR",
        "IR-481": "IR",
        "IR-489": "IR",
        "IR-482": "IR",
        "POL-405": "IR",
        "POL-413": "IR",
        "POL-302": "IR",
        "POL-304": "IR",
        "POL-305": "IR",
        "POL-306": "IR",
        "POL-120": "IR",
        "LAW-301": "IR",
        "LAW-304": "IR",
        "LAW-305": "IR",
        "PAD-110": "IR",
        "PA-110": "IR",
        "PHIL-210": "IR",
        "ECON-455": "IR",
        "ECON-368": "IR",
        "ECON-310": "IR",
        "ECON-459": "IR",
        # TESOL signature courses (high confidence)
        "ENGL-200A": "TESOL",
        "EDUC-400": "TESOL",
        "ENGL-302A": "TESOL",
        "EDUC-301": "TESOL",
        "EDUC-401": "TESOL",
        "EDUC-404": "TESOL",
        "EDUC-403": "TESOL",
        "EDUC-405": "TESOL",
        "ENGL-401A": "TESOL",
        "EDUC-408": "TESOL",
        "EDUC-407": "TESOL",
        "ENGL-403": "TESOL",
        "ENGL-306": "TESOL",
        "ENGL-301": "TESOL",
        "ENGL-303": "TESOL",
        "LIT-325": "TESOL",
        "ENGL-450": "TESOL",
        "EDUC-300": "TESOL",
        "PSYC-313": "TESOL",
        "ENGL-201A": "TESOL",
        # Business Administration signature courses
        "BUS-464": "BUSADMIN",
        "BUS-465": "BUSADMIN",
        "BUS-425": "BUSADMIN",
        "BUS-460": "BUSADMIN",
        "BUS-463": "BUSADMIN",
        "BUS-489": "BUSADMIN",
        "MGT-489": "BUSADMIN",
        "BUS-360": "BUSADMIN",
        "BUS-461": "BUSADMIN",
        "MGT-467": "BUSADMIN",
        # Finance & Banking signature courses
        "FIN-360": "FIN-BANK",
        "FIN-445": "FIN-BANK",
        "FIN-444": "FIN-BANK",
        "FIN-442": "FIN-BANK",
        "FIN-443": "FIN-BANK",
        "FIN-453": "FIN-BANK",
        "FIN-489": "FIN-BANK",
        "FIN-442A": "FIN-BANK",
        "ECON-425": "FIN-BANK",
        "ECON-449": "FIN-BANK",
        "ECON-456": "FIN-BANK",
        # Tourism & Hospitality signature courses
        "THM-431": "TOUR-HOSP",
        "THM-323": "TOUR-HOSP",
        "THM-321": "TOUR-HOSP",
        "THM-411": "TOUR-HOSP",
        "THM-322": "TOUR-HOSP",
        "THM-332": "TOUR-HOSP",
        "THM-413": "TOUR-HOSP",
        "THM-312": "TOUR-HOSP",
        "THM-324": "TOUR-HOSP",
        "THM-422": "TOUR-HOSP",
        "THM-215": "TOUR-HOSP",
        "THM-314": "TOUR-HOSP",
        "THM-225": "TOUR-HOSP",
        "THM-331": "TOUR-HOSP",
        "THM-313": "TOUR-HOSP",
        "THM-421": "TOUR-HOSP",
        "THM-423": "TOUR-HOSP",
        "THM-412": "TOUR-HOSP",
        "THM-333": "TOUR-HOSP",
        "THM-424": "TOUR-HOSP",
        "THM-414": "TOUR-HOSP",
        "THM-432": "TOUR-HOSP",
        "THM-433": "TOUR-HOSP",
        # MBA signature courses
        "MGT-505": "MBA",
        "ECON-515": "MBA",
        "MGT-535": "MBA",
        "FIN-540": "MBA",
        "FIN-571": "MBA",
        "MGT-545": "MBA",
        "MGT-578": "MBA",
        "MGT-582": "MBA",
        "MGT-585": "MBA",
        "BUS-520": "MBA",
        "ECON-544": "MBA",
        "ACCT-545": "MBA",
        "MKT-567": "MBA",
        "MKT-569": "MBA",
        "MGT-570": "MBA",
        "MKT-571": "MBA",
        "FIN-574": "MBA",
        "MGT-597": "MBA",
        "MGT-598": "MBA",
        "MGT-599": "MBA",
    }

    # REMOVED: COURSE_PREFIX_TO_MAJOR was erroneous logic that created fake majors
    # Only the 5 official signature course mappings should be used for academic major deduction

    def add_arguments(self, parser):
        """Add command arguments."""
        super().add_arguments(parser)
        parser.add_argument("csv_file", type=str, help="Path to the course enrollment CSV file")
        parser.add_argument(
            "--student-id",
            type=str,
            help="Process only a specific student ID for testing",
        )
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=0.3,
            help="Minimum confidence for major deduction (0-1)",
        )
        parser.add_argument(
            "--students-csv",
            type=str,
            help="Path to students CSV with SelMajor data (optional)",
        )

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories."""
        return [
            "STUDENT_NOT_FOUND",
            "TERM_NOT_FOUND",
            "MAJOR_NOT_FOUND",
            "INVALID_DATA",
            "DUPLICATE_ENROLLMENT",
            "STUDENT_PROCESSING_ERROR",
        ]

    def execute_migration(self, *args, **options):
        """Execute the actual migration logic."""
        csv_file = options["csv_file"]
        student_filter = options.get("student_id")
        self.confidence_threshold = options["confidence_threshold"]

        self.stdout.write(f"Loading program enrollments from {csv_file}")

        # Record input stats
        self.audit_data["summary"]["input"]["csv_file"] = csv_file
        self.audit_data["summary"]["input"]["confidence_threshold"] = self.confidence_threshold

        # Read and group enrollments by student
        student_enrollments = self.read_enrollments(csv_file, student_filter)

        # Process each student
        total_students = len(student_enrollments)
        self.audit_data["summary"]["input"]["total_students"] = total_students
        self.stdout.write(f"Processing {total_students} students...")

        created_count = 0
        error_count = 0

        for student_id, enrollments in student_enrollments.items():
            try:
                created = self.process_student_enrollments(student_id, enrollments)
                created_count += created
                if created > 0:
                    self.record_success("program_enrollments_created", created)
            except Exception as e:
                self.record_rejection(
                    "STUDENT_PROCESSING_ERROR",
                    student_id,
                    {"error": str(e), "student_id": student_id},
                )
                error_count += 1

        # Final summary
        self.audit_data["summary"]["output"]["total_processed"] = total_students
        self.audit_data["summary"]["output"]["errors"] = error_count

        return {
            "success": True,
            "program_enrollments_created": created_count,
            "errors": error_count,
        }

    def read_enrollments(self, csv_file: str, student_filter: str | None = None) -> dict:
        """Read enrollments from CSV and group by student."""
        student_enrollments = defaultdict(list)

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                student_id = row["ID"]

                if student_filter and student_id != student_filter:
                    continue

                # Parse enrollment data
                enrollment = {
                    "student_id": student_id,
                    "term": row["parsed_termid"],
                    "course_code": row["parsed_coursecode"],
                    "section": row["section"],
                    "grade": row["Grade"].strip(),
                    "credit": row["Credit"],
                    "grade_point": row["GradePoint"],
                }

                student_enrollments[student_id].append(enrollment)

        return student_enrollments

    def process_student_enrollments(self, student_id: str, enrollments: list[dict]) -> int:
        """Process enrollments for a single student with proper major progression and term grouping.

        This method:
        1. Groups enrollments by term and detects majors chronologically
        2. Groups consecutive terms by major to create enrollment periods
        3. Creates ProgramEnrollment records for each major period with proper term counts/dates
        """
        # Get or skip student
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            self.record_rejection("STUDENT_NOT_FOUND", student_id, f"student_id: {student_id}")
            return 0

        # Group enrollments by term and section
        term_programs = self.group_enrollments_by_program(enrollments)
        sorted_terms = sorted(term_programs.keys())

        # Try to get legacy major for fallback
        try:
            legacy_major_name = self.get_legacy_major_from_batchid_and_selmajor(student_id)
        except Exception:
            legacy_major_name = None

        # Step 1: Detect major for each term and build major progression
        major_progression = {}  # {term: major_name}

        for term in sorted_terms:
            term_data = term_programs[term]
            section = term_data["primary_section"]
            courses = term_data["courses"]

            # Skip non-academic sections
            if not section or section not in self.SECTION_PROGRAM_MAP:
                continue

            program_info = self.SECTION_PROGRAM_MAP[section]

            # Handle language programs separately - they have fixed majors
            if program_info["division"] == "LANGUAGE":
                major_name = program_info["name_pattern"]
                major_progression[term] = ("LANGUAGE", major_name, program_info)
                continue

            # For academic programs, detect major from signature courses
            detected_major = self._detect_major_from_term_courses(courses)

            if detected_major:
                major_name = detected_major["major"]
                # Use string format for Bachelor/Master patterns
                if "%s" in program_info["name_pattern"]:
                    formatted_major = program_info["name_pattern"] % major_name
                else:
                    formatted_major = major_name
                major_progression[term] = ("ACADEMIC", formatted_major, program_info)
            elif legacy_major_name:
                # Fall back to legacy major
                cycle = program_info.get("cycle", "BA")
                if cycle == "BA":
                    formatted_major = f"Bachelor of {legacy_major_name}"
                elif cycle == "MA":
                    formatted_major = f"Master of {legacy_major_name}"
                else:
                    formatted_major = legacy_major_name
                major_progression[term] = ("ACADEMIC", formatted_major, program_info)

        # Step 2: Group consecutive terms by major into enrollment periods
        enrollment_periods = []  # [(major_name, program_info, [terms], division)]
        current_major = None
        current_terms = []
        current_program_info = None
        current_division = None

        for term in sorted_terms:
            if term not in major_progression:
                continue

            division, major_name, program_info = major_progression[term]

            # If major changes, save current period and start new one
            if current_major != major_name:
                # Save previous period
                if current_major and current_terms:
                    enrollment_periods.append(
                        (
                            current_major,
                            current_program_info,
                            current_terms.copy(),
                            current_division,
                        ),
                    )

                # Start new period
                current_major = major_name
                current_program_info = program_info
                current_terms = [term]
                current_division = division
            else:
                # Same major, add term to current period
                current_terms.append(term)

        # Don't forget the last period
        if current_major and current_terms:
            enrollment_periods.append((current_major, current_program_info, current_terms, current_division))

        # Step 3: Create ProgramEnrollment records for each period
        created_count = 0

        for period_data in enrollment_periods:
            major_name, program_info, terms_list, division = period_data
            if program_info is None:
                continue
            # Build term_periods dict for this major period
            term_periods = {}
            for term in terms_list:
                if term in term_programs:
                    term_periods[term] = term_programs[term]

            if not term_periods:
                continue

            try:
                if division == "LANGUAGE":
                    # Create language program enrollment
                    success = self.create_language_program_enrollment(student, term_periods, program_info)
                else:
                    # Create academic program enrollment
                    enrollment = self.create_or_update_program_enrollment(
                        student,
                        major_name,
                        term_periods,
                        program_info,
                        is_new_major=True,
                    )

                if (division == "LANGUAGE" and success) or (division != "LANGUAGE" and enrollment):
                    created_count += 1
                    self.stdout.write(
                        f"✅ Created {division} enrollment: {major_name} "
                        f"({len(terms_list)} terms: {terms_list[0]}→{terms_list[-1]})",
                    )

            except Exception as e:
                self.record_rejection(
                    "ENROLLMENT_CREATION_ERROR",
                    f"{student.student_id}_{major_name}",
                    f"error: {e}, major: {major_name}",
                )

        return created_count

    def group_enrollments_by_program(self, enrollments: list[dict]) -> dict:
        """Group enrollments by term and identify program."""
        from typing import Any

        term_programs: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {"courses": [], "sections": set(), "credits": 0.0, "grade_points": 0.0}
        )

        for enrollment in enrollments:
            term = enrollment["term"]
            section = enrollment["section"]

            term_programs[term]["courses"].append(enrollment["course_code"])
            term_programs[term]["sections"].add(section)

            # Sum credits and grade points
            try:
                credits = float(enrollment["credit"] or 0)
                grade_points = float(enrollment["grade_point"] or 0)
                term_programs[term]["credits"] += credits
                term_programs[term]["grade_points"] += grade_points * credits
            except (ValueError, TypeError):
                pass

        # Determine primary section for each term
        for term_data in term_programs.values():
            sections = list(term_data["sections"])
            # Use most common section or first one
            term_data["primary_section"] = sections[0] if sections else None

        return term_programs

    def identify_program_periods(self, term_programs: dict) -> list[dict]:
        """Identify continuous program enrollment periods."""
        # First, group all terms by their program type (section)
        from typing import Any

        program_groups: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "terms": [],
                "all_courses": [],
                "total_credits": 0,
                "total_grade_points": 0,
                "term_data": {},
            },
        )

        # Sort terms chronologically
        sorted_terms = sorted(term_programs.keys())

        for term in sorted_terms:
            data = term_programs[term]
            section = data["primary_section"]

            if not section or section not in self.SECTION_PROGRAM_MAP:
                continue

            # Add to the appropriate program group
            group = program_groups[section]
            group["terms"].append(term)
            group["all_courses"].extend(data["courses"])
            group["total_credits"] += data["credits"]
            group["total_grade_points"] += data["grade_points"]
            group["term_data"][term] = data

        # Now create periods from the groups
        periods = []
        for section, group_data in program_groups.items():
            if not group_data["terms"]:
                continue

            program_info = self.SECTION_PROGRAM_MAP[section]

            # Sort the terms for this program
            sorted_group_terms = sorted(group_data["terms"])

            # Create one period for the entire program enrollment
            period = {
                "section": section,
                "division": program_info["division"],
                "cycle": program_info["cycle"],
                "start_term": sorted_group_terms[0],
                "end_term": sorted_group_terms[-1],
                "terms": sorted_group_terms,
                "all_courses": group_data["all_courses"],
                "total_credits": group_data["total_credits"],
                "total_grade_points": group_data["total_grade_points"],
            }

            periods.append(period)

        # Sort periods by start date
        periods.sort(key=lambda p: p["start_term"])

        return periods

    def create_program_enrollment(self, student: StudentProfile, period: dict, legacy_major=None) -> bool:
        """Create a ProgramEnrollment record for a period."""
        # Deduce or find the major
        major = self.determine_major(period, legacy_major)
        if not major:
            self.record_rejection(
                "MAJOR_NOT_FOUND",
                f"{student.student_id}_{period['section']}",
                f"student_id: {student.student_id}, section: {period['section']}",
            )
            return False

        # Get terms
        try:
            start_term = Term.objects.get(code=period["start_term"])
            end_term = Term.objects.get(code=period["end_term"])
        except Term.DoesNotExist as e:
            self.record_rejection(
                "TERM_NOT_FOUND",
                f"{student.student_id}_{period['start_term']}",
                f"student_id: {student.student_id}, term: {e}",
            )
            return False

        # Calculate GPA
        gpa = None
        if period["total_credits"] > 0:
            gpa = Decimal(str(period["total_grade_points"] / period["total_credits"])).quantize(Decimal("0.01"))

        # Determine status
        status = self.determine_enrollment_status(period, student)

        # Map division to the proper choice value
        division_choice = "LANG" if period["division"] == "LANGUAGE" else "ACAD"

        # Map cycle to the proper choice value
        cycle_map = {"BA": "BA", "MA": "MA", "HS": "HS", "CERT": "CERT", "PREP": "PREP"}
        cycle_choice = cycle_map.get(period["cycle"], "BA")

        # Create enrollment with all fields
        _enrollment, created = ProgramEnrollment.objects.get_or_create(
            student=student,
            program=major,
            start_date=start_term.start_date,
            defaults={
                "enrollment_type": ("LANG" if period["division"] == "LANGUAGE" else "ACAD"),
                "status": status,
                "end_date": end_term.end_date if status != "ACTIVE" else None,
                "start_term": start_term,
                "end_term": end_term if status != "ACTIVE" else None,
                "terms_active": len(period["terms"]),
                "is_system_generated": True,
                "notes": f"Generated from course enrollments. Sections: {period['section']}",
                # New enhanced fields
                "division": division_choice,
                "cycle": cycle_choice,
                "credits_earned": Decimal(str(period["total_credits"])),
                "gpa_at_exit": gpa if status != "ACTIVE" else None,
                "legacy_section_code": period["section"],
                "is_deduced": hasattr(major, "_was_deduced") and major._was_deduced,
                "deduction_confidence": (
                    Decimal(str(major._deduction_confidence)) if hasattr(major, "_deduction_confidence") else None
                ),
                "completion_percentage": 0,  # Will be calculated later
            },
        )

        return created

    def determine_major(self, period: dict, legacy_major=None) -> Major | None:
        """Determine the major for a program period."""
        program_info = self.SECTION_PROGRAM_MAP[period["section"]]

        if period["division"] == "LANGUAGE":
            # Language programs have fixed majors
            major_name = program_info["name_pattern"]
            was_deduced = False
            deduction_confidence = 0
        else:
            # Academic programs - try recent term analysis first, then full course analysis
            deduced = self.deduce_major_from_recent_terms(period)
            if deduced:
                method = deduced.get("method", "unknown")
                confidence = deduced["confidence"]

                # Enhanced logging for signature course detection
                if method == "recent_term_signature":
                    signature_courses = deduced.get("signature_courses", [])
                    detection_term = deduced.get("detection_term", "unknown")
                    self.stdout.write(
                        f"🎯 SIGNATURE COURSE DETECTION: {deduced['major']} "
                        f"(confidence: {confidence:.2f}) in term {detection_term} "
                        f"via courses: {', '.join(signature_courses)}",
                    )
                elif method == "signature_courses":
                    signature_courses = deduced.get("signature_courses", [])
                    self.stdout.write(
                        f"📚 SIGNATURE COURSE ANALYSIS: {deduced['major']} "
                        f"(confidence: {confidence:.2f}) via courses: {', '.join(signature_courses)}",
                    )
                else:
                    self.stdout.write(
                        f"📊 Major deduced: {deduced['major']} with confidence {confidence:.2f} using {method}",
                    )
            if deduced and deduced["confidence"] >= self.confidence_threshold:
                # Use deduced major with high confidence
                # Use string format for Bachelor/Master patterns
                if "%s" in program_info["name_pattern"]:
                    major_name = program_info["name_pattern"] % deduced["major"]
                else:
                    major_name = deduced["major"]
                was_deduced = True
                deduction_confidence = deduced["confidence"]
            elif legacy_major:
                # Fall back to legacy major if deduction failed
                if period["cycle"] == "BA":
                    major_name = f"Bachelor of {legacy_major}"
                elif period["cycle"] == "MA":
                    major_name = f"Master of {legacy_major}"
                else:
                    major_name = legacy_major
                was_deduced = False  # From legacy data, not deduced
                deduction_confidence = 0.5  # Medium confidence from legacy
            else:
                # Last resort: use unknown major names
                if period["cycle"] == "BA":
                    major_name = "Bachelor of Arts (Unknown)"
                elif period["cycle"] == "MA":
                    major_name = "Master of Arts (Unknown)"
                else:
                    major_name = program_info["name_pattern"]
                was_deduced = False
                deduction_confidence = 0

        # First, find or create the appropriate division and cycle
        division_name = "Language Division" if period["division"] == "LANGUAGE" else "Academic Division"
        division, _ = Division.objects.get_or_create(
            name=division_name,
            defaults={
                "short_name": period["division"][:10],
                "description": f"{division_name} programs",
            },
        )

        # Map cycle codes to proper names
        cycle_names = {
            "BA": "Bachelor's Degree",
            "MA": "Master's Degree",
            "HS": "High School",
            "CERT": "Certificate",
            "PREP": "Preparatory",
        }
        cycle_name = cycle_names.get(period["cycle"], period["cycle"])

        # Try to find cycle by short_name and division first
        cycle, _ = Cycle.objects.get_or_create(
            short_name=period["cycle"],
            division=division,
            defaults={
                "name": cycle_name,
                "description": f"{cycle_name} programs",
                "is_active": True,
            },
        )

        # Determine program type
        program_type = Major.ProgramType.LANGUAGE if period["division"] == "LANGUAGE" else Major.ProgramType.ACADEMIC

        # Map degree for academic programs
        degree_map = {"BA": Major.DegreeAwarded.BA, "MA": Major.DegreeAwarded.MA}
        if program_type == Major.ProgramType.ACADEMIC:
            degree_map.get(period["cycle"], Major.DegreeAwarded.NONE)
        else:
            # Language programs get CERT or NONE
            (Major.DegreeAwarded.CERT if period["cycle"] == "CERT" else Major.DegreeAwarded.NONE)

        # Find existing major by code (DO NOT CREATE NEW MAJORS)
        # For academic programs, use the official major codes from signature course mappings
        try:
            if period["division"] == "ACADEMIC":
                # Map major_name to official major code
                if major_name in ["IR", "International Relations"]:
                    major = Major.objects.get(code="IR")
                elif major_name in ["BUSADMIN", "Business Administration"]:
                    major = Major.objects.get(code="BUSADMIN")
                elif major_name in ["FIN-BANK", "Finance & Banking"]:
                    major = Major.objects.get(code="FIN-BANK")
                elif major_name in [
                    "TOUR-HOSP",
                    "Tourism & Hospitality",
                    "Hospitality and Tourism",
                ]:
                    major = Major.objects.get(code="TOUR-HOSP")
                elif major_name in ["TESOL"]:
                    major = Major.objects.get(code="TESOL")
                elif major_name in ["MBA"]:
                    major = Major.objects.get(code="MBA")
                else:
                    # Unknown academic major - skip this period
                    return None
            else:
                # For language programs, find by name
                major = Major.objects.get(
                    name=major_name,
                    cycle=cycle,
                    program_type=Major.ProgramType.LANGUAGE,
                )

        except Major.DoesNotExist:
            # Major doesn't exist - return None instead of creating fake majors
            return None

        # Add deduction metadata to major object for later use
        if period["division"] == "ACADEMIC":
            major._was_deduced = was_deduced
            major._deduction_confidence = deduction_confidence

        return major

    def deduce_major_from_courses(self, courses: list[str]) -> dict | None:
        """Enhanced major deduction using signature courses with recent term prioritization.

        Priority order:
        1. Signature courses (high confidence)
        2. Course prefix analysis (medium confidence)
        3. Fallback to unknown (low confidence)
        """
        if not courses:
            return None

        # Phase 1: Check for signature courses (HIGHEST PRIORITY)
        signature_majors = defaultdict(int)
        signature_courses_found = []

        for course_code in courses:
            if course_code in self.SIGNATURE_COURSE_MAPPINGS:
                major = self.SIGNATURE_COURSE_MAPPINGS[course_code]
                signature_majors[major] += 1
                signature_courses_found.append(course_code)

        # If signature courses found, use them with high confidence
        if signature_majors:
            # Find major with most signature courses
            most_signature_major = max(signature_majors, key=signature_majors.get)
            signature_count = signature_majors[most_signature_major]
            total_courses = len(courses)

            # High confidence for signature course detection
            confidence = min(0.95, 0.7 + (signature_count / total_courses) * 0.25)

            return {
                "major": most_signature_major,
                "confidence": confidence,
                "method": "signature_courses",
                "signature_courses": signature_courses_found,
                "signature_count": signature_count,
                "total_courses": total_courses,
            }

        # REMOVED: Phase 2 prefix analysis was erroneous logic that created fake majors
        # Academic majors should ONLY be deduced from signature courses provided by the user

        return None

    def deduce_major_from_recent_terms(self, period: dict) -> dict | None:
        """Enhanced major deduction prioritizing most recent term enrollments.

        This method looks at the student's most recent actual enrollments and derives
        the major from signature classes the student took (e.g., SOC-429 for International Relations).

        Args:
            period: Period data containing all courses and terms

        Returns:
            dict with major, confidence, and detection details, or None
        """
        if not period.get("terms") or not period.get("all_courses"):
            return None

        # Sort terms in reverse chronological order (most recent first)
        sorted_terms = sorted(period["terms"], reverse=True)

        # Analyze terms starting from most recent
        recent_term_limit = min(3, len(sorted_terms))  # Look at last 3 terms max

        for term_priority, term in enumerate(sorted_terms[:recent_term_limit]):
            # Get courses for this specific term from the period's term_data if available
            term_courses = []
            if "term_data" in period and term in period["term_data"]:
                term_courses = period["term_data"][term].get("courses", [])

            if not term_courses:
                continue

            # Try signature course detection for this term
            signature_result = self._detect_signature_courses_in_term(term_courses, term)
            if signature_result:
                # Boost confidence for more recent terms
                recency_boost = 1.0 - (term_priority * 0.1)  # 100%, 90%, 80% for terms 1,2,3
                signature_result["confidence"] = min(0.98, signature_result["confidence"] * recency_boost)
                signature_result["recent_term"] = term
                signature_result["term_priority"] = term_priority + 1
                return signature_result

        # If no signature courses in recent terms, fall back to analyzing all courses
        return self.deduce_major_from_courses(period["all_courses"])

    def _detect_signature_courses_in_term(self, courses: list[str], term: str) -> dict | None:
        """Detect signature courses within a single term.

        Args:
            courses: List of course codes for the term
            term: Term identifier

        Returns:
            dict with detection results or None
        """
        signature_majors = defaultdict(int)
        signature_courses_found = []

        for course_code in courses:
            if course_code in self.SIGNATURE_COURSE_MAPPINGS:
                major = self.SIGNATURE_COURSE_MAPPINGS[course_code]
                signature_majors[major] += 1
                signature_courses_found.append(course_code)

        if not signature_majors:
            return None

        # Find major with most signature courses in this term
        most_signature_major = max(signature_majors, key=signature_majors.get)
        signature_count = signature_majors[most_signature_major]

        # Very high confidence for signature courses in recent terms
        confidence = min(0.95, 0.8 + (signature_count / len(courses)) * 0.15)

        return {
            "major": most_signature_major,
            "confidence": confidence,
            "method": "recent_term_signature",
            "signature_courses": signature_courses_found,
            "signature_count": signature_count,
            "term_courses": len(courses),
            "detection_term": term,
        }

    def _detect_major_from_term_courses(self, courses: list[str]) -> dict | None:
        """Detect major from courses in a single term.

        Args:
            courses: List of course codes for the term

        Returns:
            dict with detection results or None
        """
        if not courses:
            return None

        # Check for signature courses first
        signature_majors = defaultdict(int)
        signature_courses_found = []

        for course_code in courses:
            if course_code in self.SIGNATURE_COURSE_MAPPINGS:
                major = self.SIGNATURE_COURSE_MAPPINGS[course_code]
                signature_majors[major] += 1
                signature_courses_found.append(course_code)

        if signature_majors:
            # Find major with most signature courses
            most_signature_major = max(signature_majors, key=signature_majors.get)
            signature_count = signature_majors[most_signature_major]

            return {
                "major": most_signature_major,
                "confidence": 0.95,  # High confidence for signature courses
                "method": "signature_courses",
                "signature_courses": signature_courses_found,
                "signature_count": signature_count,
            }

        return None

    def _get_previous_term(self, current_term: str) -> Term | None:
        """Get the previous term for a given term code."""
        try:
            current_term_obj = Term.objects.get(code=current_term)
            # Find the term that ends just before this one starts
            previous_term = Term.objects.filter(end_date__lt=current_term_obj.start_date).order_by("-end_date").first()
            return previous_term
        except Term.DoesNotExist:
            return None

    def create_or_update_program_enrollment(
        self,
        student: StudentProfile,
        major_name: str,
        term_periods: dict,
        program_info: dict,
        is_new_major: bool = False,
    ) -> ProgramEnrollment | None:
        """Create or update a ProgramEnrollment record with proper term calculations.

        Args:
            student: StudentProfile object
            major_name: Name of the major
            term_periods: Dict containing terms and enrollment data for this major
            program_info: Program configuration
            is_new_major: Whether this is a new major detection
        """
        try:
            # Get the major object or create it
            major = self.get_or_create_major(major_name, program_info)
            if not major:
                return None

            # Calculate the enrollment period based on actual terms enrolled
            terms_list = sorted(term_periods.keys())
            if not terms_list:
                return None

            # Get first and last terms
            first_term_code = terms_list[0]
            last_term_code = terms_list[-1]

            # Get term objects
            try:
                start_term = Term.objects.get(code=first_term_code)
                end_term = Term.objects.get(code=last_term_code)
            except Term.DoesNotExist:
                return None

            # Calculate total terms and status
            terms_active = len(terms_list)

            # Determine status based on term end dates (more accurate logic)
            today = timezone.now().date()

            # Check if any term end date is in the future (meaning currently enrolled)
            has_future_terms = any(
                Term.objects.filter(code=term_code, end_date__gt=today).exists() for term_code in terms_list
            )

            if has_future_terms:
                # Currently enrolled - has future or ongoing terms
                status = ProgramEnrollment.EnrollmentStatus.ACTIVE
                end_date = None
                end_term = None
            elif end_term.end_date >= today - timedelta(days=365):
                # Ended within last year - recently completed/inactive
                status = ProgramEnrollment.EnrollmentStatus.INACTIVE
                end_date = end_term.end_date
            else:
                # Ended more than a year ago - completed
                status = ProgramEnrollment.EnrollmentStatus.COMPLETED
                end_date = end_term.end_date

            # Create new enrollment with proper dates and term counts
            enrollment = ProgramEnrollment.objects.create(
                student=student,
                program=major,
                enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
                status=status,
                start_date=start_term.start_date,
                end_date=end_date,
                start_term=start_term,
                end_term=end_term,
                terms_active=terms_active,
                is_system_generated=True,
                notes=f"Major: {major_name}. Terms: {first_term_code} to {last_term_code} ({terms_active} terms)",
            )

            return enrollment

        except Exception as e:
            self.record_rejection(
                "MAJOR_CREATION_ERROR",
                f"{student.student_id}_{first_term_code if 'first_term_code' in locals() else 'unknown'}",
                {"error": str(e), "major": major_name},
            )
            return None

    def create_language_program_enrollment(
        self,
        student: StudentProfile,
        term_periods: dict,
        program_info: dict,
    ) -> bool:
        """Create enrollment for language programs with proper term calculations."""
        try:
            major_name = program_info["name_pattern"]
            major = self.get_or_create_major(major_name, program_info)
            if not major:
                return False

            # Calculate the enrollment period based on actual terms enrolled
            terms_list = sorted(term_periods.keys())
            if not terms_list:
                return False

            # Get first and last terms
            first_term_code = terms_list[0]
            last_term_code = terms_list[-1]

            # Get term objects
            try:
                start_term = Term.objects.get(code=first_term_code)
                end_term = Term.objects.get(code=last_term_code)
            except Term.DoesNotExist:
                return False

            # Calculate total terms and status
            terms_active = len(terms_list)

            # Determine status based on term end dates (more accurate logic)
            today = timezone.now().date()

            # Check if any term end date is in the future (meaning currently enrolled)
            has_future_terms = any(
                Term.objects.filter(code=term_code, end_date__gt=today).exists() for term_code in terms_list
            )

            if has_future_terms:
                # Currently enrolled - has future or ongoing terms
                status = ProgramEnrollment.EnrollmentStatus.ACTIVE
                end_date = None
                end_term = None
            elif end_term.end_date >= today - timedelta(days=365):
                # Ended within last year - recently completed/inactive
                status = ProgramEnrollment.EnrollmentStatus.INACTIVE
                end_date = end_term.end_date
            else:
                # Ended more than a year ago - completed
                status = ProgramEnrollment.EnrollmentStatus.COMPLETED
                end_date = end_term.end_date

            # Create language program enrollment with proper dates
            ProgramEnrollment.objects.create(
                student=student,
                program=major,
                enrollment_type=ProgramEnrollment.EnrollmentType.LANGUAGE,
                status=status,
                start_date=start_term.start_date,
                end_date=end_date,
                start_term=start_term,
                end_term=end_term,
                terms_active=terms_active,
                is_system_generated=True,
                notes=f"Language: {major_name}. Terms: {first_term_code} to {last_term_code} ({terms_active} terms)",
            )
            return True

        except Exception:
            return False

    def get_or_create_major(self, major_name: str, program_info: dict) -> Major | None:
        """Get or create a major object for the given major name."""
        try:
            # Build the full major name based on program pattern
            if program_info["division"] == "ACADEMIC":
                if major_name == "Unknown":
                    full_major_name = "Bachelor of Arts (Unknown)"
                elif "%s" in program_info["name_pattern"]:
                    full_major_name = program_info["name_pattern"] % major_name
                else:
                    full_major_name = major_name
            else:
                full_major_name = major_name

            # First, find or create the appropriate division and cycle
            division_name = "Language Division" if program_info["division"] == "LANGUAGE" else "Academic Division"
            division, _ = Division.objects.get_or_create(
                name=division_name,
                defaults={
                    "short_name": program_info["division"][:10],
                    "description": f"{division_name} programs",
                },
            )

            # Map cycle codes to proper names
            cycle_names = {
                "BA": "Bachelor's Degree",
                "MA": "Master's Degree",
                "HS": "High School",
                "CERT": "Certificate",
                "PREP": "Preparatory",
            }
            cycle_name = cycle_names.get(program_info["cycle"], program_info["cycle"])

            _cycle, _ = Cycle.objects.get_or_create(
                short_name=program_info["cycle"],
                division=division,
                defaults={
                    "name": cycle_name,
                    "description": f"{cycle_name} programs",
                    "is_active": True,
                },
            )

            # Find existing major (DO NOT CREATE NEW MAJORS)
            try:
                if program_info["division"] == "ACADEMIC":
                    # Map to official academic major codes
                    if full_major_name in ["IR", "International Relations"]:
                        major = Major.objects.get(code="IR")
                    elif full_major_name in ["BUSADMIN", "Business Administration"]:
                        major = Major.objects.get(code="BUSADMIN")
                    elif full_major_name in ["FIN-BANK", "Finance & Banking"]:
                        major = Major.objects.get(code="FIN-BANK")
                    elif full_major_name in [
                        "TOUR-HOSP",
                        "Tourism & Hospitality",
                        "Hospitality and Tourism",
                    ]:
                        major = Major.objects.get(code="TOUR-HOSP")
                    elif full_major_name in ["TESOL"]:
                        major = Major.objects.get(code="TESOL")
                    elif full_major_name in ["MBA"]:
                        major = Major.objects.get(code="MBA")
                    else:
                        # Unknown academic major - return None
                        return None
                else:
                    # For language programs, map to official programs only
                    # Extract course prefix to determine language program
                    if "IEAP" in full_major_name.upper():
                        major = Major.objects.get(code="IEAP")
                    elif "GESL" in full_major_name.upper():
                        major = Major.objects.get(code="GESL")
                    elif "EHSS" in full_major_name.upper():
                        major = Major.objects.get(code="EHSS")
                    elif "EXPRESS" in full_major_name.upper():
                        major = Major.objects.get(code="EXPRESS")
                    elif "IELTS" in full_major_name.upper():
                        major = Major.objects.get(code="IELTS")
                    elif "ELL" in full_major_name.upper():
                        major = Major.objects.get(code="ELL")
                    else:
                        # Anomalous language course - log it but don't create major
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️  Anomalous language course detected: {full_major_name} - "
                                f"Not mapping to any official language program"
                            )
                        )
                        return None

            except Major.DoesNotExist:
                # Major doesn't exist - return None instead of creating fake majors
                return None

            return major

        except Exception:
            return None

    def _get_degree_awarded(self, program_info: dict) -> str:
        """Get the degree awarded based on program info."""
        if program_info["division"] == "LANGUAGE":
            return Major.DegreeAwarded.CERT if program_info["cycle"] == "CERT" else Major.DegreeAwarded.NONE
        else:
            degree_map = {"BA": Major.DegreeAwarded.BA, "MA": Major.DegreeAwarded.MA}
            return degree_map.get(program_info["cycle"], Major.DegreeAwarded.NONE)

    def get_legacy_major_from_batchid_and_selmajor(self, student_id: str) -> str | None:
        """Get major from legacy data with enhanced priority order.

        Priority:
        1. left(batchidformaster,3) → BAD/TES/FIN/TOU/INT dictionary
        2. selmajor if selprogram = 87 → 2400/2301/540/4060/4316 dictionary
        3. None (will become "Unknown")

        Args:
            student_id: Student ID to look up

        Returns:
            Major name string or None
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT batchidformaster, selprogram, selmajor
                    FROM legacy_students
                    WHERE id = %s
                    """,
                    [student_id],
                )

                row = cursor.fetchone()
                if not row:
                    return None

                batchidformaster, sel_program, sel_major = row

                # Priority 1: BatchIdForMaster prefix (first 3 characters)
                if batchidformaster and len(str(batchidformaster)) >= 3:
                    batch_prefix = str(batchidformaster)[:3].upper()
                    if batch_prefix in self.BATCHID_MAJOR_CODES:
                        return self.BATCHID_MAJOR_CODES[batch_prefix]

                # Priority 2: SelMajor if SelProgram = 87 (BA program)
                if sel_program == 87 and sel_major:
                    sel_major_str = str(sel_major)
                    if sel_major_str in self.LEGACY_MAJOR_CODES:
                        return self.LEGACY_MAJOR_CODES[sel_major_str]

                return None
        except Exception:
            # legacy_students table may not exist in LOCAL environment
            # Fall back to None, which will result in "Unknown" major
            return None

    def determine_enrollment_status(self, period: dict, student: StudentProfile) -> str:
        """Determine the enrollment status."""
        # Simple logic - would be more sophisticated in production
        last_term_year = int(period["end_term"][:4]) if period["end_term"] else 0
        current_year = datetime.now().year

        if current_year - last_term_year > 2:
            return "COMPLETED"
        elif current_year - last_term_year > 1:
            return "INACTIVE"
        else:
            return "ACTIVE"
