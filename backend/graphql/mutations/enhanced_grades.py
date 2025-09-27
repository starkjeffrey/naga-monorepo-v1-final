"""Enhanced Grade mutations for real-time collaboration."""

import logging
from typing import List, Optional
import strawberry
from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from apps.grading.models import Grade, Assignment
from apps.enrollment.models import ClassHeaderEnrollment
from apps.scheduling.models import ClassHeader

from ..types.enhanced_student import BulkActionResult

logger = logging.getLogger(__name__)


@strawberry.input
class GradeEntryInput:
    """Input for grade entry."""
    student_id: strawberry.ID
    assignment_id: strawberry.ID
    score: Optional[float] = None
    max_score: float
    notes: Optional[str] = None


@strawberry.input
class BulkGradeUpdateInput:
    """Input for bulk grade updates."""
    class_id: strawberry.ID
    grades: List[GradeEntryInput]
    notify_students: bool = False


@strawberry.input
class GradeCollaborationInput:
    """Input for collaborative grade editing."""
    class_id: strawberry.ID
    user_id: strawberry.ID
    action: str  # "lock", "unlock", "update", "comment"
    cell_reference: Optional[str] = None  # "student_123_assignment_456"
    data: Optional[str] = None  # JSON string with action data


@strawberry.type
class GradeUpdateResult:
    """Result of grade update operation."""
    success: bool
    message: str
    grade_id: Optional[strawberry.ID] = None
    updated_score: Optional[float] = None
    validation_errors: List[str] = strawberry.field(default_factory=list)


@strawberry.type
class CollaborationState:
    """Current collaboration state for grade editing."""
    class_id: strawberry.ID
    active_users: List[str]
    locked_cells: List[str]
    last_updated: datetime
    version: int


