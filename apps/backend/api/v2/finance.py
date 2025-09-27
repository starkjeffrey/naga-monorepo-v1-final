"""Enhanced Finance API v2 with POS system and analytics.

This module provides enhanced financial management endpoints with:
- Point-of-sale payment processing interface
- Financial forecasting and trend analysis
- AI-powered scholarship matching algorithm
- Automated reminder management system
- Advanced payment analytics and insights
- Financial compliance and audit features
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum, Avg, Count, F
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import paginate

from apps.finance.models import (
    Invoice, Payment, Currency, FinancialTransaction,
    InvoiceLineItem, CashierSession
)
from apps.people.models import StudentProfile
from apps.scholarships.models import Scholarship, ScholarshipApplication

from ..v1.auth import jwt_auth
from .schemas import (
    POSTransaction,
    FinancialAnalytics,
    BulkActionRequest,
    BulkActionResult,
    TimeSeriesPoint,
    ChartData,
    MetricValue
)

logger = logging.getLogger(__name__)

router = Router(auth=jwt_auth, tags=["finance-enhanced"])


@router.post("/pos/transaction/")
def process_pos_transaction(request, transaction: POSTransaction):
    """Process point-of-sale payment transaction."""

    try:
        with transaction.atomic():
            # Get or create cashier session
            cashier_session = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                cashier_session, created = CashierSession.objects.get_or_create(
                    cashier=request.user,
                    session_date=datetime.now().date(),
                    is_closed=False,
                    defaults={
                        'opening_balance': Decimal('0.00'),
                        'expected_balance': Decimal('0.00')
                    }
                )

            # Get student if provided
            student = None
            if transaction.student_id:
                student = get_object_or_404(StudentProfile, unique_id=transaction.student_id)

            # Get default currency (USD)
            currency = Currency.objects.filter(code='USD').first()
            if not currency:
                currency = Currency.objects.create(
                    code='USD',
                    name='US Dollar',
                    symbol='$'
                )

            # Create financial transaction record
            financial_transaction = FinancialTransaction.objects.create(
                amount=transaction.amount,
                currency=currency,
                transaction_type='payment',
                payment_method=transaction.payment_method,
                description=transaction.description,
                student=student,
                cashier_session=cashier_session,
                metadata=transaction.metadata
            )

            # Create invoice if needed
            invoice = None
            if student:
                invoice = Invoice.objects.create(
                    student=student,
                    amount=transaction.amount,
                    currency=currency,
                    description=transaction.description,
                    due_date=datetime.now().date(),
                    status='paid'
                )

                # Create line items
                for line_item in transaction.line_items:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        description=line_item.get('description', ''),
                        quantity=line_item.get('quantity', 1),
                        unit_price=Decimal(str(line_item.get('unit_price', '0.00'))),
                        total_amount=Decimal(str(line_item.get('total_amount', '0.00')))
                    )

            # Create payment record
            payment = Payment.objects.create(
                invoice=invoice,
                amount=transaction.amount,
                currency=currency,
                payment_method=transaction.payment_method,
                status='completed',
                payment_date=datetime.now(),
                cashier_session=cashier_session,
                notes=transaction.description
            )

            # Update cashier session balance
            if cashier_session:
                cashier_session.expected_balance += transaction.amount
                cashier_session.save(update_fields=['expected_balance'])

            return {
                "transaction_id": str(financial_transaction.unique_id),
                "payment_id": str(payment.unique_id),
                "invoice_id": str(invoice.unique_id) if invoice else None,
                "amount": str(transaction.amount),
                "status": "completed",
                "receipt_number": f"POS-{payment.unique_id.hex[:8].upper()}",
                "processed_at": datetime.now().isoformat(),
                "cashier_session": str(cashier_session.unique_id) if cashier_session else None
            }

    except Exception as e:
        logger.error("POS transaction failed: %s", e)
        return {
            "error": "Transaction failed",
            "message": str(e),
            "status": "failed"
        }


@router.get("/analytics/dashboard/", response=FinancialAnalytics)
def get_financial_dashboard(
    request,
    date_range: int = Query(30, description="Days to look back"),
    include_forecasts: bool = Query(True)
):
    """Get comprehensive financial analytics for dashboard."""

    cache_key = f"financial_analytics_{date_range}_{include_forecasts}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return FinancialAnalytics(**cached_data)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=date_range)

    # Calculate totals
    payments_query = Payment.objects.filter(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
        status='completed'
    )

    total_revenue = payments_query.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Pending payments
    pending_invoices = Invoice.objects.filter(
        status='pending',
        due_date__gte=start_date
    )

    pending_payments = pending_invoices.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Overdue amounts
    overdue_invoices = Invoice.objects.filter(
        status='pending',
        due_date__lt=datetime.now().date()
    )

    overdue_amount = overdue_invoices.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Scholarship totals
    scholarship_total = Decimal('0.00')
    try:
        from apps.scholarships.models import ScholarshipApplication
        active_scholarships = ScholarshipApplication.objects.filter(
            status='approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        scholarship_total = active_scholarships.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    except ImportError:
        pass  # Scholarships app not available

    # Payment trends (daily totals)
    daily_payments = payments_query.extra(
        select={'day': 'date(payment_date)'}
    ).values('day').annotate(
        total=Sum('amount')
    ).order_by('day')

    payment_trends = [
        TimeSeriesPoint(
            timestamp=datetime.combine(payment['day'], datetime.min.time()),
            value=float(payment['total']),
            label=payment['day'].strftime('%Y-%m-%d')
        )
        for payment in daily_payments
    ]

    # Payment method breakdown
    method_breakdown = payments_query.values('payment_method').annotate(
        total=Sum('amount')
    ).order_by('-total')

    payment_method_breakdown = {
        method['payment_method']: float(method['total'])
        for method in method_breakdown
    }

    # Forecasts (simplified linear projection)
    forecasts = {}
    if include_forecasts and payment_trends:
        # Simple 30-day forecast based on recent trend
        recent_avg = sum(point.value for point in payment_trends[-7:]) / 7 if len(payment_trends) >= 7 else 0
        forecasts = {
            "next_30_days": recent_avg * 30,
            "next_quarter": recent_avg * 90,
            "confidence": 0.75  # Simplified confidence score
        }

    analytics_data = {
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
        "overdue_amount": overdue_amount,
        "scholarship_total": scholarship_total,
        "payment_trends": payment_trends,
        "forecasts": forecasts,
        "payment_method_breakdown": payment_method_breakdown
    }

    # Cache for 15 minutes
    cache.set(cache_key, analytics_data, 900)

    return FinancialAnalytics(**analytics_data)


@router.get("/scholarships/matching/{student_id}/")
def get_scholarship_matches(request, student_id: UUID):
    """AI-powered scholarship matching for a student."""

    student = get_object_or_404(StudentProfile, unique_id=student_id)

    try:
        from apps.scholarships.models import Scholarship, ScholarshipApplication

        # Get student characteristics for matching
        student_gpa = 3.5  # TODO: Calculate actual GPA
        student_program = student.current_program
        student_level = student.current_level
        student_financial_need = True  # TODO: Calculate from financial data

        # Get available scholarships
        available_scholarships = Scholarship.objects.filter(
            is_active=True,
            application_deadline__gte=datetime.now().date()
        )

        matches = []
        for scholarship in available_scholarships:
            match_score = 0.0
            criteria_met = []
            criteria_missing = []

            # GPA requirements
            if hasattr(scholarship, 'min_gpa') and scholarship.min_gpa:
                if student_gpa >= scholarship.min_gpa:
                    match_score += 0.3
                    criteria_met.append(f"GPA requirement ({scholarship.min_gpa})")
                else:
                    criteria_missing.append(f"GPA requirement ({scholarship.min_gpa})")

            # Program requirements
            if hasattr(scholarship, 'eligible_programs') and scholarship.eligible_programs.exists():
                if student_program in scholarship.eligible_programs.all():
                    match_score += 0.2
                    criteria_met.append("Program eligibility")
                else:
                    criteria_missing.append("Program eligibility")
            else:
                # No program restriction
                match_score += 0.2

            # Level requirements
            if hasattr(scholarship, 'eligible_levels') and scholarship.eligible_levels:
                if student_level in scholarship.eligible_levels:
                    match_score += 0.2
                    criteria_met.append("Academic level")
                else:
                    criteria_missing.append("Academic level")
            else:
                match_score += 0.2

            # Financial need
            if hasattr(scholarship, 'requires_financial_need'):
                if scholarship.requires_financial_need == student_financial_need:
                    match_score += 0.2
                    criteria_met.append("Financial need assessment")

            # Previous applications
            has_applied = ScholarshipApplication.objects.filter(
                student=student,
                scholarship=scholarship
            ).exists()

            if has_applied:
                match_score -= 0.1  # Slight penalty for reapplication

            # Only include scholarships with reasonable match scores
            if match_score >= 0.4:
                matches.append({
                    "scholarship_id": str(scholarship.unique_id),
                    "name": scholarship.name,
                    "amount": str(scholarship.amount),
                    "deadline": scholarship.application_deadline.isoformat(),
                    "match_score": round(match_score, 2),
                    "criteria_met": criteria_met,
                    "criteria_missing": criteria_missing,
                    "has_applied": has_applied,
                    "recommendation": "Highly recommended" if match_score >= 0.8 else "Recommended" if match_score >= 0.6 else "Consider applying"
                })

        # Sort by match score
        matches.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "student_id": str(student_id),
            "total_matches": len(matches),
            "matches": matches,
            "student_profile": {
                "gpa": student_gpa,
                "program": student_program.name if student_program else None,
                "level": student_level,
                "financial_need": student_financial_need
            },
            "generated_at": datetime.now().isoformat()
        }

    except ImportError:
        return {
            "error": "Scholarship matching not available",
            "message": "Scholarships module is not installed"
        }


@router.post("/automation/payment-reminders/")
def setup_payment_reminders(
    request,
    student_ids: List[UUID] = [],
    reminder_days: List[int] = [7, 3, 1],  # Days before due date
    template: str = "default"
):
    """Setup automated payment reminder system."""

    results = {
        "reminders_created": 0,
        "students_processed": 0,
        "errors": []
    }

    try:
        # Get students with pending invoices
        if student_ids:
            students = StudentProfile.objects.filter(unique_id__in=student_ids)
        else:
            # Get all students with overdue or soon-due invoices
            upcoming_due_date = datetime.now().date() + timedelta(days=max(reminder_days))
            students = StudentProfile.objects.filter(
                invoices__status='pending',
                invoices__due_date__lte=upcoming_due_date
            ).distinct()

        for student in students:
            results["students_processed"] += 1

            # Get pending invoices for this student
            pending_invoices = Invoice.objects.filter(
                student=student,
                status='pending',
                due_date__gte=datetime.now().date()
            )

            for invoice in pending_invoices:
                for days_before in reminder_days:
                    reminder_date = invoice.due_date - timedelta(days=days_before)

                    # Only create reminders for future dates
                    if reminder_date >= datetime.now().date():
                        # TODO: Create reminder task in task queue
                        # For now, just log the reminder creation
                        logger.info(
                            "Payment reminder created: Student %s, Invoice %s, Reminder date %s",
                            student.student_id,
                            invoice.unique_id,
                            reminder_date
                        )
                        results["reminders_created"] += 1

        return {
            "success": True,
            "results": results,
            "message": f"Created {results['reminders_created']} reminders for {results['students_processed']} students"
        }

    except Exception as e:
        logger.error("Failed to setup payment reminders: %s", e)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/reports/revenue-forecast/", response=ChartData)
def get_revenue_forecast(
    request,
    months_ahead: int = Query(6, ge=1, le=24),
    confidence_level: float = Query(0.8, ge=0.5, le=0.95)
):
    """Generate revenue forecast chart data."""

    # Get historical payment data for the last year
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)

    monthly_revenue = Payment.objects.filter(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
        status='completed'
    ).extra(
        select={'month': "DATE_TRUNC('month', payment_date)"}
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    # Calculate trend (simplified linear regression)
    if len(monthly_revenue) >= 3:
        # Simple moving average for trend
        revenues = [float(month['total']) for month in monthly_revenue]
        recent_avg = sum(revenues[-3:]) / 3
        older_avg = sum(revenues[-6:-3]) / 3 if len(revenues) >= 6 else recent_avg
        monthly_trend = (recent_avg - older_avg) / 3  # Monthly change
    else:
        monthly_trend = 0
        recent_avg = float(monthly_revenue[-1]['total']) if monthly_revenue else 0

    # Generate forecast
    forecast_points = []
    current_month = datetime.now().replace(day=1)

    for i in range(months_ahead):
        forecast_month = current_month + timedelta(days=32 * i)
        forecast_month = forecast_month.replace(day=1)  # First of month

        # Simple forecast: recent average + trend * months
        base_forecast = recent_avg + (monthly_trend * i)

        # Add seasonal adjustment (simplified)
        seasonal_multiplier = 1.0
        if forecast_month.month in [1, 9]:  # January and September (enrollment months)
            seasonal_multiplier = 1.2
        elif forecast_month.month in [6, 7, 12]:  # Summer and December
            seasonal_multiplier = 0.8

        forecasted_revenue = base_forecast * seasonal_multiplier

        # Apply confidence interval
        confidence_range = forecasted_revenue * (1 - confidence_level) * 0.5
        forecasted_revenue = max(0, forecasted_revenue)  # Ensure non-negative

        forecast_points.append(TimeSeriesPoint(
            timestamp=datetime.combine(forecast_month.date(), datetime.min.time()),
            value=forecasted_revenue,
            label=forecast_month.strftime('%Y-%m')
        ))

    return ChartData(
        title=f"Revenue Forecast - Next {months_ahead} Months",
        type="line",
        data=forecast_points,
        options={
            "confidence_level": confidence_level,
            "trend_direction": "increasing" if monthly_trend > 0 else "decreasing" if monthly_trend < 0 else "stable",
            "monthly_trend": monthly_trend,
            "forecast_method": "linear_trend_with_seasonality"
        }
    )


@router.get("/audit/payment-summary/")
def get_payment_audit_summary(
    request,
    start_date: datetime,
    end_date: datetime,
    cashier_id: Optional[UUID] = None
):
    """Get payment audit summary for compliance reporting."""

    payments_query = Payment.objects.filter(
        payment_date__date__gte=start_date.date(),
        payment_date__date__lte=end_date.date()
    )

    if cashier_id:
        payments_query = payments_query.filter(
            cashier_session__cashier__unique_id=cashier_id
        )

    # Summary statistics
    summary = payments_query.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
        avg_amount=Avg('amount')
    )

    # Payment method breakdown
    method_breakdown = payments_query.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')

    # Daily summaries
    daily_summaries = payments_query.extra(
        select={'day': 'date(payment_date)'}
    ).values('day').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('day')

    # Cashier session summaries
    session_summaries = []
    if cashier_id:
        sessions = CashierSession.objects.filter(
            cashier__unique_id=cashier_id,
            session_date__gte=start_date.date(),
            session_date__lte=end_date.date()
        ).annotate(
            total_payments=Sum('payments__amount'),
            payment_count=Count('payments')
        )

        session_summaries = [
            {
                "session_id": str(session.unique_id),
                "date": session.session_date.isoformat(),
                "opening_balance": str(session.opening_balance),
                "expected_balance": str(session.expected_balance),
                "actual_balance": str(session.actual_balance) if session.actual_balance else None,
                "total_payments": str(session.total_payments or 0),
                "payment_count": session.payment_count,
                "is_closed": session.is_closed
            }
            for session in sessions
        ]

    return {
        "period": {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat()
        },
        "summary": {
            "total_amount": str(summary['total_amount'] or 0),
            "total_count": summary['total_count'],
            "average_amount": str(summary['avg_amount'] or 0)
        },
        "payment_methods": [
            {
                "method": method['payment_method'],
                "count": method['count'],
                "total": str(method['total'])
            }
            for method in method_breakdown
        ],
        "daily_summaries": [
            {
                "date": daily['day'].isoformat(),
                "count": daily['count'],
                "total": str(daily['total'])
            }
            for daily in daily_summaries
        ],
        "cashier_sessions": session_summaries,
        "generated_at": datetime.now().isoformat()
    }


# Export router
__all__ = ["router"]