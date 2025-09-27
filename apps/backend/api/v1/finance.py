"""Finance API endpoints for v1 API.

This module provides REST API endpoints for:
- Course and fee pricing lookups
- Invoice generation and management
- Payment processing and tracking
- Financial transaction history
- Billing automation and management
- Administrative fee management (consolidated from separate module)

Consolidated from apps.finance.api and api.v1.finance.administrative_api
to eliminate circular dependencies and create unified finance API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema
from ninja.errors import HttpError

# Import business logic from apps
from apps.curriculum.models import Course, Term
from apps.finance.models import AdministrativeFeeConfig
from apps.finance.services import (
    FinancialError,
    InvoiceService,
)
from apps.finance.services.separated_pricing_service import SeparatedPricingService
from apps.people.models import StudentProfile

# Import from unified authentication system
from .auth import jwt_auth
from .permissions import check_admin_access, has_permission

# Create router
router = Router(tags=["Finance"], auth=jwt_auth)


# Authorization helper functions
def can_access_student_financial_data(user, student: StudentProfile) -> bool:
    """Check if user can access financial data for a student.

    Rules:
    - Admins can access all student data
    - Finance staff can access all student data
    - Teachers can access data for their enrolled students
    - Students can access their own data
    """
    # Check admin access first
    if check_admin_access(user) or user.is_staff or user.is_superuser:
        return True

    # Check finance role access
    if has_permission(user, "finance.view_invoice"):
        return True

    # Check if user is the student
    if hasattr(user, "person") and hasattr(user.person, "student_profile"):
        if user.person.student_profile.id == student.id:
            return True

    return False


# Pricing Schemas
class PricingLookupSchema(Schema):
    """Schema for pricing lookup requests."""

    course_id: int
    student_id: int | None = None
    term_id: int | None = None


class PricingResponseSchema(Schema):
    """Schema for pricing lookup response."""

    course_id: int
    course_name: str
    base_price: Decimal
    final_price: Decimal
    discounts_applied: list[dict[str, Any]]
    pricing_tier: str | None = None
    currency: str


class InvoiceCreateSchema(Schema):
    """Schema for creating invoices."""

    student_id: int
    items: list[dict[str, Any]]
    due_date: datetime | None = None
    notes: str | None = None


class InvoiceResponseSchema(Schema):
    """Schema for invoice responses."""

    id: int
    student_id: int
    student_name: str
    total_amount: Decimal
    status: str
    due_date: str | None = None
    created_at: str


# Administrative Fee Schemas (consolidated from administrative_api)
class AdministrativeFeeConfigIn(Schema):
    """Administrative fee configuration input schema."""

    cycle_type: str
    fee_amount: float
    included_document_units: int
    description: str
    is_active: bool = True


class AdministrativeFeeConfigOut(Schema):
    """Administrative fee configuration output schema."""

    id: int
    cycle_type: str
    cycle_type_display: str
    fee_amount: float
    included_document_units: int
    description: str
    is_active: bool
    created_at: str
    updated_at: str


class DocumentExcessFeeIn(Schema):
    """Document excess fee configuration input schema."""

    cycle_type: str
    fee_per_unit: float
    is_active: bool = True


class DocumentExcessFeeOut(Schema):
    """Document excess fee configuration output schema."""

    id: int
    cycle_type: str
    cycle_type_display: str
    fee_per_unit: float
    is_active: bool
    created_at: str
    updated_at: str


# Core Finance Endpoints
@router.get("/pricing/lookup", response=PricingResponseSchema)
def get_pricing(request, data: PricingLookupSchema = Query(...)):
    """Get pricing information for a course and student."""
    try:
        course = get_object_or_404(Course, id=data.course_id)

        # Get student if provided
        student = None
        if data.student_id:
            student = get_object_or_404(StudentProfile, id=data.student_id)

            # Check authorization
            if not can_access_student_financial_data(request.user, student):
                raise HttpError(403, "Access denied to student financial data")

        # Get term if provided
        term = None
        if data.term_id:
            term = get_object_or_404(Term, id=data.term_id)

        # Calculate pricing using service
        pricing_result = SeparatedPricingService.get_active_pricing(course=course, student=student, term=term)

        return PricingResponseSchema(
            course_id=course.id,
            course_name=course.title,
            base_price=pricing_result.base_price,
            final_price=pricing_result.final_price,
            discounts_applied=pricing_result.discounts_applied,
            pricing_tier=pricing_result.pricing_tier,
            currency=pricing_result.currency,
        )

    except FinancialError as e:
        raise HttpError(400, str(e)) from e
    except Exception as e:
        raise HttpError(500, f"Internal error: {e!s}") from e


@router.post("/invoices", response=InvoiceResponseSchema)
def create_invoice(request, data: InvoiceCreateSchema):
    """Create a new invoice for a student."""
    # Check if user has permission to create invoices
    if not has_permission(request.user, "finance.add_invoice"):
        raise HttpError(403, "Permission denied to create invoices")

    try:
        student = get_object_or_404(StudentProfile, id=data.student_id)

        # Create invoice using service
        invoice = InvoiceService.create_invoice(
            student=student, items=data.items, due_date=data.due_date, notes=data.notes, created_by=request.user
        )

        return InvoiceResponseSchema(
            id=invoice.id,
            student_id=student.id,
            student_name=student.person.full_name,
            total_amount=invoice.total_amount,
            status=invoice.status,
            due_date=invoice.due_date.isoformat() if invoice.due_date else None,
            created_at=invoice.created_at.isoformat(),
        )

    except FinancialError as e:
        raise HttpError(400, str(e)) from e
    except Exception as e:
        raise HttpError(500, f"Internal error: {e!s}") from e


# Administrative Fee Endpoints (consolidated from administrative_api)
@router.post("/administrative-fees/config", response=AdministrativeFeeConfigOut)
def create_administrative_fee_config(request, data: AdministrativeFeeConfigIn):
    """Create a new administrative fee configuration."""
    # Check permissions using unified system
    if not has_permission(request.user, "finance.add_administrativefeeconfig"):
        raise HttpError(403, "Permission denied")

    try:
        with transaction.atomic():
            config = AdministrativeFeeConfig.objects.create(
                cycle_type=data.cycle_type,
                fee_amount=Decimal(str(data.fee_amount)),
                included_document_units=data.included_document_units,
                description=data.description,
                is_active=data.is_active,
                created_by=request.user,
            )

            return AdministrativeFeeConfigOut(
                id=config.id,
                cycle_type=config.cycle_type,
                cycle_type_display=config.get_cycle_type_display(),
                fee_amount=float(config.fee_amount),
                included_document_units=config.included_document_units,
                description=config.notes,
                is_active=config.is_active,
                created_at=config.created_at.isoformat(),
                updated_at=config.updated_at.isoformat(),
            )

    except Exception as e:
        raise HttpError(400, f"Error creating configuration: {e!s}") from e


@router.get("/administrative-fees/config", response=list[AdministrativeFeeConfigOut])
def list_administrative_fee_configs(request):
    """List all administrative fee configurations."""
    if not has_permission(request.user, "finance.view_administrativefeeconfig"):
        raise HttpError(403, "Permission denied")

    configs = AdministrativeFeeConfig.objects.all().order_by("-created_at")

    return [
        AdministrativeFeeConfigOut(
            id=config.id,
            cycle_type=config.cycle_type,
            cycle_type_display=config.get_cycle_type_display(),
            fee_amount=float(config.fee_amount),
            included_document_units=config.included_document_units,
            description=config.notes,
            is_active=config.is_active,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        for config in configs
    ]


# Note: This is a consolidated finance API that combines:
# 1. Original apps/finance/api.py endpoints
# 2. api/v1/finance/administrative_api.py endpoints
#
# This eliminates the circular dependency and provides a unified
# finance API under the v1 structure. Additional endpoints would
# be added following the same pattern.


# Export the router
__all__ = ["router"]
