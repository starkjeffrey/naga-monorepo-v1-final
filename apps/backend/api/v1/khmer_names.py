"""API endpoints for Khmer name approximation and correction."""

import logging
from typing import List

from ninja import Router
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from api.v1.auth import jwt_auth
from apps.people.models import Person, KhmerNameCorrection
from apps.people.services.khmer_approximator import KhmerNameApproximator
from apps.people.services.pattern_learner import PatternLearner
from .schemas import ErrorResponse


logger = logging.getLogger(__name__)

router = Router(auth=jwt_auth, tags=["khmer-names"])


# Schemas
from ninja import Schema
from typing import Optional


class KhmerNameSubmissionSchema(Schema):
    """Schema for submitting correct Khmer name."""
    khmer_name: str
    is_verification: bool = False  # True if user is verifying existing name


class KhmerNameResponseSchema(Schema):
    """Schema for Khmer name response."""
    english_name: str
    khmer_name: str
    is_approximated: bool
    confidence: float
    can_edit: bool
    source: str
    approximated_at: Optional[str] = None
    verified_at: Optional[str] = None


class ApproximationRequestSchema(Schema):
    """Schema for requesting name approximation."""
    english_name: str


class ApproximationResponseSchema(Schema):
    """Schema for approximation response."""
    original_english: str
    approximated_khmer: str
    confidence_score: float
    is_approximation: bool
    method_used: str
    components_used: List[dict]
    warnings: List[str]


class CorrectionResponseSchema(Schema):
    """Schema for correction submission response."""
    status: str
    message: str
    previous_name: str
    new_name: str
    learning_results: dict


class NameStatsSchema(Schema):
    """Schema for name statistics."""
    total_people: int
    with_khmer_names: int
    approximated: int
    user_provided: int
    verified: int
    coverage_percentage: float
    approximation_percentage: float
    avg_confidence: Optional[float]


# Endpoints

@router.get("/verify", response=KhmerNameResponseSchema)
def get_name_for_verification(request):
    """Get current Khmer name for user verification.

    Returns the user's current Khmer name information including
    whether it's approximated and editing permissions.
    """
    try:
        person = request.user.person
    except AttributeError:
        return {"error": "User has no associated person record"}, 404

    return {
        "english_name": f"{person.family_name} {person.personal_name}".strip(),
        "khmer_name": person.khmer_name or "",
        "is_approximated": person.khmer_name_source == 'approximated',
        "confidence": float(person.khmer_name_confidence or 0.0),
        "can_edit": True,
        "source": person.khmer_name_source,
        "approximated_at": person.khmer_name_approximated_at.isoformat() if person.khmer_name_approximated_at else None,
        "verified_at": person.khmer_name_verified_at.isoformat() if person.khmer_name_verified_at else None
    }


@router.post("/submit", response=CorrectionResponseSchema)
def submit_khmer_name(request, data: KhmerNameSubmissionSchema):
    """Allow users to submit their correct Khmer name.

    This endpoint handles both corrections of approximated names
    and initial submissions of Khmer names.
    """
    try:
        person = request.user.person
    except AttributeError:
        return {"error": "User has no associated person record"}, 404

    if not data.khmer_name.strip():
        return {"error": "Khmer name cannot be empty"}, 400

    logger.info(f"Khmer name submission from user {request.user.id} for person {person.id}")

    try:
        with transaction.atomic():
            # Store the previous name for response
            previous_name = person.khmer_name or ""

            # Create correction record
            correction = KhmerNameCorrection.objects.create(
                person=person,
                original_khmer_name=previous_name,
                corrected_khmer_name=data.khmer_name.strip(),
                original_english_name=f"{person.family_name} {person.personal_name}",
                correction_source='mobile_app',
                created_by=request.user
            )

            # Apply correction and learn from it
            correction.apply_correction()

            # Learn from the correction to improve patterns
            learner = PatternLearner()
            learning_results = learner.learn_from_correction(correction)

            logger.info(f"Successfully processed Khmer name correction for person {person.id}")

            return {
                "status": "success",
                "message": "Khmer name updated successfully",
                "previous_name": previous_name,
                "new_name": data.khmer_name.strip(),
                "learning_results": learning_results
            }

    except Exception as e:
        logger.error(f"Error submitting Khmer name for person {person.id}: {e}")
        return {"error": "Failed to update Khmer name"}, 500


@router.post("/approximate", response=ApproximationResponseSchema)
def approximate_name(request, data: ApproximationRequestSchema):
    """Approximate a Khmer name from English name.

    This endpoint is primarily for testing and admin use.
    It approximates a Khmer name without saving it.
    """
    if not data.english_name.strip():
        return {"error": "English name cannot be empty"}, 400

    try:
        approximator = KhmerNameApproximator()
        result = approximator.approximate_name(data.english_name.strip())

        return {
            "original_english": result.original_english,
            "approximated_khmer": result.approximated_khmer,
            "confidence_score": result.confidence_score,
            "is_approximation": result.is_approximation,
            "method_used": result.method_used,
            "components_used": result.components_used,
            "warnings": result.warnings
        }

    except Exception as e:
        logger.error(f"Error approximating name '{data.english_name}': {e}")
        return {"error": "Failed to approximate name"}, 500


