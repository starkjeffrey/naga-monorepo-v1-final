# Academic Records App

## Overview

The `academic_records` app manages official document generation, transcript services, and secure academic record management for the Naga SIS. This service layer app provides comprehensive document lifecycle management, from request initiation through secure delivery, ensuring institutional compliance and student privacy.

## Features

### Document Generation & Management

- **Official transcript generation** with security features and verification codes
- **Certificate and diploma production** with customizable templates
- **Academic record verification** with digital signatures and authentication
- **Document request workflow** with approval processes and status tracking

### Security & Verification

- **Digital watermarks** and security features for document authenticity
- **Verification codes** for third-party validation of document authenticity
- **Access control** with role-based permissions for sensitive documents
- **Audit trail** for all document access and generation activities

### Request Management

- **Student self-service** portal for document requests
- **Administrative processing** workflow with approval stages
- **Delivery tracking** for physical and digital document distribution
- **Fee integration** for transcript and document services

### Template System

- **Configurable document templates** for various document types
- **Multi-language support** for international document requirements
- **Institutional branding** with customizable layouts and formatting
- **Version control** for template changes and updates

## Models

### Document Management

#### DocumentTypeConfig

Configurable document types with templates and processing rules.

```python
# Configure official transcript template
transcript_config = DocumentTypeConfig.objects.create(
    document_type=DocumentType.OFFICIAL_TRANSCRIPT,
    name="Official Academic Transcript",
    description="Complete academic record with grades and credits",
    template_file="transcripts/official_transcript_template.pdf",
    requires_approval=True,
    fee_amount=Decimal("25.00"),
    processing_days=3,
    security_features={
        "watermark": True,
        "verification_code": True,
        "digital_signature": True
    }
)
```

#### DocumentRequest

Student or administrative requests for official documents.

```python
# Student requests official transcript
document_request = DocumentRequest.objects.create(
    student=student_profile,
    document_type=DocumentType.OFFICIAL_TRANSCRIPT,
    request_type=RequestType.STUDENT_INITIATED,
    delivery_method=DeliveryMethod.EMAIL,
    recipient_email="admissions@university.edu",
    purpose="Graduate school application",
    rush_processing=False,
    requested_by=student_user
)

# Set delivery address for physical delivery
if document_request.delivery_method == DeliveryMethod.MAIL:
    document_request.delivery_address = {
        "name": "University Admissions Office",
        "address": "123 University Ave",
        "city": "Phnom Penh",
        "country": "Cambodia",
        "postal_code": "12345"
    }
    document_request.save()
```

#### GeneratedDocument

Actual generated documents with security features and tracking.

```python
# Generate secure document
generated_doc = GeneratedDocument.objects.create(
    document_request=document_request,
    document_type=DocumentType.OFFICIAL_TRANSCRIPT,
    generation_method=GenerationMethod.AUTOMATED,
    file_path="documents/transcripts/2024/transcript_12345_20240715.pdf",
    verification_code="NAGA-2024-TXR-847291",
    security_features={
        "watermark_applied": True,
        "encryption_level": "AES-256",
        "digital_signature": "sha256:abc123..."
    },
    generated_by=system_user,
    generated_at=timezone.now()
)
```

#### DocumentUsageTracker

Comprehensive tracking of document access and usage.

```python
# Track document access
usage_tracker = DocumentUsageTracker.objects.create(
    generated_document=generated_doc,
    accessed_by=registrar_user,
    access_type=AccessType.DOWNLOAD,
    access_method=AccessMethod.WEB_PORTAL,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    purpose="Third-party verification request"
)
```

## Services

### Document Generation Service

Comprehensive document generation with security and customization.

```python
from apps.academic_records.services import DocumentGenerationService

# Generate official transcript
transcript_data = {
    'student': student_profile,
    'include_grades': True,
    'include_gpa': True,
    'include_honors': True,
    'date_range': {
        'start_term': 'Fall 2020',
        'end_term': 'Spring 2024'
    },
    'security_level': 'OFFICIAL',
    'watermark': True
}

generated_document = DocumentGenerationService.generate_transcript(
    student=student_profile,
    config=transcript_config,
    options=transcript_data
)

# Returns secure PDF with verification features
{
    'document_id': generated_document.id,
    'verification_code': 'NAGA-2024-TXR-847291',
    'file_path': 'documents/transcripts/...',
    'security_features': {
        'watermark': True,
        'digital_signature': True,
        'encryption': 'AES-256'
    }
}
```

