"""API endpoints for document requests with quota integration."""

from typing import Any, cast

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from api.v1.auth import JWTAuth
from api.v1.permissions import has_student_permission
from apps.academic_records.models import (
    DocumentRequest,
    DocumentTypeConfig,
)
from apps.academic_records.services import DocumentQuotaService
from apps.curriculum.models import Term
from apps.people.models import StudentProfile

router = Router(auth=JWTAuth())


class DocumentTypeOut(Schema):
    """Document type output schema."""

    id: int
    code: str
    name: str
    category: str
    description: str
    unit_cost: int
    processing_time_hours: int
    available_delivery_methods: list[str]
    has_fee: bool
    fee_amount: float | None


class QuotaSummaryOut(Schema):
    """Document quota summary output schema."""

    has_quota: bool
    total_units: int
    used_units: int
    remaining_units: int
    usage_percentage: float
    is_expired: bool
    expires_date: str | None
    cycle_type: str | None


class DocumentRequestIn(Schema):
    """Document request input schema."""

    document_type_id: int
    delivery_method: str
    request_notes: str | None = ""
    recipient_name: str | None = ""
    recipient_email: str | None = ""
    recipient_address: str | None = ""
    term_id: int | None = None


class DocumentRequestOut(Schema):
    """Document request output schema."""

    id: int
    request_id: str
    document_type: DocumentTypeOut
    request_status: str
    delivery_method: str
    requested_date: str
    due_date: str | None
    has_fee: bool
    fee_amount: float | None
    is_free_allowance: bool
    payment_status: str
    quota_used: bool
    excess_units: int
    request_notes: str


class DocumentQuotaCheckOut(Schema):
    """Quota check result schema."""

    document_type: DocumentTypeOut
    units_required: int
    quota_summary: QuotaSummaryOut
    will_use_quota: bool
    excess_units: int
    excess_fee_per_unit: float | None
    total_excess_fee: float | None


@router.get("/document-types", response=list[DocumentTypeOut])
def list_document_types(request):
    """List all active document types."""
    types = DocumentTypeConfig.objects.filter(is_active=True).order_by("display_order", "name")
    results: list[DocumentTypeOut] = []
    for dt in types:
        d = cast("Any", dt)
        results.append(
            DocumentTypeOut(
                id=d.id,
                code=d.code,
                name=d.name,
                category=d.category,
                description=d.description,
                unit_cost=d.unit_cost,
                processing_time_hours=d.processing_time_hours,
                available_delivery_methods=d.available_delivery_methods,
                has_fee=d.has_fee,
                fee_amount=float(d.fee_amount) if d.fee_amount else None,
            ),
        )
    return results


@router.get("/students/{student_id}/quota-summary", response=QuotaSummaryOut)
def get_student_quota_summary(request, student_id: int, term_id: int | None = None):
    """Get document quota summary for a student."""
    # Check permissions
    if not has_student_permission(request.user, student_id):
        raise HttpError(403, "You don't have permission to view this student's quota")

    student = get_object_or_404(StudentProfile, id=student_id)

    # Get term
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.get_current_term()

    if not term:
        raise HttpError(400, "No active term found")

    # Get quota summary
    summary = DocumentQuotaService.get_quota_summary(student, term)

    return QuotaSummaryOut(
        has_quota=summary["has_quota"],
        total_units=summary["total_units"],
        used_units=summary["used_units"],
        remaining_units=summary["remaining_units"],
        usage_percentage=summary["usage_percentage"],
        is_expired=summary["is_expired"],
        expires_date=summary["expires_date"].isoformat() if summary["expires_date"] else None,
        cycle_type=summary["cycle_type"],
    )