@router.get("/stats", response=NameStatsSchema)
def get_name_statistics(request):
    """Get statistics about Khmer names in the system.

    Returns overall statistics about name coverage and approximation quality.
    """
    try:
        approximator = KhmerNameApproximator()
        stats = approximator.get_approximation_stats()

        return {
            "total_people": stats['total_people'],
            "with_khmer_names": stats['with_khmer_names'],
            "approximated": stats['approximated'],
            "user_provided": stats['user_provided'],
            "verified": stats['verified'],
            "coverage_percentage": stats['coverage_percentage'],
            "approximation_percentage": stats['approximation_percentage'],
            "avg_confidence": float(stats['avg_confidence']) if stats['avg_confidence'] else None
        }

    except Exception as e:
        logger.error(f"Error getting name statistics: {e}")
        return {"error": "Failed to get statistics"}, 500


@router.get("/corrections", response=List[dict])
def get_user_corrections(request):
    """Get correction history for the current user."""
    try:
        person = request.user.person
    except AttributeError:
        return {"error": "User has no associated person record"}, 404

    corrections = KhmerNameCorrection.objects.filter(
        person=person
    ).order_by('-created_at')[:10]  # Last 10 corrections

    return [
        {
            "id": correction.id,
            "original_khmer_name": correction.original_khmer_name,
            "corrected_khmer_name": correction.corrected_khmer_name,
            "correction_source": correction.correction_source,
            "created_at": correction.created_at.isoformat(),
            "verified_at": correction.verified_at.isoformat() if correction.verified_at else None,
            "patterns_learned_count": len(correction.patterns_learned.get('patterns', [])) if correction.patterns_learned else 0
        }
        for correction in corrections
    ]


@router.get("/person/{person_id}/name", response=KhmerNameResponseSchema)
def get_person_khmer_name(request, person_id: int):
    """Get Khmer name information for a specific person.

    This endpoint is for admin/staff use to view any person's name data.
    """
    # Check if user has permission to view other people's data
    if not (request.user.is_staff or request.user.is_superuser):
        # Regular users can only access their own data
        try:
            if request.user.person.id != person_id:
                return {"error": "Permission denied"}, 403
        except AttributeError:
            return {"error": "Permission denied"}, 403

    person = get_object_or_404(Person, id=person_id)

    return {
        "english_name": f"{person.family_name} {person.personal_name}".strip(),
        "khmer_name": person.khmer_name or "",
        "is_approximated": person.khmer_name_source == 'approximated',
        "confidence": float(person.khmer_name_confidence or 0.0),
        "can_edit": True,
        "source": person.khmer_name_source,
        "approximated_at": person.khmer_name_approximated_at.isoformat() if person.khmer_name_approximated_at else None,
        "verified_at": person.khmer_name_verified_at.isoformat() if person.khmer_name_verified_at else None
    }


@router.post("/person/{person_id}/approximate")
def approximate_person_name(request, person_id: int):
    """Approximate Khmer name for a specific person.

    This endpoint is for admin use to trigger approximation for specific people.
    """
    # Only staff can trigger approximations for others
    if not (request.user.is_staff or request.user.is_superuser):
        return {"error": "Permission denied"}, 403

    person = get_object_or_404(Person, id=person_id)

    try:
        approximator = KhmerNameApproximator()
        result = approximator.approximate_for_person(person)

        # If confidence is good enough, save the approximation
        if result.confidence_score >= 0.5:
            person.khmer_name = result.display_name
            person.khmer_name_source = 'approximated'
            person.khmer_name_confidence = result.confidence_score
            person.khmer_name_approximated_at = timezone.now()
            person.khmer_name_components = {
                'original_english': result.original_english,
                'components_used': result.components_used,
                'method_used': result.method_used,
                'warnings': result.warnings
            }
            person.save(update_fields=[
                'khmer_name',
                'khmer_name_source',
                'khmer_name_confidence',
                'khmer_name_approximated_at',
                'khmer_name_components'
            ])

            return {
                "status": "approximated",
                "english_name": result.original_english,
                "khmer_name": result.display_name,
                "confidence": result.confidence_score,
                "method": result.method_used
            }
        else:
            return {
                "status": "low_confidence",
                "english_name": result.original_english,
                "confidence": result.confidence_score,
                "method": result.method_used,
                "message": "Confidence too low to save approximation"
            }

    except Exception as e:
        logger.error(f"Error approximating name for person {person_id}: {e}")
        return {"error": "Failed to approximate name"}, 500


@router.get("/quality-report")
def get_quality_report(request):
    """Get approximation quality report.

    This endpoint is for admin use to monitor system performance.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return {"error": "Permission denied"}, 403

    try:
        approximator = KhmerNameApproximator()
        quality_report = approximator.validate_approximation_quality(sample_size=200)

        learner = PatternLearner()
        correction_analysis = learner.analyze_correction_patterns()
        pattern_suggestions = learner.suggest_pattern_improvements()

        return {
            "quality_metrics": quality_report,
            "correction_analysis": correction_analysis,
            "pattern_suggestions": pattern_suggestions[:10],  # Top 10 suggestions
            "generated_at": timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating quality report: {e}")
        return {"error": "Failed to generate report"}, 500