@strawberry.type
class EnhancedGradeMutations:
    """Enhanced grade mutations with real-time collaboration."""

    @strawberry.mutation
    def update_grade(
        self,
        student_id: strawberry.ID,
        assignment_id: strawberry.ID,
        score: Optional[float] = None,
        max_score: Optional[float] = None,
        notes: Optional[str] = None
    ) -> GradeUpdateResult:
        """Update a single grade with validation."""

        try:
            # Get enrollment and assignment
            enrollment = get_object_or_404(
                ClassHeaderEnrollment,
                student_profile__unique_id=student_id
            )
            assignment = get_object_or_404(Assignment, unique_id=assignment_id)

            # Validate score
            validation_errors = []
            if score is not None:
                if score < 0:
                    validation_errors.append("Score cannot be negative")
                if max_score and score > max_score:
                    validation_errors.append("Score cannot exceed maximum score")

            if validation_errors:
                return GradeUpdateResult(
                    success=False,
                    message="Validation failed",
                    validation_errors=validation_errors
                )

            # Get or create grade
            grade, created = Grade.objects.get_or_create(
                class_header_enrollment=enrollment,
                assignment=assignment,
                defaults={
                    'score': score,
                    'max_score': max_score or assignment.max_score,
                    'notes': notes
                }
            )

            if not created:
                # Update existing grade
                if score is not None:
                    grade.score = score
                if max_score is not None:
                    grade.max_score = max_score
                if notes is not None:
                    grade.notes = notes
                grade.save()

            # Invalidate related caches
            cache_keys = [
                f"student_analytics_{enrollment.student_profile.unique_id}",
                f"class_grades_{assignment.class_header.unique_id}",
                f"enhanced_student_{enrollment.student_profile.unique_id}"
            ]
            cache.delete_many(cache_keys)

            return GradeUpdateResult(
                success=True,
                message="Grade updated successfully",
                grade_id=str(grade.unique_id),
                updated_score=grade.score
            )

        except Exception as e:
            logger.error("Failed to update grade: %s", e)
            return GradeUpdateResult(
                success=False,
                message=f"Update failed: {str(e)}"
            )

    @strawberry.mutation
    def bulk_update_grades(self, input: BulkGradeUpdateInput) -> BulkActionResult:
        """Bulk update grades for a class with transaction safety."""

        class_header = get_object_or_404(ClassHeader, unique_id=input.class_id)
        success_count = 0
        failed_ids = []

        try:
            with transaction.atomic():
                for grade_input in input.grades:
                    try:
                        # Get enrollment
                        enrollment = ClassHeaderEnrollment.objects.get(
                            student_profile__unique_id=grade_input.student_id,
                            class_header=class_header
                        )

                        # Get assignment
                        assignment = Assignment.objects.get(
                            unique_id=grade_input.assignment_id
                        )

                        # Update or create grade
                        grade, created = Grade.objects.get_or_create(
                            class_header_enrollment=enrollment,
                            assignment=assignment,
                            defaults={
                                'score': grade_input.score,
                                'max_score': grade_input.max_score,
                                'notes': grade_input.notes
                            }
                        )

                        if not created:
                            grade.score = grade_input.score
                            grade.max_score = grade_input.max_score
                            grade.notes = grade_input.notes
                            grade.save()

                        success_count += 1

                    except Exception as e:
                        logger.error("Failed to update grade for student %s: %s",
                                   grade_input.student_id, e)
                        failed_ids.append(grade_input.student_id)

            # Clear relevant caches
            cache.delete_many([
                f"class_grades_{class_header.unique_id}",
                f"grade_spreadsheet_{class_header.unique_id}"
            ])

            # TODO: Send notifications if requested
            if input.notify_students and success_count > 0:
                # Implement notification sending
                pass

            return BulkActionResult(
                success=True,
                processed_count=success_count,
                failed_count=len(failed_ids),
                failed_ids=failed_ids,
                message=f"Updated {success_count} grades successfully"
            )

        except Exception as e:
            logger.error("Bulk grade update failed: %s", e)
            return BulkActionResult(
                success=False,
                processed_count=0,
                failed_count=len(input.grades),
                failed_ids=[g.student_id for g in input.grades],
                message=f"Bulk update failed: {str(e)}"
            )

    @strawberry.mutation
    def start_grade_collaboration(
        self,
        class_id: strawberry.ID,
        user_id: strawberry.ID
    ) -> CollaborationState:
        """Start collaborative grade editing session."""

        # Use Redis for real-time collaboration state
        collaboration_key = f"grade_collaboration:{class_id}"

        # Get current state
        current_state = cache.get(collaboration_key, {
            'active_users': [],
            'locked_cells': [],
            'version': 0
        })

        # Add user to active users
        if str(user_id) not in current_state['active_users']:
            current_state['active_users'].append(str(user_id))

        current_state['last_updated'] = datetime.now()
        current_state['version'] += 1

        # Store state with 30-minute expiry
        cache.set(collaboration_key, current_state, 1800)

        return CollaborationState(
            class_id=class_id,
            active_users=current_state['active_users'],
            locked_cells=current_state['locked_cells'],
            last_updated=current_state['last_updated'],
            version=current_state['version']
        )

    @strawberry.mutation
    def end_grade_collaboration(
        self,
        class_id: strawberry.ID,
        user_id: strawberry.ID
    ) -> CollaborationState:
        """End collaborative grade editing session."""

        collaboration_key = f"grade_collaboration:{class_id}"

        current_state = cache.get(collaboration_key, {
            'active_users': [],
            'locked_cells': [],
            'version': 0
        })

        # Remove user from active users
        if str(user_id) in current_state['active_users']:
            current_state['active_users'].remove(str(user_id))

        # Remove any cells locked by this user
        user_locked_cells = [
            cell for cell in current_state['locked_cells']
            if cell.endswith(f":{user_id}")
        ]
        for cell in user_locked_cells:
            current_state['locked_cells'].remove(cell)

        current_state['last_updated'] = datetime.now()
        current_state['version'] += 1

        cache.set(collaboration_key, current_state, 1800)

        return CollaborationState(
            class_id=class_id,
            active_users=current_state['active_users'],
            locked_cells=current_state['locked_cells'],
            last_updated=current_state['last_updated'],
            version=current_state['version']
        )

    @strawberry.mutation
    def lock_grade_cell(
        self,
        class_id: strawberry.ID,
        user_id: strawberry.ID,
        cell_reference: str
    ) -> CollaborationState:
        """Lock a grade cell for editing."""

        collaboration_key = f"grade_collaboration:{class_id}"
        current_state = cache.get(collaboration_key, {
            'active_users': [],
            'locked_cells': [],
            'version': 0
        })

        # Check if cell is already locked by another user
        lock_key = f"{cell_reference}:{user_id}"
        existing_locks = [
            cell for cell in current_state['locked_cells']
            if cell.startswith(f"{cell_reference}:") and not cell.endswith(f":{user_id}")
        ]

        if not existing_locks:
            # Lock the cell
            current_state['locked_cells'].append(lock_key)
            current_state['version'] += 1
            current_state['last_updated'] = datetime.now()

            cache.set(collaboration_key, current_state, 1800)

        return CollaborationState(
            class_id=class_id,
            active_users=current_state['active_users'],
            locked_cells=current_state['locked_cells'],
            last_updated=current_state['last_updated'],
            version=current_state['version']
        )

    @strawberry.mutation
    def unlock_grade_cell(
        self,
        class_id: strawberry.ID,
        user_id: strawberry.ID,
        cell_reference: str
    ) -> CollaborationState:
        """Unlock a grade cell."""

        collaboration_key = f"grade_collaboration:{class_id}"
        current_state = cache.get(collaboration_key, {
            'active_users': [],
            'locked_cells': [],
            'version': 0
        })

        # Remove lock for this user and cell
        lock_key = f"{cell_reference}:{user_id}"
        if lock_key in current_state['locked_cells']:
            current_state['locked_cells'].remove(lock_key)
            current_state['version'] += 1
            current_state['last_updated'] = datetime.now()

            cache.set(collaboration_key, current_state, 1800)

        return CollaborationState(
            class_id=class_id,
            active_users=current_state['active_users'],
            locked_cells=current_state['locked_cells'],
            last_updated=current_state['last_updated'],
            version=current_state['version']
        )

    @strawberry.mutation
    def calculate_final_grades(
        self,
        class_id: strawberry.ID,
        grading_scale_id: Optional[strawberry.ID] = None
    ) -> BulkActionResult:
        """Calculate final grades for all students in a class."""

        try:
            class_header = get_object_or_404(ClassHeader, unique_id=class_id)

            # Get all enrollments for this class
            enrollments = ClassHeaderEnrollment.objects.filter(
                class_header=class_header,
                status='enrolled'
            ).prefetch_related('grades__assignment')

            success_count = 0
            failed_ids = []

            with transaction.atomic():
                for enrollment in enrollments:
                    try:
                        # Calculate weighted average of all grades
                        grades = enrollment.grades.exclude(score__isnull=True)

                        if grades.exists():
                            total_weighted_score = 0
                            total_weight = 0

                            for grade in grades:
                                if grade.assignment and grade.assignment.weight:
                                    weight = float(grade.assignment.weight)
                                    score_percentage = grade.score / grade.max_score
                                    total_weighted_score += score_percentage * weight
                                    total_weight += weight

                            if total_weight > 0:
                                final_percentage = total_weighted_score / total_weight

                                # Create or update final grade assignment
                                final_assignment, created = Assignment.objects.get_or_create(
                                    class_header=class_header,
                                    assignment_type='final',
                                    defaults={
                                        'name': 'Final Grade',
                                        'max_score': 100,
                                        'weight': 1.0
                                    }
                                )

                                # Create or update final grade
                                final_grade, grade_created = Grade.objects.get_or_create(
                                    class_header_enrollment=enrollment,
                                    assignment=final_assignment,
                                    defaults={
                                        'score': final_percentage * 100,
                                        'max_score': 100
                                    }
                                )

                                if not grade_created:
                                    final_grade.score = final_percentage * 100
                                    final_grade.save()

                                success_count += 1

                    except Exception as e:
                        logger.error("Failed to calculate final grade for %s: %s",
                                   enrollment.student_profile.unique_id, e)
                        failed_ids.append(str(enrollment.student_profile.unique_id))

            # Clear caches
            cache.delete_many([
                f"class_grades_{class_header.unique_id}",
                f"grade_spreadsheet_{class_header.unique_id}"
            ])

            return BulkActionResult(
                success=True,
                processed_count=success_count,
                failed_count=len(failed_ids),
                failed_ids=failed_ids,
                message=f"Calculated final grades for {success_count} students"
            )

        except Exception as e:
            logger.error("Final grade calculation failed: %s", e)
            return BulkActionResult(
                success=False,
                processed_count=0,
                failed_count=0,
                failed_ids=[],
                message=f"Final grade calculation failed: {str(e)}"
            )