@router.post("/students/{student_id}/check-quota", response=DocumentQuotaCheckOut)
def check_document_quota(request, student_id: int, document_type_id: int, term_id: int | None = None):
    """Check if student has quota for a document type."""
    # Check permissions
    if not has_student_permission(request.user, student_id):
        raise HttpError(403, "You don't have permission to check this student's quota")

    student = get_object_or_404(StudentProfile, id=student_id)
    document_type = get_object_or_404(DocumentTypeConfig, id=document_type_id, is_active=True)

    # Get term
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.get_current_term()

    if not term:
        raise HttpError(400, "No active term found")

    # Get quota summary
    quota_summary = DocumentQuotaService.get_quota_summary(student, term)

    # Check if quota would be used
    units_required = document_type.unit_cost
    will_use_quota = False
    excess_units = 0
    excess_fee_per_unit = None
    total_excess_fee = None

    if quota_summary["has_quota"]:
        if quota_summary["remaining_units"] >= units_required:
            will_use_quota = True
            excess_units = 0
        else:
            will_use_quota = quota_summary["remaining_units"] > 0
            excess_units = units_required - quota_summary["remaining_units"]

            # Get excess fee configuration
            from apps.enrollment.models import StudentCycleStatus
            from apps.finance.models import DocumentExcessFee

            # Get student's cycle status
            cycle_status = StudentCycleStatus.objects.filter(student=student, is_active=True).first()

            if cycle_status:
                excess_config = DocumentExcessFee.objects.filter(
                    cycle_type=cycle_status.cycle_type, is_active=True
                ).first()

                if excess_config:
                    excess_fee_per_unit = float(excess_config.fee_per_unit)
                    total_excess_fee = float(excess_config.fee_per_unit * excess_units)
    else:
        excess_units = units_required

    dt_cfg = cast("Any", document_type)
    return DocumentQuotaCheckOut(
        document_type=DocumentTypeOut(
            id=dt_cfg.id,
            code=dt_cfg.code,
            name=dt_cfg.name,
            category=dt_cfg.category,
            description=dt_cfg.description,
            unit_cost=dt_cfg.unit_cost,
            processing_time_hours=dt_cfg.processing_time_hours,
            available_delivery_methods=dt_cfg.available_delivery_methods,
            has_fee=dt_cfg.has_fee,
            fee_amount=float(dt_cfg.fee_amount) if dt_cfg.fee_amount else None,
        ),
        units_required=units_required,
        quota_summary=QuotaSummaryOut(
            has_quota=quota_summary["has_quota"],
            total_units=quota_summary["total_units"],
            used_units=quota_summary["used_units"],
            remaining_units=quota_summary["remaining_units"],
            usage_percentage=quota_summary["usage_percentage"],
            is_expired=quota_summary["is_expired"],
            expires_date=quota_summary["expires_date"].isoformat() if quota_summary["expires_date"] else None,
            cycle_type=quota_summary["cycle_type"],
        ),
        will_use_quota=will_use_quota,
        excess_units=excess_units,
        excess_fee_per_unit=excess_fee_per_unit,
        total_excess_fee=total_excess_fee,
    )


