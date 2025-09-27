"""Grade-related GraphQL mutations."""

import strawberry
from typing import List
from django.db import transaction

from ..types.academic import (
    GradeUpdateInput,
    BulkGradeUpdateInput,
    GradeUpdateResult,
    GradeType,
    AssignmentType,
    CourseType
)


@strawberry.type
class GradeMutations:
    """Grade-related GraphQL mutations."""

    @strawberry.mutation
    def update_grade(
        self,
        info,
        grade_update: GradeUpdateInput
    ) -> GradeUpdateResult:
        """Update a single grade."""

        try:
            # In a real implementation, this would update the actual grade
            # For now, return a mock success response

            mock_grade = GradeType(
                unique_id=str(grade_update.student_id),
                score=grade_update.score,
                assignment=AssignmentType(
                    unique_id=str(grade_update.assignment_id),
                    name="Mock Assignment",
                    assignment_type="exam",
                    max_score=100.0,
                    weight=0.3,
                    is_published=True,
                    course=CourseType(
                        unique_id="1",
                        code="MOCK101",
                        name="Mock Course"
                    )
                ),
                student_id=grade_update.student_id,
                entered_by="current_user",
                entered_at=strawberry.datetime.datetime.now(),
                notes=grade_update.notes
            )

            return GradeUpdateResult(
                success=True,
                message="Grade updated successfully",
                grade=mock_grade
            )

        except Exception as e:
            return GradeUpdateResult(
                success=False,
                message=f"Failed to update grade: {str(e)}",
                grade=None
            )

    @strawberry.mutation
    def bulk_update_grades(
        self,
        info,
        bulk_update: BulkGradeUpdateInput
    ) -> List[GradeUpdateResult]:
        """Bulk update grades for a class."""

        results = []

        with transaction.atomic():
            for grade_update in bulk_update.grade_updates:
                try:
                    # Mock successful update
                    mock_grade = GradeType(
                        unique_id=str(grade_update.student_id),
                        score=grade_update.score,
                        assignment=AssignmentType(
                            unique_id=str(grade_update.assignment_id),
                            name="Mock Assignment",
                            assignment_type="exam",
                            max_score=100.0,
                            weight=0.3,
                            is_published=True,
                            course=CourseType(
                                unique_id="1",
                                code="MOCK101",
                                name="Mock Course"
                            )
                        ),
                        student_id=grade_update.student_id,
                        entered_by="current_user",
                        entered_at=strawberry.datetime.datetime.now(),
                        notes=grade_update.notes
                    )

                    results.append(GradeUpdateResult(
                        success=True,
                        message="Grade updated successfully",
                        grade=mock_grade
                    ))

                except Exception as e:
                    results.append(GradeUpdateResult(
                        success=False,
                        message=f"Failed to update grade: {str(e)}",
                        grade=None
                    ))

        return results