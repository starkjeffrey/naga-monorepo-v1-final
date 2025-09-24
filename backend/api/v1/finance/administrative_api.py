"""API endpoints for administrative fee management."""

from decimal import Decimal
from typing import Any, cast

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from api.v1.auth import JWTAuth
from api.v1.permissions import has_permission
from apps.curriculum.models import Term
from apps.enrollment.models import StudentCycleStatus
from apps.finance.models import AdministrativeFeeConfig, DocumentExcessFee
from apps.finance.services import AdministrativeFeeService

router = Router(auth=JWTAuth())


class AdministrativeFeeConfigIn(Schema):
    """Administrative fee configuration input schema."""

    cycle_type: str
    fee_amount: float
    included_document_units: int
    notes: str
    is_active: bool = True
    effective_date: str
    end_date: str | None = None


class AdministrativeFeeConfigOut(Schema):
    """Administrative fee configuration output schema."""

    id: int
    cycle_type: str
    cycle_type_display: str
    fee_amount: float
    included_document_units: int
    notes: str
    is_active: bool
    effective_date: str
    end_date: str | None
    created_at: str
    updated_at: str


class DocumentExcessFeeIn(Schema):
    """Document excess fee configuration input schema."""

    units_charged: int
    unit_price: float
    document_request_id: int
    invoice_line_item_id: int


class DocumentExcessFeeOut(Schema):
    """Document excess fee configuration output schema."""

    id: int
    units_charged: int
    unit_price: float
    total_amount: float
    document_request_id: int
    invoice_line_item_id: int
    created_at: str
    updated_at: str


class ProcessingResultOut(Schema):
    """Term processing result schema."""

    processed: int
    fees_applied: int
    total_revenue: float
    errors: list[dict]


class StudentCycleStatusOut(Schema):
    """Student cycle status output schema."""

    id: int
    student_id: int
    student_name: str
    student_number: int
    cycle_type: str
    cycle_type_display: str
    source_program: str | None
    target_program: str
    detected_date: str
    is_active: bool
    deactivated_date: str | None
    deactivation_reason: str | None


# Administrative Fee Configuration Endpoints


@router.get("/admin-fee-configs", response=list[AdministrativeFeeConfigOut])
def list_admin_fee_configs(request: HttpRequest) -> list[AdministrativeFeeConfigOut]:
    """List all administrative fee configurations."""
    if not has_permission(request.user, "finance.view_administrativefeeconfig"):
        raise HttpError(403, "You don't have permission to view administrative fee configurations")

    configs = AdministrativeFeeConfig.objects.all().order_by("cycle_type")

    results: list[AdministrativeFeeConfigOut] = []
    for config in configs:
        cfg = cast("Any", config)
        results.append(
            AdministrativeFeeConfigOut(
                id=cfg.id,
                cycle_type=cfg.cycle_type,
                cycle_type_display=cfg.get_cycle_type_display(),
                fee_amount=float(cfg.fee_amount),
                included_document_units=cfg.included_document_units,
                notes=cfg.notes,
                is_active=cfg.is_active,
                effective_date=cfg.effective_date.isoformat(),
                end_date=(cfg.end_date.isoformat() if cfg.end_date else None),
                created_at=cfg.created_at.isoformat(),
                updated_at=cfg.updated_at.isoformat(),
            ),
        )
    return results


@router.post("/admin-fee-configs", response=AdministrativeFeeConfigOut)
def create_admin_fee_config(request: HttpRequest, data: AdministrativeFeeConfigIn) -> AdministrativeFeeConfigOut:
    """Create a new administrative fee configuration."""
    if not has_permission(request.user, "finance.add_administrativefeeconfig"):
        raise HttpError(403, "You don't have permission to create administrative fee configurations")

    # Check if configuration already exists for this cycle type
    if AdministrativeFeeConfig.objects.filter(cycle_type=data.cycle_type).exists():
        raise HttpError(400, f"Configuration already exists for cycle type {data.cycle_type}")

    from datetime import date

    effective_date = (
        date.fromisoformat(data.effective_date) if isinstance(data.effective_date, str) else data.effective_date
    )
    end_date = date.fromisoformat(data.end_date) if data.end_date and isinstance(data.end_date, str) else data.end_date

    config = AdministrativeFeeConfig.objects.create(
        cycle_type=data.cycle_type,
        fee_amount=Decimal(str(data.fee_amount)),
        included_document_units=data.included_document_units,
        notes=data.notes,
        is_active=data.is_active,
        effective_date=effective_date,
        end_date=end_date,
        created_by=request.user,
    )

    cfg = cast("Any", config)
    return AdministrativeFeeConfigOut(
        id=cfg.id,
        cycle_type=cfg.cycle_type,
        cycle_type_display=cfg.get_cycle_type_display(),
        fee_amount=float(cfg.fee_amount),
        included_document_units=cfg.included_document_units,
        notes=cfg.notes,
        is_active=cfg.is_active,
        effective_date=cfg.effective_date.isoformat(),
        end_date=cfg.end_date.isoformat() if cfg.end_date else None,
        created_at=cfg.created_at.isoformat(),
        updated_at=cfg.updated_at.isoformat(),
    )