@router.post("/students/{student_id}/document-requests", response=DocumentRequestOut)
@transaction.atomic
def create_document_request(request, student_id: int, data: DocumentRequestIn):
    """Create a new document request with quota processing."""
    # Check permissions
    if not has_student_permission(request.user, student_id):
        raise HttpError(403, "You don't have permission to create requests for this student")

    student = get_object_or_404(StudentProfile, id=student_id)
    document_type = get_object_or_404(DocumentTypeConfig, id=data.document_type_id, is_active=True)

    # Validate delivery method
    if data.delivery_method not in document_type.available_delivery_methods:
        raise HttpError(400, f"Delivery method {data.delivery_method} not available for this document type")

    # Create document request
    document_request = DocumentRequest.objects.create(
        document_type=document_type,
        student=student,
        delivery_method=data.delivery_method,
        request_notes=data.request_notes,
        recipient_name=data.recipient_name,
        recipient_email=data.recipient_email,
        recipient_address=data.recipient_address,
        requested_by=request.user,
    )

    # Process quota
    _success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(document_request)

    # Determine quota usage
    quota_used = quota_usage is not None
    excess_units = 0

    if excess_charge:
        excess_units = int(excess_charge.quantity)

    # Update request with payment information if excess charge was created
    if excess_charge:
        document_request.has_fee = True
        document_request.fee_amount = excess_charge.line_total
        document_request.payment_required = True
        document_request.payment_status = "PENDING"
        document_request.finance_invoice_id = excess_charge.invoice.id
        document_request.save()

    dr = cast("Any", document_request)
    dt = cast("Any", document_type)
    return DocumentRequestOut(
        id=dr.id,
        request_id=str(document_request.request_id),
        document_type=DocumentTypeOut(
            id=dt.id,
            code=dt.code,
            name=dt.name,
            category=dt.category,
            description=dt.description,
            unit_cost=dt.unit_cost,
            processing_time_hours=dt.processing_time_hours,
            available_delivery_methods=dt.available_delivery_methods,
            has_fee=dt.has_fee,
            fee_amount=float(dt.fee_amount) if dt.fee_amount else None,
        ),
        request_status=dr.request_status,
        delivery_method=dr.delivery_method,
        requested_date=dr.requested_date.isoformat(),
        due_date=dr.due_date.isoformat() if dr.due_date else None,
        has_fee=dr.has_fee,
        fee_amount=float(dr.fee_amount) if dr.fee_amount else None,
        is_free_allowance=dr.is_free_allowance,
        payment_status=dr.payment_status,
        quota_used=quota_used,
        excess_units=excess_units,
        request_notes=dr.request_notes,
    )


@router.get("/students/{student_id}/document-requests", response=list[DocumentRequestOut])
def list_student_document_requests(request, student_id: int):
    """List all document requests for a student."""
    # Check permissions
    if not has_student_permission(request.user, student_id):
        raise HttpError(403, "You don't have permission to view this student's requests")

    student = get_object_or_404(StudentProfile, id=student_id)

    requests = (
        DocumentRequest.objects.filter(student=student).select_related("document_type").order_by("-requested_date")
    )

    results: list[DocumentRequestOut] = []
    for req in requests:
        r = cast("Any", req)
        # Check if quota was used
        quota_usage = r.quota_usage.first()
        quota_used = quota_usage is not None

        # Calculate excess units from line items if any
        excess_units = 0
        if r.finance_invoice_id:
            from apps.finance.models import InvoiceLineItem

            excess_line = InvoiceLineItem.objects.filter(
                invoice_id=r.finance_invoice_id, line_item_type=InvoiceLineItem.LineItemType.DOC_EXCESS
            ).first()
            if excess_line:
                excess_units = int(excess_line.quantity)

        results.append(
            DocumentRequestOut(
                id=r.id,
                request_id=str(r.request_id),
                document_type=DocumentTypeOut(
                    id=r.document_type.id,
                    code=r.document_type.code,
                    name=r.document_type.name,
                    category=r.document_type.category,
                    description=r.document_type.description,
                    unit_cost=r.document_type.unit_cost,
                    processing_time_hours=r.document_type.processing_time_hours,
                    available_delivery_methods=r.document_type.available_delivery_methods,
                    has_fee=r.document_type.has_fee,
                    fee_amount=float(r.document_type.fee_amount) if r.document_type.fee_amount else None,
                ),
                request_status=r.request_status,
                delivery_method=r.delivery_method,
                requested_date=r.requested_date.isoformat(),
                due_date=r.due_date.isoformat() if r.due_date else None,
                has_fee=r.has_fee,
                fee_amount=float(r.fee_amount) if r.fee_amount else None,
                is_free_allowance=r.is_free_allowance,
                payment_status=r.payment_status,
                quota_used=quota_used,
                excess_units=excess_units,
                request_notes=r.request_notes,
            )
        )

    return results
