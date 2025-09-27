"""Academic-related GraphQL queries."""

import strawberry
from typing import List, Optional
from django.shortcuts import get_object_or_404

from apps.scheduling.models import ClassHeader
from apps.grading.models import Assignment, Grade

from ..types.academic import (
    ClassHeaderType,
    GradeSpreadsheetData,
    AssignmentType,
    GradeSpreadsheetRow,
    CourseType
)


@strawberry.type
class AcademicQueries:
    """Academic-related GraphQL queries."""

    @strawberry.field
    def class_header(self, info, class_id: strawberry.ID) -> Optional[ClassHeaderType]:
        """Get a single class header by ID."""
        try:
            class_header = ClassHeader.objects.select_related(
                'course', 'instructor__person', 'term'
            ).get(unique_id=class_id)

            return ClassHeaderType(
                unique_id=str(class_header.unique_id),
                course=CourseType(
                    unique_id=str(class_header.course.unique_id),
                    code=class_header.course.code,
                    name=class_header.course.name,
                    description=class_header.course.description,
                    credit_hours=class_header.course.credit_hours
                ),
                instructor=class_header.instructor.person.full_name if class_header.instructor else None,
                term=class_header.term.name if class_header.term else None,
                capacity=getattr(class_header, 'capacity', None),
                enrolled_count=class_header.enrollments.filter(status='enrolled').count(),
                status=getattr(class_header, 'status', 'active')
            )
        except ClassHeader.DoesNotExist:
            return None

    @strawberry.field
    def grade_spreadsheet(self, info, class_id: strawberry.ID) -> Optional[GradeSpreadsheetData]:
        """Get grade spreadsheet data for a class."""
        try:
            class_header = get_object_or_404(ClassHeader, unique_id=class_id)

            # Get assignments
            assignments = Assignment.objects.filter(
                class_header=class_header
            ).order_by('due_date')

            assignment_types = []
            for assignment in assignments:
                assignment_types.append(AssignmentType(
                    unique_id=str(assignment.unique_id),
                    name=assignment.name,
                    assignment_type=assignment.assignment_type,
                    max_score=float(assignment.max_score),
                    weight=float(assignment.weight),
                    due_date=assignment.due_date,
                    is_published=assignment.is_published,
                    course=CourseType(
                        unique_id=str(class_header.course.unique_id),
                        code=class_header.course.code,
                        name=class_header.course.name
                    )
                ))

            # Get enrollments and grades
            enrollments = class_header.enrollments.filter(
                status='enrolled'
            ).select_related('student__person')

            # Build grade matrix
            rows = []
            for enrollment in enrollments:
                # Get grades for this student
                student_grades = []
                for assignment in assignments:
                    try:
                        grade = Grade.objects.get(
                            enrollment=enrollment,
                            assignment=assignment
                        )
                        student_grades.append(float(grade.score) if grade.score else None)
                    except Grade.DoesNotExist:
                        student_grades.append(None)

                rows.append(GradeSpreadsheetRow(
                    student_id=str(enrollment.student.unique_id),
                    student_name=enrollment.student.person.full_name,
                    grades=student_grades
                ))

            # Calculate completion rate
            total_possible = len(enrollments) * len(assignments)
            total_entered = Grade.objects.filter(
                enrollment__in=enrollments,
                assignment__in=assignments,
                score__isnull=False
            ).count()

            completion_rate = total_entered / total_possible if total_possible > 0 else 0.0

            return GradeSpreadsheetData(
                class_header=ClassHeaderType(
                    unique_id=str(class_header.unique_id),
                    course=CourseType(
                        unique_id=str(class_header.course.unique_id),
                        code=class_header.course.code,
                        name=class_header.course.name
                    ),
                    instructor=class_header.instructor.person.full_name if class_header.instructor else None,
                    term=class_header.term.name if class_header.term else None,
                    enrolled_count=len(enrollments),
                    status='active'
                ),
                assignments=assignment_types,
                rows=rows,
                completion_rate=completion_rate,
                last_modified=class_header.last_modified
            )

        except ClassHeader.DoesNotExist:
            return None