@router.put("/admin-fee-configs/{config_id}", response=AdministrativeFeeConfigOut)
def update_admin_fee_config(
    request: HttpRequest, config_id: int, data: AdministrativeFeeConfigIn
) -> AdministrativeFeeConfigOut:
    """Update an administrative fee configuration."""
    if not has_permission(request.user, "finance.change_administrativefeeconfig"):
        raise HttpError(403, "You don't have permission to update administrative fee configurations")

    config = get_object_or_404(AdministrativeFeeConfig, id=config_id)

    from datetime import date

    effective_date = (
        date.fromisoformat(data.effective_date) if isinstance(data.effective_date, str) else data.effective_date
    )
    end_date = date.fromisoformat(data.end_date) if data.end_date and isinstance(data.end_date, str) else data.end_date

    config.cycle_type = data.cycle_type
    config.fee_amount = Decimal(str(data.fee_amount))
    config.included_document_units = data.included_document_units
    config.notes = data.notes
    config.is_active = data.is_active
    config.effective_date = effective_date
    config.end_date = end_date
    config.updated_by = request.user
    config.save()

    cfg = cast("Any", config)
    return AdministrativeFeeConfigOut(
        id=cfg.id,
        cycle_type=cfg.cycle_type,
        cycle_type_display=cfg.get_cycle_type_display(),
        fee_amount=float(cfg.fee_amount),
        included_document_units=cfg.included_document_units,
        notes=cfg.notes,
        is_active=cfg.is_active,
        effective_date=cfg.effective_date.isoformat(),
        end_date=cfg.end_date.isoformat() if cfg.end_date else None,
        created_at=cfg.created_at.isoformat(),
        updated_at=cfg.updated_at.isoformat(),
    )


# Document Excess Fee Configuration Endpoints


@router.get("/document-excess-fees", response=list[DocumentExcessFeeOut])
def list_document_excess_fees(request: HttpRequest) -> list[DocumentExcessFeeOut]:
    """List all document excess fee configurations."""
    if not has_permission(request.user, "finance.view_documentexcessfee"):
        raise HttpError(403, "You don't have permission to view document excess fee configurations")

    fees = (
        DocumentExcessFee.objects.select_related("document_request", "invoice_line_item").all().order_by("-created_at")
    )

    fee_results: list[DocumentExcessFeeOut] = []
    for fee in fees:
        f = cast("Any", fee)
        fee_results.append(
            DocumentExcessFeeOut(
                id=f.id,
                units_charged=f.units_charged,
                unit_price=float(f.unit_price),
                total_amount=float(f.total_amount),
                document_request_id=f.document_request.id,
                invoice_line_item_id=f.invoice_line_item.id,
                created_at=f.created_at.isoformat(),
                updated_at=f.updated_at.isoformat(),
            ),
        )
    return fee_results


@router.post("/document-excess-fees", response=DocumentExcessFeeOut)
def create_document_excess_fee(request: HttpRequest, data: DocumentExcessFeeIn) -> DocumentExcessFeeOut:
    """Create a new document excess fee."""
    if not has_permission(request.user, "finance.add_documentexcessfee"):
        raise HttpError(403, "You don't have permission to create document excess fees")

    # Get related objects
    from apps.academic_records.models import DocumentRequest
    from apps.finance.models import InvoiceLineItem

    document_request = get_object_or_404(DocumentRequest, id=data.document_request_id)
    invoice_line_item = get_object_or_404(InvoiceLineItem, id=data.invoice_line_item_id)

    fee = DocumentExcessFee.objects.create(
        document_request=document_request,
        invoice_line_item=invoice_line_item,
        units_charged=data.units_charged,
        unit_price=Decimal(str(data.unit_price)),
        created_by=request.user,
    )

    f = cast("Any", fee)
    return DocumentExcessFeeOut(
        id=f.id,
        units_charged=f.units_charged,
        unit_price=float(f.unit_price),
        total_amount=float(f.total_amount),
        document_request_id=f.document_request.id,
        invoice_line_item_id=f.invoice_line_item.id,
        created_at=f.created_at.isoformat(),
        updated_at=f.updated_at.isoformat(),
    )


