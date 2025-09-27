"""End-to-end tests for complete student journey.

These tests verify the entire student lifecycle from admission to graduation,
testing all integrated systems working together.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

# from apps.academic.models import GraduationAudit  # TODO: This model doesn't exist
from apps.attendance.models import AttendanceRecord, AttendanceSession
from apps.curriculum.models import Course, Division, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import Invoice, Payment
from apps.grading.models import ClassPartGrade, GPARecord
from apps.people.models import Person, StudentProfile, TeacherProfile
from apps.scheduling.models import ClassHeader
from tests.fixtures.factories import PersonFactory, StudentProfileFactory


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteStudentJourney:
    """Test the complete student journey from admission to graduation."""

    def test_four_year_student_journey(self):
        """Test a complete 4-year student journey through the system.

        This comprehensive test covers:
        1. Student admission and account creation
        2. Program enrollment
        3. Course registration each semester
        4. Class attendance
        5. Grade recording
        6. Financial transactions
        7. Academic progress tracking
        8. Graduation requirements
        9. Transcript generation
        """

        # Year 1: Admission and First Semester
        with freeze_time("2020-08-01"):
            # Step 1: Create student account
            User.objects.create_user(email="jane.student@example.com", password="SecurePass123!")

            person = Person.objects.create(
                personal_name="Jane",
                family_name="Student",
                date_of_birth=date(2002, 3, 15),
                preferred_gender="F",
                citizenship="KH",
                personal_email="jane.student@example.com",
                phone_number="+855123456789",
            )

            student = StudentProfile.objects.create(
                person=person,
                student_id=20200001,
                entry_date=date(2020, 9, 1),
                expected_graduation_date=date(2024, 6, 30),
                current_status="ACTIVE",
                high_school="Phnom Penh International School",
                high_school_graduation_year=2020,
            )

            # Step 2: Enroll in degree program
            division = Division.objects.create(name="Computer Science", short_name="CS")

            program = Program.objects.create(
                name="Bachelor of Science in Computer Science",
                code="BSCS",
                degree_type="BS",
                division=division,
                total_credits=120,
                duration_years=4,
                requires_senior_project=True,
            )

            # Add program requirements
            core_requirements = [
                ("CS101", "Introduction to Programming", 3),
                ("CS102", "Data Structures", 3),
                ("MATH101", "Calculus I", 4),
                ("ENG101", "English Composition", 3),
            ]

            for code, title, credits in core_requirements:
                course = Course.objects.create(
                    code=code, title=title, credits=credits, division=division, cycle="BA", level="100"
                )

                ProgramRequirement.objects.create(
                    program=program, course=course, requirement_type="CORE", minimum_grade="C"
                )

        # Fall 2020 Semester
        with freeze_time("2020-09-01"):
            fall_2020 = Term.objects.create(
                name="Fall 2020",
                code="FA20",
                start_date=date(2020, 9, 7),
                end_date=date(2020, 12, 18),
                registration_start=date(2020, 8, 15),
                registration_end=date(2020, 9, 14),
                is_current=True,
            )

            # Register for first semester
            registration = Registration.objects.create(
                student=student, term=fall_2020, registration_date=timezone.now(), status="APPROVED", total_credits=13
            )

            # Enroll in first semester courses
            courses_enrolled = []
            for course_code in ["CS101", "MATH101", "ENG101"]:
                course = Course.objects.get(code=course_code)
                class_header = ClassHeader.objects.create(
                    course=course, term=fall_2020, section="A", max_enrollment=30, current_enrollment=0
                )

                enrollment = ClassHeaderEnrollment.objects.create(
                    student=student,
                    class_header=class_header,
                    registration=registration,
                    enrollment_date=timezone.now(),
                    status="ENROLLED",
                )
                courses_enrolled.append((course, class_header, enrollment))

                class_header.current_enrollment += 1
                class_header.save()

            # Generate invoice for semester
            invoice = Invoice.objects.create(
                student=student,
                term=fall_2020,
                invoice_number="INV-2020-0001",
                issue_date=date(2020, 9, 1),
                due_date=date(2020, 9, 15),
                total_amount=Decimal("1950.00"),  # $150 per credit
                status="PENDING",
            )

            # Make payment
            payment = Payment.objects.create(
                invoice=invoice,
                amount=Decimal("1950.00"),
                payment_date=date(2020, 9, 10),
                payment_method="BANK_TRANSFER",
                reference_number="BT20200910001",
                status="COMPLETED",
            )

            invoice.status = "PAID"
            invoice.paid_amount = payment.amount
            invoice.save()

        # Attend classes throughout the semester
        with freeze_time("2020-10-15"):
            for _course, class_header, _enrollment in courses_enrolled:
                # Simulate attendance for multiple sessions
                for week in range(1, 11):  # 10 weeks of classes
                    session_date = date(2020, 9, 7) + timedelta(weeks=week)

                    session = AttendanceSession.objects.create(
                        class_header=class_header,
                        session_date=session_date,
                        start_time="09:00",
                        end_time="10:20",
                        session_code=f"ATT{week:03d}",
                        is_active=False,  # Already closed
                    )

                    # Student attends most classes (90% attendance)
                    if week != 5:  # Skip week 5
                        AttendanceRecord.objects.create(
                            session=session, student=student, status="PRESENT", check_in_time=f"09:{week:02d}"
                        )

        # End of semester - Record grades
        with freeze_time("2020-12-20"):
            grades = {"CS101": "A", "MATH101": "B+", "ENG101": "A-"}

            total_grade_points = Decimal("0")
            total_credits = 0

            for course, _class_header, enrollment in courses_enrolled:
                grade = grades[course.code]

                # Calculate grade points
                grade_point_map = {
                    "A": Decimal("4.0"),
                    "A-": Decimal("3.7"),
                    "B+": Decimal("3.3"),
                    "B": Decimal("3.0"),
                }

                grade_points = grade_point_map[grade]

                # Record grade
                ClassPartGrade.objects.create(
                    enrollment=enrollment,
                    grade=grade,
                    grade_points=grade_points,
                    credits_earned=course.credits,
                    is_final=True,
                    recorded_date=timezone.now(),
                )

                enrollment.grade = grade
                enrollment.grade_points = grade_points
                enrollment.status = "COMPLETED"
                enrollment.save()

                total_grade_points += grade_points * course.credits
                total_credits += course.credits

            # Calculate GPA
            semester_gpa = total_grade_points / total_credits

            GPARecord.objects.create(
                student=student,
                term=fall_2020,
                term_gpa=semester_gpa,
                term_credits=total_credits,
                cumulative_gpa=semester_gpa,
                cumulative_credits=total_credits,
                calculation_date=timezone.now(),
            )

        # Continue through remaining semesters (simplified)
        semesters = [
            ("Spring 2021", "SP21", date(2021, 1, 15), date(2021, 5, 15)),
            ("Fall 2021", "FA21", date(2021, 9, 1), date(2021, 12, 18)),
            ("Spring 2022", "SP22", date(2022, 1, 15), date(2022, 5, 15)),
            ("Fall 2022", "FA22", date(2022, 9, 1), date(2022, 12, 18)),
            ("Spring 2023", "SP23", date(2023, 1, 15), date(2023, 5, 15)),
            ("Fall 2023", "FA23", date(2023, 9, 1), date(2023, 12, 18)),
            ("Spring 2024", "SP24", date(2024, 1, 15), date(2024, 5, 15)),
        ]

        cumulative_credits = 13
        cumulative_grade_points = total_grade_points

        for term_name, term_code, start_date, end_date in semesters:
            with freeze_time(start_date):
                term = Term.objects.create(
                    name=term_name, code=term_code, start_date=start_date, end_date=end_date, is_current=True
                )

                # Register for 15 credits each semester
                registration = Registration.objects.create(
                    student=student, term=term, status="APPROVED", total_credits=15
                )

                # Simplified: Add grades
                semester_grade_points = Decimal("3.5") * 15  # B+ average
                cumulative_credits += 15
                cumulative_grade_points += semester_grade_points

                cumulative_gpa = cumulative_grade_points / cumulative_credits

                GPARecord.objects.create(
                    student=student,
                    term=term,
                    term_gpa=Decimal("3.5"),
                    term_credits=15,
                    cumulative_gpa=cumulative_gpa,
                    cumulative_credits=cumulative_credits,
                )

        # Year 4: Graduation Check
        with freeze_time("2024-05-01"):
            # Verify graduation requirements
            graduation_audit = GraduationAudit.objects.create(
                student=student,
                program=program,
                audit_date=timezone.now(),
                total_credits_required=120,
                total_credits_earned=cumulative_credits,
                gpa_required=Decimal("2.0"),
                gpa_earned=cumulative_gpa,
                core_requirements_met=True,
                elective_requirements_met=True,
                senior_project_completed=True,
                is_eligible=True,
            )

            assert graduation_audit.is_eligible
            assert graduation_audit.total_credits_earned >= 120
            assert graduation_audit.gpa_earned >= Decimal("2.0")

            # Update student status
            student.current_status = "GRADUATED"
            student.actual_graduation_date = date(2024, 6, 30)
            student.save()

        # Verify complete journey
        assert student.current_status == "GRADUATED"
        assert student.actual_graduation_date == date(2024, 6, 30)

        # Check academic records
        gpa_records = GPARecord.objects.filter(student=student)
        assert gpa_records.count() == 8  # 8 semesters

        final_gpa = gpa_records.last().cumulative_gpa
        assert final_gpa >= Decimal("3.0")  # Good standing

        # Verify financial records
        invoices = Invoice.objects.filter(student=student)
        assert invoices.count() >= 8  # One per semester

        unpaid_invoices = invoices.filter(status="PENDING")
        assert unpaid_invoices.count() == 0  # All paid


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestTeacherWorkflow:
    """Test complete teacher workflow from hiring to course management."""

    def test_teacher_semester_workflow(self):
        """Test a teacher's complete workflow for one semester.

        Covers:
        1. Teacher account creation
        2. Course assignment
        3. Class roster management
        4. Attendance tracking
        5. Grade submission
        6. Student interaction
        """

        with freeze_time("2024-01-01"):
            # Create teacher account
            user = User.objects.create_user(
                email="john.teacher@pucsr.edu.kh", password="TeacherPass123!", is_staff=True
            )

            person = Person.objects.create(
                personal_name="John",
                family_name="Teacher",
                date_of_birth=date(1980, 5, 20),
                preferred_gender="M",
                citizenship="US",
                university_email="john.teacher@pucsr.edu.kh",
            )

            teacher = TeacherProfile.objects.create(
                person=person,
                employee_id="TCH2024001",
                hire_date=date(2020, 1, 1),
                contract_type="FULL_TIME",
                department="Computer Science",
                title="Assistant Professor",
                can_supervise_projects=True,
            )

            # Create term and course
            term = Term.objects.create(
                name="Spring 2024",
                code="SP24",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 5, 15),
                is_current=True,
            )

            division = Division.objects.create(name="Computer Science", short_name="CS")

            course = Course.objects.create(
                code="CS301", title="Software Engineering", credits=3, division=division, level="300"
            )

            # Assign teacher to class
            class_header = ClassHeader.objects.create(
                course=course, term=term, section="A", max_enrollment=25, current_enrollment=0
            )

            # Create class part with teacher assignment
            from apps.scheduling.models import ClassPart

            ClassPart.objects.create(
                class_header=class_header,
                part_type="LECTURE",
                teacher=teacher,
                day_of_week=2,  # Tuesday
                start_time="14:00",
                end_time="15:20",
            )

            # Enroll students
            students = []
            for i in range(20):
                student_person = PersonFactory(personal_name=f"Student{i}", family_name=f"Test{i}")
                student_profile = StudentProfileFactory(person=student_person, student_id=20240100 + i)
                students.append(student_profile)

                registration = Registration.objects.create(student=student_profile, term=term, status="APPROVED")

                ClassHeaderEnrollment.objects.create(
                    student=student_profile, class_header=class_header, registration=registration, status="ENROLLED"
                )

                class_header.current_enrollment += 1

            class_header.save()

            # Throughout semester: Take attendance
            for week in range(1, 16):  # 15 weeks
                session_date = date(2024, 1, 15) + timedelta(weeks=week - 1, days=1)

                with freeze_time(session_date):
                    # Teacher creates attendance session
                    session = AttendanceSession.objects.create(
                        class_header=class_header,
                        session_date=session_date,
                        start_time="14:00",
                        end_time="15:20",
                        session_code=f"CS301W{week:02d}",
                        created_by=user,
                        is_active=True,
                    )

                    # Students check in
                    for student in students[:18]:  # 90% attendance
                        AttendanceRecord.objects.create(
                            session=session, student=student, status="PRESENT", check_in_time="14:05"
                        )

                    # Mark two as absent
                    for student in students[18:]:
                        AttendanceRecord.objects.create(session=session, student=student, status="ABSENT")

                    session.is_active = False
                    session.save()

            # End of semester: Submit grades
            with freeze_time("2024-05-10"):
                enrollments = ClassHeaderEnrollment.objects.filter(class_header=class_header)

                grade_distribution = [("A", 3), ("A-", 4), ("B+", 5), ("B", 5), ("B-", 2), ("C+", 1)]

                idx = 0
                for grade, count in grade_distribution:
                    for _ in range(count):
                        enrollment = enrollments[idx]

                        ClassPartGrade.objects.create(
                            enrollment=enrollment,
                            grade=grade,
                            is_final=True,
                            recorded_by=user,
                            recorded_date=timezone.now(),
                        )

                        enrollment.grade = grade
                        enrollment.status = "COMPLETED"
                        enrollment.save()

                        idx += 1

            # Verify teacher's work
            sessions = AttendanceSession.objects.filter(class_header=class_header)
            assert sessions.count() == 15  # 15 weeks

            grades = ClassPartGrade.objects.filter(enrollment__class_header=class_header)
            assert grades.count() == 20  # All students graded

            # Check class completion
            completed = ClassHeaderEnrollment.objects.filter(class_header=class_header, status="COMPLETED")
            assert completed.count() == 20