### Document Request Service

Request workflow management with approval processes.

```python
from apps.academic_records.services import DocumentRequestService

# Process document request
request_result = DocumentRequestService.process_request(
    request_id=document_request.id,
    processor=registrar_user,
    action=ProcessAction.APPROVE,
    notes="All requirements verified, approved for generation"
)

# Automatic generation for approved requests
if request_result.approved:
    generated_doc = DocumentRequestService.generate_approved_document(
        request=document_request,
        expedite=document_request.rush_processing
    )
```

### Verification Service

Document authenticity verification for third parties.

```python
from apps.academic_records.services import VerificationService

# Verify document authenticity
verification_result = VerificationService.verify_document(
    verification_code="NAGA-2024-TXR-847291",
    document_hash="sha256:abc123...",
    requester_info={
        'organization': 'Graduate University',
        'contact_email': 'verify@graduni.edu',
        'purpose': 'Admissions verification'
    }
)

# Returns verification details
{
    'is_authentic': True,
    'student_name': 'Sophea Chan',  # Limited info for privacy
    'issue_date': '2024-07-15',
    'document_type': 'Official Transcript',
    'issuing_institution': 'Pannasastra University',
    'verification_timestamp': '2024-07-20T10:30:00Z'
}
```

## Views & Templates

### Student Document Portal

Self-service document request interface.

```python
from apps.academic_records.views import StudentDocumentPortalView

class StudentTranscriptRequestView(StudentDocumentPortalView):
    template_name = 'academic_records/student_transcript_request.html'
    document_type = DocumentType.OFFICIAL_TRANSCRIPT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'available_delivery_methods': self.get_delivery_options(),
            'estimated_fees': self.calculate_fees(),
            'processing_timeline': self.get_processing_timeline()
        })
        return context
```

### Administrative Document Management

Staff interface for processing document requests.

```python
class DocumentRequestProcessingView(StaffRequiredMixin, DetailView):
    model = DocumentRequest
    template_name = 'academic_records/process_request.html'

    def post(self, request, *args, **kwargs):
        document_request = self.get_object()
        action = request.POST.get('action')

        if action == 'approve':
            DocumentRequestService.approve_request(
                request=document_request,
                approved_by=request.user,
                notes=request.POST.get('notes')
            )
        elif action == 'reject':
            DocumentRequestService.reject_request(
                request=document_request,
                rejected_by=request.user,
                reason=request.POST.get('reason')
            )

        return redirect('admin:document_requests')
```

## Management Commands

### Document Generation

```bash
# Generate transcripts for graduating students
python manage.py generate_graduation_transcripts --term=spring2024

# Batch generate certificates
python manage.py generate_certificates --document-type=diploma --term=spring2024

# Regenerate documents with updated templates
python manage.py regenerate_documents --template-version=2024.1
```

### Document Maintenance

```bash
# Clean up expired temporary documents
python manage.py cleanup_expired_documents --days=90

# Verify document integrity
python manage.py verify_document_integrity --check-signatures

# Generate document usage reports
python manage.py generate_usage_reports --month=july --format=csv
```

### Template Management

```bash
# Update document templates
python manage.py update_document_templates --template-set=2024

# Validate template configurations
python manage.py validate_templates --document-type=all

# Import legacy document templates
python manage.py import_legacy_templates --source=old_system
```

## API Endpoints

### Document Request API

```python
# Submit document request
POST /api/academic-records/requests/
{
    "document_type": "official_transcript",
    "delivery_method": "email",
    "recipient_email": "admissions@university.edu",
    "purpose": "Graduate school application",
    "rush_processing": false,
    "include_unofficial_courses": false
}

# Response
{
    "request_id": 123,
    "status": "pending_approval",
    "estimated_completion": "2024-07-18",
    "fee_amount": "25.00",
    "tracking_number": "TR-2024-000123"
}
```