@router.put("/document-excess-fees/{fee_id}", response=DocumentExcessFeeOut)
def update_document_excess_fee(request: HttpRequest, fee_id: int, data: DocumentExcessFeeIn) -> DocumentExcessFeeOut:
    """Update a document excess fee."""
    if not has_permission(request.user, "finance.change_documentexcessfee"):
        raise HttpError(403, "You don't have permission to update document excess fees")

    fee = get_object_or_404(DocumentExcessFee, id=fee_id)

    # Get related objects if changed
    from apps.academic_records.models import DocumentRequest
    from apps.finance.models import InvoiceLineItem

    if data.document_request_id != fee.document_request.id:
        fee.document_request = get_object_or_404(DocumentRequest, id=data.document_request_id)

    if data.invoice_line_item_id != fee.invoice_line_item.id:
        fee.invoice_line_item = get_object_or_404(InvoiceLineItem, id=data.invoice_line_item_id)

    fee.units_charged = data.units_charged
    fee.unit_price = Decimal(str(data.unit_price))
    fee.updated_by = request.user
    fee.save()

    f = cast("Any", fee)
    return DocumentExcessFeeOut(
        id=f.id,
        units_charged=f.units_charged,
        unit_price=float(f.unit_price),
        total_amount=float(f.total_amount),
        document_request_id=f.document_request.id,
        invoice_line_item_id=f.invoice_line_item.id,
        created_at=f.created_at.isoformat(),
        updated_at=f.updated_at.isoformat(),
    )


# Processing Endpoints


@router.post("/process-term-fees/{term_id}", response=ProcessingResultOut)
@transaction.atomic
def process_term_administrative_fees(request: HttpRequest, term_id: int) -> ProcessingResultOut:
    """Process administrative fees for all eligible students in a term."""
    if not has_permission(request.user, "finance.add_invoice"):
        raise HttpError(403, "You don't have permission to process administrative fees")

    term = get_object_or_404(Term, id=term_id)

    # Process fees
    results = AdministrativeFeeService.process_term_administrative_fees(term)

    return ProcessingResultOut(
        processed=results["processed"],
        fees_applied=results["fees_applied"],
        total_revenue=float(results["total_revenue"]),
        errors=results["errors"],
    )


# Student Cycle Status Endpoints


@router.get("/student-cycle-statuses", response=list[StudentCycleStatusOut])
def list_student_cycle_statuses(request: HttpRequest, is_active: bool | None = None) -> list[StudentCycleStatusOut]:
    """List student cycle statuses with optional filtering."""
    if not has_permission(request.user, "enrollment.view_studentcyclestatus"):
        raise HttpError(403, "You don't have permission to view student cycle statuses")

    statuses = StudentCycleStatus.objects.select_related("student__person", "source_program", "target_program")

    if is_active is not None:
        statuses = statuses.filter(is_active=is_active)

    statuses = statuses.order_by("-detected_date")

    out: list[StudentCycleStatusOut] = []
    for status in statuses:
        st = cast("Any", status)
        out.append(
            StudentCycleStatusOut(
                id=st.id,
                student_id=st.student.id,
                student_name=st.student.person.full_name,
                student_number=st.student.student_id,
                cycle_type=st.cycle_type,
                cycle_type_display=st.get_cycle_type_display(),
                source_program=(st.source_program.name if st.source_program else None),
                target_program=st.target_program.name,
                detected_date=st.detected_date.isoformat(),
                is_active=st.is_active,
                deactivated_date=(st.deactivated_date.isoformat() if st.deactivated_date else None),
                deactivation_reason=st.deactivation_reason,
            ),
        )
    return out


@router.post("/detect-cycle-changes/{term_id}")
def detect_and_record_cycle_changes(request: HttpRequest, term_id: int) -> dict[str, Any]:
    """Detect and record cycle changes for all students in a term."""
    if not has_permission(request.user, "enrollment.add_studentcyclestatus"):
        raise HttpError(403, "You don't have permission to detect cycle changes")

    term = get_object_or_404(Term, id=term_id)

    # Get all enrollments for the term
    from typing import cast

    from apps.enrollment import services as enrollment_services
    from apps.enrollment.models import ClassHeaderEnrollment

    enrollments = (
        ClassHeaderEnrollment.objects.filter(class_header__term=term, status__in=["ENROLLED", "COMPLETED"])
        .select_related("student", "class_header__course")
        .distinct("student")
    )

    detected = 0
    for enrollment in enrollments:
        cycle_status = cast("Any", enrollment_services).CycleDetectionService.detect_cycle_change(
            enrollment.student, enrollment.class_header.course
        )
        if cycle_status:
            detected += 1

    return {"detected": detected, "message": f"Detected {detected} cycle changes"}
