"""Academic Progression Builder Service

This service handles the intelligent construction of academic progression records
from unreliable legacy enrollment data. It uses multiple detection strategies
with confidence scoring to handle data quality issues.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.curriculum.models import Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.enrollment.models_progression import (
    AcademicJourney,
    AcademicProgression,
    ProgramMilestone,
)
from apps.people.models import StudentProfile

logger = logging.getLogger(__name__)


class ProgressionBuilder:
    """Service for building academic progression from enrollment data."""

    # Grade handling from legacy system
    PASSING_GRADES = ["A", "B", "C", "D", "CR"]  # D is passing
    FAILING_GRADES = ["F", "W"]  # Both require retaking
    IN_PROGRESS_GRADES = ["IP", "I"]  # IP = In Progress/Program, I = Incomplete

    # Signature courses for major detection (using normalized course codes)
    # These are courses that uniquely identify each major
    # No student has 2 majors, so first match wins
    MAJOR_SIGNATURES = {
        "International Relations": [
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
        ],
        "Business Administration": [
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
        ],
        "Teaching of English as a Second Language": [
            "ENGL-200",
            "EDUC-400",
            "ENGL-302",
            "EDUC-301",
            "EDUC-401",
            "EDUC-404",
            "EDUC-403",
            "EDUC-405",
            "ENGL-401",
            "EDUC-408",
            "ENGL-140",
            "PHIL-213",
            "EDUC-407",
            "ENGL-130",
            "ENGL-403",
            "ENGL-306",
            "ENGL-301",
            "ENGL-303",
            "LIT-325",
            "ENGL-450",
            "EDUC-300",
            "PSYC-313",
            "ENGL-201",
        ],
        "Finance and Banking": [
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
        ],
        "Tourism & Hospitality": [
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
        ],
    }

    # Language program identifiers
    LANGUAGE_PROGRAMS = ["IEAP", "GESL", "EHSS", "Foundation Year"]

    # Major code mappings from legacy system
    LEGACY_MAJOR_CODES = {
        "87": "Bachelor",
        "147": "Master",
        "IEAP": "Intensive English for Academic Purposes",
        "GESL": "General English as a Second Language",
        "EHSS": "English for High School Students",
    }

    def __init__(self):
        self.major_cache = {}
        self.term_cache = {}
        self.course_cache = {}
        self._load_caches()

    def _load_caches(self):
        """Pre-load frequently used data."""
        # Cache all majors
        for major in Major.objects.all():
            self.major_cache[major.name] = major
            if major.code:
                self.major_cache[major.code] = major

        # Cache all terms
        for term in Term.objects.all():
            self.term_cache[term.id] = term
            self.term_cache[term.code] = term

    @transaction.atomic
    def build_student_journey(self, student_id: int) -> list[AcademicJourney]:
        """Build complete academic journey for a student.

        Creates multiple AcademicJourney records - one for each program period.

        Args:
            student_id: The database primary key (id) of the StudentProfile

        Returns:
            List of AcademicJourney records created
        """
        logger.info(f"Building journey for student {student_id}")

        # Get student and enrollments
        student = StudentProfile.objects.get(id=student_id)
        enrollments: list[ClassHeaderEnrollment] = list(
            ClassHeaderEnrollment.objects.filter(student_id=student_id)
            .select_related("class_header__course", "class_header__term")
            .order_by("class_header__term__start_date")
        )

        if not enrollments:
            raise ValueError(f"No enrollments found for student {student_id}")

        # Detect program periods
        program_periods = self._detect_program_periods(enrollments)

        if not program_periods:
            logger.warning(f"No program periods detected for student {student_id}")
            return []

        journeys = []

        # Create an AcademicJourney record for each program period
        for i, period in enumerate(program_periods):
            # Determine transition status
            if i == len(program_periods) - 1:
                # Last period - check if still active
                months_since = (date.today() - period["end_date"]).days / 30
                if months_since < 6:
                    transition_status = AcademicJourney.TransitionStatus.ACTIVE
                elif period.get("is_graduated"):
                    transition_status = AcademicJourney.TransitionStatus.GRADUATED
                else:
                    transition_status = AcademicJourney.TransitionStatus.DROPPED_OUT
            else:
                # Not the last period - they changed programs
                transition_status = AcademicJourney.TransitionStatus.CHANGED_PROGRAM

            # Get the Major object if it's an academic program
            program_major = None
            if period["program_type"] in ["BA", "MA"]:
                program_major = period.get("major")

            # Create journey record for this program period
            journey = AcademicJourney.objects.create(
                student=student,
                program_type=self._map_program_type(period["program_type"]),
                program=program_major,
                start_date=period["start_date"],
                stop_date=period["end_date"] if transition_status != AcademicJourney.TransitionStatus.ACTIVE else None,
                start_term=period["start_term"],
                term_code=period["start_term_code"],
                duration_in_terms=period["term_count"],
                transition_status=transition_status,
                data_source=AcademicJourney.DataSource.LEGACY,
                confidence_score=Decimal(str(period.get("confidence", 0.8))),
                requires_review=period.get("confidence", 0.8) < 0.7,
                notes=f"Program: {period['program_name']}, Terms: {period['term_count']}",
            )

            journeys.append(journey)

            # Create milestones for this journey
            self._create_period_milestones(journey, period, transition_status)

        # Create denormalized progression view
        if journeys:
            self._create_academic_progression_from_journeys(student, journeys, program_periods)

        logger.info(f"Created {len(journeys)} journey records for student {student_id}")
        return journeys

    def _detect_academic_phases(self, enrollments: list[ClassHeaderEnrollment]) -> list[dict[str, Any]]:
        """Detect distinct academic phases from enrollments."""
        phases = []

        # Group enrollments by program type
        language_enrollments = []
        ba_enrollments = []
        ma_enrollments = []

        for enrollment in enrollments:
            course_code = enrollment.class_header.course.code  # type: ignore[attr-defined]

            # Detect language courses
            if any(lang in course_code for lang in ["IEAP", "GESL", "EHSS", "ELL"]):
                language_enrollments.append(enrollment)
            # Detect graduate courses (500+ level)
            elif course_code.split("-")[-1].isdigit() and int(course_code.split("-")[-1]) >= 500:
                ma_enrollments.append(enrollment)
            else:
                ba_enrollments.append(enrollment)

        # Process language phase
        if language_enrollments:
            phase = self.detect_language_phase(language_enrollments)
            if phase:
                phases.append(phase)

        # Process BA phase
        if ba_enrollments:
            phase = self.detect_ba_phase(ba_enrollments)
            if phase:
                phases.append(phase)

        # Process MA phase
        if ma_enrollments:
            phase = self.detect_ma_phase(ma_enrollments)
            if phase:
                phases.append(phase)

        return phases

    def detect_language_phase(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect language program progression."""
        if not enrollments:
            return {}

        # Extract language program info
        programs = defaultdict(list)
        for enrollment in enrollments:
            course_code = enrollment.class_header.course.code  # type: ignore[attr-defined]
            for program in ["IEAP", "GESL", "EHSS"]:
                if program in course_code:
                    programs[program].append(enrollment)
                    break

        if not programs:
            return None

        # Find primary program (most enrollments)
        primary_program = max(programs.keys(), key=lambda k: len(programs[k]))
        program_enrollments = programs[primary_program]

        # Extract levels
        levels = []
        for enrollment in program_enrollments:
            # Extract level from course code (e.g., IEAP-201 -> 2)
            parts = enrollment.class_header.course.code.split("-")  # type: ignore[attr-defined]
            if len(parts) > 1 and parts[1]:
                try:
                    level = int(parts[1][0])  # First digit of course number
                    levels.append(level)
                except (ValueError, IndexError):
                    pass

        # Determine completion
        final_level = max(levels) if levels else 0
        if primary_program == "IEAP" and final_level >= 4:
            completion_status = "completed"
        elif primary_program in ["GESL", "EHSS"] and final_level >= 12:
            completion_status = "completed"
        else:
            completion_status = "incomplete"

        return {
            "type": "language",
            "program": self.LEGACY_MAJOR_CODES.get(primary_program, primary_program),
            "start_date": min(e.class_header.term.start_date for e in program_enrollments),  # type: ignore[attr-defined]
            "end_date": max(e.class_header.term.end_date for e in program_enrollments),  # type: ignore[attr-defined]
            "enrollments": program_enrollments,
            "final_level": str(final_level),
            "completion_status": completion_status,
            "terms": len({e.class_header.term_id for e in program_enrollments}),  # type: ignore[attr-defined]
            "confidence": 0.9 if levels else 0.7,
        }

    def detect_ba_phase(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect BA program and major."""
        if not enrollments:
            return None

        # Detect major using multiple strategies
        detection_results = []

        # Strategy 1: Signature courses
        result = self.detect_by_signature_courses(enrollments)
        if result["major"]:
            result["strategy"] = "signature_courses"
            detection_results.append(result)

        # Strategy 2: Course frequency
        result = self.detect_by_course_frequency(enrollments)
        if result["major"]:
            result["strategy"] = "course_frequency"
            detection_results.append(result)

        # Strategy 3: Concentration in later terms
        result = self.detect_by_concentration_pattern(enrollments)
        if result["major"]:
            result["strategy"] = "concentration"
            detection_results.append(result)

        # Combine results
        final_result = self.combine_detection_results(detection_results)

        return {
            "type": "bachelor",
            "major": final_result.get("major"),
            "start_date": min(e.class_header.term.start_date for e in enrollments),  # type: ignore[attr-defined]
            "end_date": max(e.class_header.term.end_date for e in enrollments),  # type: ignore[attr-defined]
            "enrollments": enrollments,
            "terms": len({e.class_header.term_id for e in enrollments}),  # type: ignore[attr-defined]
            "confidence": final_result.get("confidence", 0.5),
            "detection_method": final_result.get("detection_method", "unknown"),
            "is_certain": final_result.get("is_certain", False),
        }

    def detect_ma_phase(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect MA program."""
        if not enrollments:
            return None

        # MA detection is simpler - usually fewer signature courses
        # Check for MBA courses
        mba_courses = ["MGT-5", "FIN-5", "MKT-5", "ECON-5", "BUS-5"]
        is_mba = any(any(prefix in e.class_header.course.code for prefix in mba_courses) for e in enrollments)  # type: ignore[attr-defined]

        if is_mba:
            major = self.major_cache.get("Master of Business Administration")
        else:
            # Try to detect based on undergraduate major continuation
            # This is a simplification - would need more logic in production
            major = None

        return {
            "type": "master",
            "major": major,
            "start_date": min(e.class_header.term.start_date for e in enrollments),  # type: ignore[attr-defined]
            "end_date": max(e.class_header.term.end_date for e in enrollments),  # type: ignore[attr-defined]
            "enrollments": enrollments,
            "terms": len({e.class_header.term_id for e in enrollments}),  # type: ignore[attr-defined]
            "confidence": 0.8 if major else 0.4,
        }

    def detect_by_signature_courses(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect major by signature course matches."""
        # Count signature course matches
        course_codes = [e.class_header.course.code for e in enrollments]  # type: ignore[attr-defined]
        major_matches = defaultdict(list)

        for code in course_codes:
            for major_name, signatures in self.MAJOR_SIGNATURES.items():
                if code in signatures:
                    major_matches[major_name].append(code)

        if not major_matches:
            return {"major": None, "confidence": 0}

        # Find major with most matches
        best_major = max(major_matches.keys(), key=lambda k: len(major_matches[k]))
        matches = major_matches[best_major]

        # High confidence if multiple signature courses
        confidence = min(0.95, 0.7 + (len(matches) * 0.05))

        return {
            "major": self.major_cache.get(best_major),
            "confidence": confidence,
            "matches": matches,
            "count": len(matches),
        }

    def detect_by_course_frequency(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect major by department frequency."""
        # Count courses by department prefix
        dept_counts: dict[str, int] = defaultdict(int)
        total_courses = 0

        for enrollment in enrollments:
            code = enrollment.class_header.course.code  # type: ignore[attr-defined]
            if "-" in code:
                dept = code.split("-")[0]
                dept_counts[dept] += 1
                total_courses += 1

        if not dept_counts or total_courses == 0:
            return {"major": None, "confidence": 0}

        # Map departments to majors
        dept_major_map = {
            "IR": "International Relations",
            "POL": "International Relations",
            "LAW": "International Relations",
            "BUS": "Business Administration",
            "MGT": "Business Administration",
            "MKT": "Business Administration",
            "FIN": "Finance and Banking",
            "EDUC": "Teaching of English as a Second Language",
            "THM": "Tourism & Hospitality",
        }

        # Find dominant department
        dominant_dept = max(dept_counts.keys(), key=lambda k: dept_counts[k])
        count = dept_counts[dominant_dept]

        major_name = dept_major_map.get(dominant_dept)
        if major_name:
            return {
                "major": self.major_cache.get(major_name),
                "confidence": min(0.8, count / total_courses * 1.5),  # Scale confidence
                "department": dominant_dept,
                "course_count": count,
            }

        return {"major": None, "confidence": 0}

    def detect_by_concentration_pattern(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Detect major by course concentration in later terms."""
        # Group enrollments by term
        terms_courses = defaultdict(list)
        for enrollment in enrollments:
            term_date = enrollment.class_header.term.start_date  # type: ignore[attr-defined]
            terms_courses[term_date].append(enrollment.class_header.course.code)  # type: ignore[attr-defined]

        # Focus on last 40% of terms (where concentration typically occurs)
        sorted_terms = sorted(terms_courses.keys())
        cutoff_index = int(len(sorted_terms) * 0.6)
        later_terms = sorted_terms[cutoff_index:]

        # Analyze concentration in later terms
        concentrated_courses = []
        for term in later_terms:
            concentrated_courses.extend(terms_courses[term])

        # Use signature detection on concentrated courses
        mock_enrollments = [
            type(
                "MockEnrollment",
                (),
                {"class_header": type("MockHeader", (), {"course": type("MockCourse", (), {"code": code})})},
            )
            for code in concentrated_courses
        ]

        return self.detect_by_signature_courses(mock_enrollments)  # type: ignore[arg-type]

    def detect_by_legacy_codes(self, enrollments: list[ClassHeaderEnrollment]) -> dict[str, Any]:
        """Last resort: check legacy program codes."""
        # This would check ProgramEnrollment if it exists
        student_id = enrollments[0].student_id

        try:
            # Check if there's an existing ProgramEnrollment
            existing = ProgramEnrollment.objects.filter(
                student_id=student_id, enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC
            ).first()

            if existing and existing.program:
                return {
                    "major": existing.program,
                    "confidence": 0.5,  # Low confidence for legacy data
                    "source": "legacy_program_enrollment",
                }
        except Exception:
            pass

        return {"major": None, "confidence": 0}

    def combine_detection_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Combine multiple detection results with weighted confidence."""
        if not results:
            return {"major": None, "confidence": 0, "detection_method": "none", "is_certain": False}

        # Weight strategies by reliability
        strategy_weights = {
            "signature_courses": 1.0,
            "concentration": 0.8,
            "course_frequency": 0.6,
            "legacy_codes": 0.3,
        }

        # Calculate weighted scores
        major_scores: dict[str, float] = defaultdict(float)
        for result in results:
            if result.get("major"):
                strategy = result.get("strategy", "unknown")
                weight = strategy_weights.get(strategy, 0.5)
                score = result["confidence"] * weight
                major_scores[result["major"].id] = max(major_scores[result["major"].id], score)

        if not major_scores:
            return {"major": None, "confidence": 0, "detection_method": "none", "is_certain": False}

        # Find best major
        best_major_id = max(major_scores.keys(), key=lambda k: major_scores[k])
        best_score = major_scores[best_major_id]
        best_major = Major.objects.get(id=best_major_id)

        # Find which strategies detected this major
        detection_methods = []
        for result in results:
            if result.get("major") and result["major"].id == best_major_id:
                detection_methods.append(result.get("strategy", "unknown"))

        return {
            "major": best_major,
            "confidence": min(best_score, 0.95),  # Cap at 95%
            "detection_method": ", ".join(detection_methods),
            "is_certain": best_score >= 0.8,
        }

    def _create_phase_milestones(self, journey: AcademicJourney, phase: dict[str, Any]):
        """Create milestone records for an academic phase."""
        # Start milestone
        if phase.get("start_date"):
            ProgramMilestone.objects.create(
                journey=journey,
                milestone_type=ProgramMilestone.MilestoneType.PROGRAM_START,
                milestone_date=phase["start_date"],
                program=phase.get("major") or self._get_language_major(phase.get("program")),
                confidence_score=Decimal(str(phase.get("confidence", 1.0))),
            )

        # Completion/graduation milestone
        if phase.get("completion_status") == "completed" and phase.get("end_date"):
            milestone_type = (
                ProgramMilestone.MilestoneType.CERTIFICATE_EARNED
                if phase["type"] == "language"
                else ProgramMilestone.MilestoneType.DEGREE_EARNED
            )

            ProgramMilestone.objects.create(
                journey=journey,
                milestone_type=milestone_type,
                milestone_date=phase["end_date"],
                program=phase.get("major") or self._get_language_major(phase.get("program")),
                level=phase.get("final_level"),
                confidence_score=Decimal(str(phase.get("confidence", 1.0))),
            )

    def _get_language_major(self, program_name: str) -> Major | None:
        """Get or create major for language program."""
        if not program_name:
            return None

        # Try cache first
        major = self.major_cache.get(program_name)
        if major:
            return major

        # Try to find by partial match
        for key, major in self.major_cache.items():
            if program_name in key or key in program_name:
                return major

        return None

    def _determine_journey_status(
        self, phases: list[dict], enrollments: list[ClassHeaderEnrollment], journey: AcademicJourney | None = None
    ) -> str:
        """Determine overall journey status."""
        if not phases:
            return "UNKNOWN"

        # Check last enrollment date
        last_enrollment_date = enrollments[-1].class_header.term.end_date  # type: ignore[attr-defined]
        months_since_last = (date.today() - last_enrollment_date).days / 30

        # Check for graduation in any phase
        has_ba_graduation = any(p["type"] == "bachelor" and p.get("completion_status") == "completed" for p in phases)
        has_ma_graduation = any(p["type"] == "master" and p.get("completion_status") == "completed" for p in phases)

        # Also check ProgramPeriod records if available
        from apps.enrollment.models_progression import ProgramPeriod

        if journey:
            program_periods = ProgramPeriod.objects.filter(journey=journey)
            has_ba_graduation = (
                has_ba_graduation
                or program_periods.filter(to_program_type="BA", completion_status="GRADUATED").exists()
            )
            has_ma_graduation = (
                has_ma_graduation
                or program_periods.filter(to_program_type="MA", completion_status="GRADUATED").exists()
            )

        if has_ma_graduation:
            return "GRADUATED"
        elif has_ba_graduation and not any(p["type"] == "master" for p in phases):
            return "GRADUATED"
        elif months_since_last < 6:
            return "ACTIVE"
        elif months_since_last < 24:
            return "INACTIVE"
        else:
            # Don't mark as dropped if they graduated
            if has_ba_graduation or has_ma_graduation:
                return "GRADUATED"
            return "DROPPED"

    def _create_academic_progression(self, journey: AcademicJourney, phases: list[dict]):
        """Create denormalized progression record for fast queries."""
        # Get student name and ID
        student_name = journey.student.person.full_name if journey.student.person else ""  # type: ignore[attr-defined]
        student_id = journey.student.student_id  # type: ignore[attr-defined]

        # Determine entry program
        first_phase = phases[0] if phases else None
        entry_program = ""
        if first_phase:
            if first_phase["type"] == "language":
                entry_program = first_phase.get("program", "")
            elif first_phase.get("major"):
                entry_program = first_phase["major"].name

        # Get first enrollment term
        enrollments = list(
            ClassHeaderEnrollment.objects.filter(student=journey.student)
            .select_related("class_header__term")
            .order_by("class_header__term__start_date")
        )
        entry_term = enrollments[0].class_header.term.code if enrollments else ""

        progression = AcademicProgression(
            student=journey.student,
            student_name=student_name,
            student_id_number=student_id,
            entry_program=entry_program,
            entry_date=journey.start_date,
            entry_term=entry_term,
            current_status="UNKNOWN",
            total_terms=journey.duration_in_terms,
        )

        # Extract phase-specific data
        for phase in phases:
            if phase["type"] == "language":
                progression.entry_program = phase.get("program", "")
                progression.language_start_date = phase.get("start_date")
                progression.language_end_date = phase.get("end_date")
                progression.language_final_level = phase.get("final_level", "")
                progression.language_terms = phase.get("terms", 0)
                progression.language_completion_status = (
                    "COMPLETED" if phase.get("completion_status") == "completed" else "DROPPED"
                )

            elif phase["type"] == "bachelor":
                if phase.get("major"):
                    progression.ba_major = phase["major"].name
                progression.ba_start_date = phase.get("start_date")
                if phase.get("completion_status") == "completed":
                    progression.ba_completion_date = phase.get("end_date")
                    progression.ba_completion_status = "GRADUATED"
                progression.ba_terms = phase.get("terms", 0)
                if progression.ba_start_date and progression.ba_completion_date:
                    progression.time_to_ba_days = (progression.ba_completion_date - progression.ba_start_date).days

            elif phase["type"] == "master":
                if phase.get("major"):
                    progression.ma_program = phase["major"].name
                progression.ma_start_date = phase.get("start_date")
                if phase.get("completion_status") == "completed":
                    progression.ma_completion_date = phase.get("end_date")
                    progression.ma_completion_status = "GRADUATED"
                progression.ma_terms = phase.get("terms", 0)
                if progression.ba_completion_date and progression.ma_completion_date:
                    progression.time_to_ma_days = (
                        progression.ma_completion_date - progression.ba_completion_date
                    ).days

        progression.save()
        return progression

    def _detect_program_periods(self, enrollments: list[ClassHeaderEnrollment]) -> list[dict[str, Any]]:
        """Detect distinct program periods from enrollments.

        This method analyzes enrollments chronologically to identify when a student
        changes programs (e.g., IEAP -> GESL, GESL -> BA, BA -> MA).
        """
        periods = []
        current_period = None

        # Group enrollments by term first
        terms_data = defaultdict(list)
        for enrollment in enrollments:
            term = enrollment.class_header.term  # type: ignore[attr-defined]
            terms_data[term.start_date].append(
                {"enrollment": enrollment, "course_code": enrollment.class_header.course.code, "term": term}  # type: ignore[attr-defined]
            )

        # Process chronologically
        for term_date in sorted(terms_data.keys()):
            term_enrollments = terms_data[term_date]

            # Detect program type for this term
            program_info = self._detect_term_program(term_enrollments)

            if not program_info:
                continue

            # Check if this is a new program period
            if current_period is None:
                # First period
                current_period = {
                    "program_type": program_info["type"],
                    "program_name": program_info["name"],
                    "major": program_info.get("major"),
                    "start_date": term_enrollments[0]["term"].start_date,
                    "end_date": term_enrollments[0]["term"].end_date,
                    "start_term": term_enrollments[0]["term"],
                    "start_term_code": term_enrollments[0]["term"].code,
                    "enrollments": [e["enrollment"] for e in term_enrollments],
                    "term_count": 1,
                    "language_level": program_info.get("level"),
                    "confidence": program_info.get("confidence", 0.8),
                }
            elif current_period["program_type"] != program_info["type"] or current_period.get(
                "major"
            ) != program_info.get("major"):
                # Program changed - save current period and start new one
                current_period["is_graduated"] = self._check_graduation(current_period)
                periods.append(current_period)

                current_period = {
                    "program_type": program_info["type"],
                    "program_name": program_info["name"],
                    "major": program_info.get("major"),
                    "start_date": term_enrollments[0]["term"].start_date,
                    "end_date": term_enrollments[0]["term"].end_date,
                    "start_term": term_enrollments[0]["term"],
                    "start_term_code": term_enrollments[0]["term"].code,
                    "enrollments": [e["enrollment"] for e in term_enrollments],
                    "term_count": 1,
                    "language_level": program_info.get("level"),
                    "confidence": program_info.get("confidence", 0.8),
                }
            else:
                # Same program - extend current period
                current_period["end_date"] = term_enrollments[0]["term"].end_date
                current_period["enrollments"].extend([e["enrollment"] for e in term_enrollments])
                current_period["term_count"] += 1
                if program_info.get("level"):
                    current_period["language_level"] = program_info["level"]

        # Don't forget the last period
        if current_period:
            current_period["is_graduated"] = self._check_graduation(current_period)
            periods.append(current_period)

        return periods

    def _detect_term_program(self, term_enrollments: list[dict]) -> dict[str, Any] | None:
        """Detect the program type for a single term's enrollments."""
        # Count course types
        language_courses = []
        ba_courses = []
        ma_courses = []

        for item in term_enrollments:
            course_code = item["course_code"]

            # Check for language programs
            if any(lang in course_code for lang in ["IEAP", "GESL", "EHSS"]):
                language_courses.append(course_code)
            # Check for MA courses (500+ level)
            elif "-" in course_code:
                try:
                    level = int(course_code.split("-")[1][:3])
                    if level >= 500:
                        ma_courses.append(course_code)
                    else:
                        ba_courses.append(course_code)
                except (ValueError, IndexError):
                    ba_courses.append(course_code)
            else:
                ba_courses.append(course_code)

        # Determine dominant program type
        if language_courses and len(language_courses) >= len(ba_courses) + len(ma_courses):
            # Language program
            program_type = self._identify_language_program(language_courses)
            level_str = self._extract_language_level(language_courses)
            return {
                "type": program_type,
                "name": self.LEGACY_MAJOR_CODES.get(program_type, program_type),
                "level": level_str,
                "confidence": 0.9,
            }
        elif ma_courses and len(ma_courses) >= len(ba_courses):
            # MA program
            enrollments = [item["enrollment"] for item in term_enrollments if item["course_code"] in ma_courses]
            ma_info = self.detect_ma_phase(enrollments)
            if ma_info:
                return {
                    "type": "MA",
                    "name": "Master of Arts",
                    "major": ma_info.get("major"),
                    "confidence": ma_info.get("confidence", 0.7),
                }
        elif ba_courses:
            # BA program
            enrollments = [item["enrollment"] for item in term_enrollments if item["course_code"] in ba_courses]
            ba_info = self.detect_ba_phase(enrollments)
            if ba_info:
                return {
                    "type": "BA",
                    "name": "Bachelor of Arts",
                    "major": ba_info.get("major"),
                    "confidence": ba_info.get("confidence", 0.7),
                }

        return None

    def _identify_language_program(self, course_codes: list[str]) -> str:
        """Identify which language program from course codes."""
        program_counts: dict[str, int] = defaultdict(int)

        for code in course_codes:
            if "IEAP" in code:
                program_counts["IEAP"] += 1
            elif "GESL" in code:
                program_counts["GESL"] += 1
            elif "EHSS" in code:
                program_counts["EHSS"] += 1

        if program_counts:
            return max(program_counts.keys(), key=lambda k: program_counts[k])
        return "LANGUAGE"

    def _extract_language_level(self, course_codes: list[str]) -> str:
        """Extract the highest language level from course codes."""
        levels = []

        for code in course_codes:
            if "-" in code:
                try:
                    # Extract level from course number
                    level_str = code.split("-")[1]
                    if level_str and level_str[0].isdigit():
                        levels.append(int(level_str[0]))
                except (ValueError, IndexError):
                    pass

        return str(max(levels)) if levels else ""

    def _check_graduation(self, period: dict) -> bool:
        """Check if a program period ended in graduation."""
        if period["program_type"] == "BA":
            # Check for exit exam or high credit count
            for enrollment in period["enrollments"]:
                course_code = enrollment.class_header.course.code
                if "EXIT" in course_code or "COMEX" in course_code:
                    return True

            # Check credit count
            total_credits = sum(
                enrollment.class_header.course.credits or Decimal("0")
                for enrollment in period["enrollments"]
                if enrollment.final_grade in self.PASSING_GRADES
            )
            return total_credits >= Decimal("100")

        elif period["program_type"] == "MA":
            # MA typically requires 30+ credits
            total_credits = sum(
                enrollment.class_header.course.credits or Decimal("0")
                for enrollment in period["enrollments"]
                if enrollment.final_grade in self.PASSING_GRADES
            )
            return total_credits >= Decimal("30")

        elif period["program_type"] in ["IEAP", "GESL", "EHSS"]:
            # Language programs complete at certain levels
            level = period.get("language_level", "")
            if level.isdigit():
                if period["program_type"] == "IEAP" and int(level) >= 4:
                    return True
                elif period["program_type"] in ["GESL", "EHSS"] and int(level) >= 6:
                    return True

        return False

    def _map_program_type(self, detected_type: str) -> str:
        """Map detected program type to AcademicJourney.ProgramType choices."""
        type_mapping = {
            "IEAP": AcademicJourney.ProgramType.LANGUAGE,
            "GESL": AcademicJourney.ProgramType.LANGUAGE,
            "EHSS": AcademicJourney.ProgramType.LANGUAGE,
            "LANGUAGE": AcademicJourney.ProgramType.LANGUAGE,
            "BA": AcademicJourney.ProgramType.BA,
            "MA": AcademicJourney.ProgramType.MA,
        }
        return type_mapping.get(detected_type, AcademicJourney.ProgramType.BA)

    def _create_period_milestones(self, journey: AcademicJourney, period: dict, transition_status: str):
        """Create milestone records for a program period."""
        # Program start milestone
        ProgramMilestone.objects.create(
            journey=journey,
            milestone_type=ProgramMilestone.MilestoneType.PROGRAM_START,
            milestone_date=period["start_date"],
            academic_term=period["start_term"],
            program=period.get("major"),
            level=period.get("language_level", ""),
            confidence_score=Decimal(str(period.get("confidence", 0.8))),
            is_inferred=True,
            inference_method="enrollment_analysis",
        )

        # If graduated, add graduation milestone
        if transition_status == AcademicJourney.TransitionStatus.GRADUATED:
            milestone_type = (
                ProgramMilestone.MilestoneType.CERTIFICATE_EARNED
                if journey.program_type == AcademicJourney.ProgramType.LANGUAGE
                else ProgramMilestone.MilestoneType.DEGREE_EARNED
            )

            ProgramMilestone.objects.create(
                journey=journey,
                milestone_type=milestone_type,
                milestone_date=period["end_date"],
                program=period.get("major"),
                level=period.get("language_level", ""),
                confidence_score=Decimal(str(period.get("confidence", 0.8))),
                is_inferred=True,
                inference_method="credit_analysis",
            )

        # If changed program, add change milestone
        elif transition_status == AcademicJourney.TransitionStatus.CHANGED_PROGRAM:
            ProgramMilestone.objects.create(
                journey=journey,
                milestone_type=ProgramMilestone.MilestoneType.MAJOR_CHANGE,
                milestone_date=period["end_date"],
                from_program=period.get("major"),
                confidence_score=Decimal(str(period.get("confidence", 0.8))),
                is_inferred=True,
                inference_method="program_detection",
            )

    def _create_academic_progression_from_journeys(
        self, student: StudentProfile, journeys: list[AcademicJourney], periods: list[dict]
    ):
        """Create denormalized progression record from multiple journey records."""
        # Get or create progression record
        progression, created = AcademicProgression.objects.get_or_create(
            student=student,
            defaults={
                "student_name": student.person.full_name if student.person else "",
                "student_id_number": student.student_id,
            },
        )

        # Determine entry program from first journey
        if journeys:
            first_journey = journeys[0]
            if first_journey.program_type == AcademicJourney.ProgramType.LANGUAGE:
                progression.entry_program = first_journey.program_type
            elif first_journey.program:
                progression.entry_program = first_journey.program.name

            progression.entry_date = first_journey.start_date
            progression.entry_term = first_journey.term_code

        # Process each journey to update progression
        for journey, period in zip(journeys, periods, strict=False):
            if journey.program_type == AcademicJourney.ProgramType.LANGUAGE:
                if not progression.language_start_date or journey.start_date < progression.language_start_date:
                    progression.language_start_date = journey.start_date

                progression.language_end_date = journey.stop_date or period["end_date"]
                progression.language_terms = (progression.language_terms or 0) + journey.duration_in_terms
                progression.language_final_level = period.get("language_level", "")

                if journey.transition_status == AcademicJourney.TransitionStatus.GRADUATED:
                    progression.language_completion_status = "COMPLETED"
                elif journey.transition_status == AcademicJourney.TransitionStatus.ACTIVE:
                    progression.language_completion_status = "ACTIVE"
                else:
                    progression.language_completion_status = "DROPPED"

            elif journey.program_type == AcademicJourney.ProgramType.BA:
                progression.ba_start_date = journey.start_date
                if journey.program:
                    progression.ba_major = journey.program.name
                progression.ba_terms = journey.duration_in_terms

                if journey.transition_status == AcademicJourney.TransitionStatus.GRADUATED:
                    progression.ba_completion_status = "GRADUATED"
                    progression.ba_completion_date = journey.stop_date or period["end_date"]
                elif journey.transition_status == AcademicJourney.TransitionStatus.ACTIVE:
                    progression.ba_completion_status = "ACTIVE"
                else:
                    progression.ba_completion_status = "DROPPED"

            elif journey.program_type == AcademicJourney.ProgramType.MA:
                progression.ma_start_date = journey.start_date
                if journey.program:
                    progression.ma_program = journey.program.name
                progression.ma_terms = journey.duration_in_terms

                if journey.transition_status == AcademicJourney.TransitionStatus.GRADUATED:
                    progression.ma_completion_status = "GRADUATED"
                    progression.ma_completion_date = journey.stop_date or period["end_date"]
                elif journey.transition_status == AcademicJourney.TransitionStatus.ACTIVE:
                    progression.ma_completion_status = "ACTIVE"
                else:
                    progression.ma_completion_status = "DROPPED"

        # Calculate total terms and time metrics
        progression.total_terms = sum(j.duration_in_terms for j in journeys)

        if progression.ba_start_date and progression.ba_completion_date:
            progression.time_to_ba_days = (progression.ba_completion_date - progression.ba_start_date).days

        if progression.ba_completion_date and progression.ma_completion_date:
            progression.time_to_ma_days = (progression.ma_completion_date - progression.ba_completion_date).days

        # Determine current status
        last_journey = journeys[-1] if journeys else None
        if last_journey:
            if last_journey.transition_status == AcademicJourney.TransitionStatus.ACTIVE:
                progression.current_status = f"ACTIVE_{last_journey.program_type}"
            elif last_journey.transition_status == AcademicJourney.TransitionStatus.GRADUATED:
                progression.current_status = "GRADUATED"
            else:
                progression.current_status = "INACTIVE"

        progression.save()
        return progression