### Document Verification API

```python
# Verify document authenticity
POST /api/academic-records/verify/
{
    "verification_code": "NAGA-2024-TXR-847291",
    "requester": {
        "organization": "Graduate University",
        "contact_email": "verify@graduni.edu"
    }
}

# Response
{
    "is_authentic": true,
    "document_type": "Official Transcript",
    "issue_date": "2024-07-15",
    "student_info": {
        "name": "Sophea Chan",
        "student_id": "SIS-12345",
        "graduation_date": "2024-05-15"
    },
    "issuing_institution": {
        "name": "Pannasastra University of Cambodia",
        "location": "Siem Reap, Cambodia"
    }
}
```

### Document Status API

```python
# Check request status
GET /api/academic-records/requests/{request_id}/status/

{
    "request_id": 123,
    "status": "completed",
    "submitted_date": "2024-07-10",
    "completed_date": "2024-07-15",
    "timeline": [
        {
            "status": "submitted",
            "date": "2024-07-10T09:00:00Z",
            "note": "Request submitted by student"
        },
        {
            "status": "approved",
            "date": "2024-07-12T14:30:00Z",
            "note": "Approved by registrar"
        },
        {
            "status": "generated",
            "date": "2024-07-15T10:15:00Z",
            "note": "Document generated and sent"
        }
    ],
    "delivery_info": {
        "method": "email",
        "delivered_date": "2024-07-15T10:30:00Z",
        "tracking_number": "TR-2024-000123"
    }
}
```

## Security Features

### Document Security

```python
class DocumentSecurityService:
    @staticmethod
    def apply_security_features(document_path, security_config):
        """Apply comprehensive security to generated document."""
        # Add digital watermark
        if security_config.get('watermark'):
            DocumentSecurityService.add_watermark(
                document_path,
                watermark_text="OFFICIAL - PANNASASTRA UNIVERSITY"
            )

        # Generate verification code
        verification_code = DocumentSecurityService.generate_verification_code(
            document_path,
            student_id=security_config['student_id']
        )

        # Apply digital signature
        if security_config.get('digital_signature'):
            DocumentSecurityService.sign_document(
                document_path,
                certificate=settings.DOCUMENT_SIGNING_CERT
            )

        # Encrypt if required
        if security_config.get('encryption'):
            DocumentSecurityService.encrypt_document(
                document_path,
                encryption_level=security_config['encryption']
            )

        return verification_code
```

### Access Control

```python
from apps.accounts.decorators import require_permission

@require_permission('academic_records.view_official_documents')
def view_student_transcript(request, student_id):
    """View student transcript - requires proper authorization."""
    # Additional checks for sensitive data access
    if not can_access_student_records(request.user, student_id):
        raise PermissionDenied("Insufficient permissions for this student")

    # Log access for audit trail
    log_document_access(
        user=request.user,
        student_id=student_id,
        document_type='transcript',
        access_reason='Administrative review'
    )
```

## Integration Examples

### With Finance App

```python
# Create fee charge for document request
def process_document_request_with_fee(request_data):
    from apps.finance.services import FinanceService

    # Calculate fees
    fee_amount = DocumentRequestService.calculate_fees(
        document_type=request_data['document_type'],
        delivery_method=request_data['delivery_method'],
        rush_processing=request_data.get('rush_processing', False)
    )

    # Create document request
    document_request = DocumentRequestService.create_request(request_data)

    # Create finance charge
    finance_charge = FinanceService.create_service_charge(
        student=document_request.student,
        service_type='transcript_fee',
        amount=fee_amount,
        description=f"Official transcript fee - {document_request.id}",
        due_date=date.today() + timedelta(days=30)
    )

    # Link request to charge
    document_request.finance_charge = finance_charge
    document_request.save()

    return document_request
```

### With People App

```python
# Generate transcript with comprehensive student data
def generate_comprehensive_transcript(student_profile):
    from apps.people.services import PersonService

    # Get complete student information
    student_data = PersonService.get_comprehensive_profile(student_profile)

    # Include academic history
    academic_history = get_complete_academic_history(student_profile)

    # Generate transcript with all data
    transcript = DocumentGenerationService.generate_transcript(
        student_data=student_data,
        academic_history=academic_history,
        include_honors=True,
        include_activities=True,
        security_level='OFFICIAL'
    )

    return transcript
```

