# Finance App API Endpoints Guide

## Overview

The Finance app provides a comprehensive REST API using django-ninja for managing financial operations including billing, payments, pricing, and reconciliation. All endpoints follow RESTful conventions and return JSON responses.

## Table of Contents

1. [Authentication](#authentication)
2. [Student Financial API](#student-financial-api)
3. [Billing API](#billing-api)
4. [Payment API](#payment-api)
5. [Pricing API](#pricing-api)
6. [Reports API](#reports-api)
7. [Error Handling](#error-handling)
8. [API Examples](#api-examples)

## Authentication

All finance API endpoints require authentication using JWT tokens:

```http
Authorization: Bearer <jwt_token>
```

Required permissions vary by endpoint - see individual endpoint documentation.

## Student Financial API

### Get Student Financial Summary

**Endpoint:** `GET /api/finance/students/{student_id}/summary/`

**Description:** Retrieve comprehensive financial summary for a student

**Permissions:** `view_student_finances` or student viewing own data

**Response:**
```json
{
    "student": {
        "id": 123,
        "student_id": "ST12345",
        "name": "John Doe",
        "program": "Bachelor of Business Administration",
        "nationality": "Cambodian"
    },
    "financial_summary": {
        "current_balance": "750.00",
        "total_charges": "1250.00",
        "total_payments": "500.00",
        "total_scholarships": "0.00",
        "overdue_amount": "250.00",
        "next_payment_due": "2024-08-15"
    },
    "recent_transactions": [
        {
            "date": "2024-07-15",
            "type": "payment",
            "amount": "500.00",
            "description": "Mobile payment - ABA PayWay",
            "status": "verified",
            "reference": "PW789012345"
        }
    ],
    "outstanding_invoices": [
        {
            "invoice_number": "INV-2024-001234",
            "issue_date": "2024-07-01",
            "due_date": "2024-08-15",
            "total_amount": "1250.00",
            "paid_amount": "500.00",
            "balance": "750.00",
            "status": "partial_payment",
            "is_overdue": false
        }
    ],
    "active_scholarships": [
        {
            "scholarship_name": "Academic Excellence",
            "percentage": 50,
            "amount_per_term": "625.00",
            "status": "active"
        }
    ]
}
```

### Get Student Transaction History

**Endpoint:** `GET /api/finance/students/{student_id}/transactions/`

**Query Parameters:**
- `start_date` (optional): Filter transactions from this date
- `end_date` (optional): Filter transactions to this date
- `type` (optional): Filter by transaction type (invoice, payment, adjustment)
- `page` (optional): Page number for pagination
- `page_size` (optional): Items per page (default: 20)

**Response:**
```json
{
    "transactions": [
        {
            "id": 456,
            "date": "2024-07-15",
            "type": "payment",
            "description": "Payment for INV-2024-001234",
            "debit": "0.00",
            "credit": "500.00",
            "balance": "750.00",
            "reference_type": "payment",
            "reference_id": 789
        }
    ],
    "pagination": {
        "total": 45,
        "page": 1,
        "page_size": 20,
        "total_pages": 3
    }
}
```

## Billing API

### Generate Term Invoice

**Endpoint:** `POST /api/finance/invoices/generate-term-invoice/`

**Request Body:**
```json
{
    "student_id": 123,
    "term_code": "2024-1",
    "include_courses": true,
    "include_fees": true,
    "apply_scholarships": true,
    "apply_discounts": true
}
```

**Response:**
```json
{
    "invoice": {
        "id": 1001,
        "invoice_number": "INV-2024-001235",
        "student_id": 123,
        "term": "2024-1",
        "issue_date": "2024-07-20",
        "due_date": "2024-08-20",
        "total_amount": "1250.00",
        "status": "issued"
    },
    "line_items": [
        {
            "description": "Tuition - ACCT-101 (3 credits)",
            "quantity": 3,
            "unit_price": "75.00",
            "total_amount": "225.00",
            "gl_account": "4100-01"
        },
        {
            "description": "Registration Fee - Fall 2024",
            "quantity": 1,
            "unit_price": "100.00",
            "total_amount": "100.00",
            "gl_account": "4200-01"
        }
    ],
    "applied_discounts": [
        {
            "type": "early_bird",
            "percentage": 10,
            "amount": "125.00",
            "description": "Early Bird Discount - 10%"
        }
    ]
}
```

### Get Invoice Details

**Endpoint:** `GET /api/finance/invoices/{invoice_id}/`

**Response:** Similar to generate invoice response with full details

### Update Invoice

**Endpoint:** `PATCH /api/finance/invoices/{invoice_id}/`

**Request Body:**
```json
{
    "due_date": "2024-08-30",
    "notes": "Extended due date per student request"
}
```

## Payment API

### Submit Payment

**Endpoint:** `POST /api/finance/payments/`

**Request Body:**
```json
{
    "student_id": 123,
    "amount": "500.00",
    "payment_method": "bank_transfer",
    "payment_date": "2024-07-15",
    "payment_details": {
        "bank_name": "ABA Bank",
        "reference_number": "BT789012345",
        "account_last_four": "1234"
    },
    "apply_to_invoices": [
        {
            "invoice_id": 1001,
            "amount": "500.00"
        }
    ],
    "notes": "Partial payment for Fall 2024"
}
```

**Response:**
```json
{
    "payment": {
        "id": 456,
        "payment_number": "PAY-2024-000456",
        "student_id": 123,
        "amount": "500.00",
        "payment_method": "bank_transfer",
        "payment_date": "2024-07-15",
        "status": "pending_verification",
        "receipt_number": "RCP-2024-000789"
    },
    "applications": [
        {
            "invoice_id": 1001,
            "invoice_number": "INV-2024-001234",
            "amount_applied": "500.00",
            "remaining_balance": "750.00"
        }
    ],
    "verification_required": true,
    "estimated_processing_time": "1-2 business days"
}
```

### Verify Payment

**Endpoint:** `POST /api/finance/payments/{payment_id}/verify/`

**Permissions:** `verify_payments`

**Request Body:**
```json
{
    "verified": true,
    "verification_notes": "Confirmed with bank statement"
}
```

### Get Payment Receipt

**Endpoint:** `GET /api/finance/payments/{payment_id}/receipt/`

**Query Parameters:**
- `format` (optional): pdf or html (default: pdf)

**Response:** Binary PDF file or HTML content

## Pricing API

### Calculate Course Price

**Endpoint:** `POST /api/finance/pricing/calculate-course-price/`

**Request Body:**
```json
{
    "course_code": "ACCT-101",
    "student_id": 123,
    "term_code": "2024-1"
}
```

**Response:**
```json
{
    "course": {
        "code": "ACCT-101",
        "title": "Introduction to Accounting",
        "credits": 3
    },
    "pricing": {
        "base_price": "225.00",
        "pricing_method": "DEFAULT_LOCAL_PRICING",
        "student_type": "local",
        "price_per_credit": "75.00"
    },
    "applicable_discounts": [
        {
            "type": "early_bird",
            "percentage": 10,
            "amount": "22.50",
            "eligibility": "eligible"
        }
    ],
    "final_price": "202.50"
}
```

### Get Fee Pricing

**Endpoint:** `GET /api/finance/pricing/fees/`

**Query Parameters:**
- `fee_type` (optional): Filter by fee type
- `student_type` (optional): local or foreign

**Response:**
```json
{
    "fees": [
        {
            "fee_code": "REGISTRATION",
            "fee_name": "Registration Fee",
            "fee_type": "REGISTRATION",
            "base_amount": "100.00",
            "local_amount": "100.00",
            "foreign_amount": "150.00"
        }
    ]
}
```

## Reports API

### Accounts Receivable Aging Report

**Endpoint:** `GET /api/finance/reports/ar-aging/`

**Query Parameters:**
- `as_of_date` (required): Date for aging calculation
- `student_type` (optional): Filter by student type
- `program` (optional): Filter by program

**Response:**
```json
{
    "report_date": "2024-07-15",
    "total_outstanding": "125000.00",
    "aging_summary": {
        "current": {
            "amount": "75000.00",
            "percentage": 60.0,
            "count": 150
        },
        "30_days": {
            "amount": "30000.00",
            "percentage": 24.0,
            "count": 60
        },
        "60_days": {
            "amount": "15000.00",
            "percentage": 12.0,
            "count": 25
        },
        "90_plus_days": {
            "amount": "5000.00",
            "percentage": 4.0,
            "count": 10
        }
    },
    "student_details": [
        {
            "student_id": "ST12345",
            "student_name": "John Doe",
            "program": "BBA",
            "current": "750.00",
            "30_days": "0.00",
            "60_days": "0.00",
            "90_plus": "0.00",
            "total": "750.00",
            "last_payment_date": "2024-07-15"
        }
    ]
}
```

### Revenue Report

**Endpoint:** `GET /api/finance/reports/revenue/`

**Query Parameters:**
- `start_date` (required): Report start date
- `end_date` (required): Report end date
- `group_by` (optional): term, program, or course

**Response:**
```json
{
    "report_period": {
        "start_date": "2024-01-01",
        "end_date": "2024-07-31"
    },
    "summary": {
        "total_revenue": "450000.00",
        "tuition_revenue": "400000.00",
        "fee_revenue": "50000.00",
        "discount_amount": "45000.00",
        "net_revenue": "405000.00"
    },
    "breakdown": [
        {
            "term": "2024-1",
            "tuition": "400000.00",
            "fees": "50000.00",
            "discounts": "45000.00",
            "net": "405000.00",
            "student_count": 250
        }
    ]
}
```

### Collection Report

**Endpoint:** `GET /api/finance/reports/collections/`

**Query Parameters:**
- `start_date` (required): Collection period start
- `end_date` (required): Collection period end
- `payment_method` (optional): Filter by payment method

**Response:**
```json
{
    "period": {
        "start_date": "2024-07-01",
        "end_date": "2024-07-31"
    },
    "summary": {
        "total_collected": "125000.00",
        "payment_count": 250,
        "average_payment": "500.00"
    },
    "by_method": {
        "cash": {
            "amount": "25000.00",
            "count": 50,
            "percentage": 20.0
        },
        "bank_transfer": {
            "amount": "75000.00",
            "count": 150,
            "percentage": 60.0
        },
        "mobile_payment": {
            "amount": "25000.00",
            "count": 50,
            "percentage": 20.0
        }
    },
    "daily_collections": [
        {
            "date": "2024-07-01",
            "amount": "5000.00",
            "count": 10
        }
    ]
}
```

## Error Handling

All API endpoints follow consistent error response format:

### Validation Error (400)
```json
{
    "error": "validation_error",
    "message": "Invalid request data",
    "details": {
        "amount": ["Amount must be greater than 0"],
        "payment_method": ["Invalid payment method"]
    }
}
```

### Not Found (404)
```json
{
    "error": "not_found",
    "message": "Invoice not found",
    "details": {
        "invoice_id": 9999
    }
}
```

### Permission Denied (403)
```json
{
    "error": "permission_denied",
    "message": "You do not have permission to perform this action",
    "details": {
        "required_permission": "verify_payments"
    }
}
```

### Server Error (500)
```json
{
    "error": "internal_server_error",
    "message": "An unexpected error occurred",
    "details": {
        "request_id": "req_123456"
    }
}
```

## API Examples

### Complete Payment Flow

```python
import httpx
from datetime import date, timedelta

# Initialize client with auth
headers = {"Authorization": "Bearer <jwt_token>"}
client = httpx.Client(base_url="https://api.naga.edu", headers=headers)

# 1. Generate invoice for student
invoice_response = client.post("/api/finance/invoices/generate-term-invoice/", json={
    "student_id": 123,
    "term_code": "2024-1",
    "include_courses": True,
    "include_fees": True,
    "apply_scholarships": True
})
invoice = invoice_response.json()

# 2. Submit payment
payment_response = client.post("/api/finance/payments/", json={
    "student_id": 123,
    "amount": str(invoice["invoice"]["total_amount"]),
    "payment_method": "bank_transfer",
    "payment_date": str(date.today()),
    "payment_details": {
        "bank_name": "ABA Bank",
        "reference_number": "BT123456789"
    },
    "apply_to_invoices": [{
        "invoice_id": invoice["invoice"]["id"],
        "amount": str(invoice["invoice"]["total_amount"])
    }]
})
payment = payment_response.json()

# 3. Get receipt
receipt_response = client.get(
    f"/api/finance/payments/{payment['payment']['id']}/receipt/",
    params={"format": "pdf"}
)
with open("receipt.pdf", "wb") as f:
    f.write(receipt_response.content)
```

### Batch Price Calculation

```python
# Calculate prices for multiple courses
courses = ["ACCT-101", "ECON-201", "MGMT-301"]
total_price = 0

for course_code in courses:
    response = client.post("/api/finance/pricing/calculate-course-price/", json={
        "course_code": course_code,
        "student_id": 123,
        "term_code": "2024-1"
    })
    
    price_data = response.json()
    total_price += float(price_data["final_price"])
    print(f"{course_code}: ${price_data['final_price']} ({price_data['pricing']['pricing_method']})")

print(f"Total: ${total_price}")
```

### Financial Report Generation

```python
# Generate AR aging report
report_response = client.get("/api/finance/reports/ar-aging/", params={
    "as_of_date": str(date.today()),
    "student_type": "all"
})

report = report_response.json()
print(f"Total Outstanding: ${report['total_outstanding']}")
print("\nAging Breakdown:")
for bucket, data in report["aging_summary"].items():
    print(f"{bucket}: ${data['amount']} ({data['percentage']}%)")

# Export detailed student list
students_over_90 = [
    s for s in report["student_details"] 
    if float(s["90_plus"]) > 0
]
print(f"\nStudents over 90 days: {len(students_over_90)}")
```

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Standard endpoints**: 100 requests per minute
- **Report endpoints**: 10 requests per minute
- **Bulk operations**: 5 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1627890123
```

## Webhooks

Finance events can trigger webhooks for external integration:

### Available Events
- `invoice.created`
- `invoice.paid`
- `payment.received`
- `payment.verified`
- `payment.failed`

### Webhook Payload Example
```json
{
    "event": "payment.verified",
    "timestamp": "2024-07-15T10:30:00Z",
    "data": {
        "payment_id": 456,
        "student_id": 123,
        "amount": "500.00",
        "status": "verified"
    }
}
```