## Testing

### Test Coverage

```bash
# Run academic records tests
pytest apps/academic_records/

# Test specific functionality
pytest apps/academic_records/tests/test_document_generation.py
pytest apps/academic_records/tests/test_security_features.py
pytest apps/academic_records/tests/test_verification_service.py
```

### Test Data

```python
from apps.academic_records.tests.factories import (
    DocumentTypeConfigFactory,
    DocumentRequestFactory,
    GeneratedDocumentFactory
)

# Create test document configuration
transcript_config = DocumentTypeConfigFactory(
    document_type=DocumentType.OFFICIAL_TRANSCRIPT,
    requires_approval=True
)

# Create test document request
request = DocumentRequestFactory(
    document_type=DocumentType.OFFICIAL_TRANSCRIPT,
    student__person__first_name_eng="Test Student"
)
```

## Performance Optimization

### Document Generation

```python
# Efficient batch document generation
def batch_generate_documents(request_ids, batch_size=10):
    """Generate multiple documents efficiently."""
    requests = DocumentRequest.objects.filter(
        id__in=request_ids
    ).select_related(
        'student__person',
        'document_type_config'
    ).prefetch_related(
        'student__academic_history',
        'student__enrollments'
    )

    # Process in batches to manage memory
    for batch in chunk_list(requests, batch_size):
        generated_docs = []
        for request in batch:
            doc = DocumentGenerationService.generate_document(request)
            generated_docs.append(doc)

        # Bulk create for performance
        GeneratedDocument.objects.bulk_create(generated_docs)
```

### Caching Strategy

```python
from django.core.cache import cache

def get_student_transcript_data(student_id):
    """Cached student data for transcript generation."""
    cache_key = f"transcript_data_{student_id}"
    data = cache.get(cache_key)

    if not data:
        data = compile_transcript_data(student_id)
        cache.set(cache_key, data, 1800)  # 30 minutes

    return data
```

## Configuration

### Settings

```python
# Academic records configuration
NAGA_ACADEMIC_RECORDS_CONFIG = {
    'DOCUMENT_STORAGE_PATH': '/secure/documents/',
    'VERIFICATION_CODE_LENGTH': 16,
    'DOCUMENT_RETENTION_YEARS': 50,
    'DIGITAL_SIGNATURE_REQUIRED': True,
    'WATERMARK_TRANSPARENCY': 0.3,
    'ENCRYPTION_ALGORITHM': 'AES-256'
}

# Document fees
NAGA_DOCUMENT_FEES = {
    'OFFICIAL_TRANSCRIPT': Decimal('25.00'),
    'UNOFFICIAL_TRANSCRIPT': Decimal('10.00'),
    'DIPLOMA_COPY': Decimal('50.00'),
    'ENROLLMENT_VERIFICATION': Decimal('15.00'),
    'RUSH_PROCESSING_FEE': Decimal('25.00')
}
```

## Dependencies

### Internal Dependencies

- `people`: Student profile and personal information
- `academic`: Academic history and degree progress
- `finance`: Fee processing and payment tracking
- `common`: Audit logging and base models

### External Dependencies

- `reportlab`: PDF generation and manipulation
- `cryptography`: Document encryption and digital signatures
- `Pillow`: Image processing for watermarks
- `requests`: External verification API integration

## Architecture Notes

### Design Principles

- **Service layer focus**: Document lifecycle management
- **Security-first**: Comprehensive document protection
- **Compliance-ready**: Meets educational record standards
- **Audit trail**: Complete tracking of document operations

### Document Lifecycle

1. **Request** → Student or staff initiates document request
2. **Approval** → Administrative review and approval
3. **Generation** → Secure document creation with features
4. **Delivery** → Secure transmission to recipient
5. **Verification** → Third-party authenticity checking

### Future Enhancements

- **Blockchain verification**: Immutable document verification
- **AI-powered fraud detection**: Advanced security features
- **Mobile document delivery**: Secure mobile app integration
- **International standards**: Support for global document formats
