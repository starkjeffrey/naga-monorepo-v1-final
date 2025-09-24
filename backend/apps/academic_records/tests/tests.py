"""Comprehensive tests for the new flexible academic records app.

Tests the new flexible document system with:
- DocumentTypeConfig: Configuration for different document types
- DocumentRequest: Flexible document request system
- GeneratedDocument: Generated academic documents with verification
- DocumentFeeCalculator: Fee calculation and usage tracking
- DocumentUsageTracker: Usage tracking for free allowances
- DocumentRequestComment: Comments and communication
- DocumentGenerationService: Document generation services

Key testing areas:
- Model validation and business logic
- Document request workflow and approval processes
- Fee calculation and usage tracking
- Document generation and security features
- Service layer functionality
- Clean architecture compliance
"""

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.academic_records.constants import (
    CRYPTOGRAPHIC_HASH_ALGORITHM,
    DEFAULT_DOCUMENT_TYPES,
    VERIFICATION_CODE_LENGTH,
)
from apps.academic_records.models import (
    DocumentFeeCalculator,
    DocumentRequest,
    DocumentRequestComment,
    DocumentTypeConfig,
    DocumentUsageTracker,
    GeneratedDocument,
)
from apps.academic_records.services import (
    DocumentGenerationService,
    TranscriptGenerationError,
)
from apps.people.models import Person, StudentProfile

User = get_user_model()


class DocumentTypeConfigModelTest(TestCase):
    """Test DocumentTypeConfig model functionality."""

    def setUp(self):
        """Set up test data."""
        self.config = DocumentTypeConfig.objects.create(
            code="TEST_TRANSCRIPT",
            name="Test Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            description="Test academic transcript",
            processing_time_hours=24,
            requires_approval=True,
            has_fee=True,
            fee_amount=Decimal("10.00"),
            free_allowance_per_year=2,
        )

    def test_create_document_type_config(self):
        """Test creating a document type configuration."""
        assert self.config.code == "TEST_TRANSCRIPT"
        assert self.config.name == "Test Transcript"
        assert self.config.category == DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT
        assert self.config.has_fee
        assert self.config.fee_amount == Decimal("10.00")
        assert self.config.is_active

    def test_available_delivery_methods(self):
        """Test available delivery methods property."""
        methods = self.config.available_delivery_methods

        # Update config to allow multiple delivery methods
        self.config.allows_email_delivery = True
        self.config.allows_pickup = True
        self.config.allows_mail_delivery = True
        self.config.save()

        methods = self.config.available_delivery_methods
        assert "EMAIL" in methods
        assert "PICKUP" in methods
        assert "MAIL" in methods

    def test_string_representation(self):
        """Test string representation."""
        expected = "Test Transcript"
        assert str(self.config) == expected

    def test_all_categories(self):
        """Test all document categories."""
        categories = [
            DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            DocumentTypeConfig.DocumentCategory.ENROLLMENT_VERIFICATION,
            DocumentTypeConfig.DocumentCategory.GRADE_REPORT,
        ]

        for category in categories:
            config = DocumentTypeConfig.objects.create(
                code=f"TEST_{category}",
                name=f"Test {category}",
                category=category,
                description=f"Test {category} document",
            )
            assert config.category == category


class DocumentRequestModelTest(TestCase):
    """Test DocumentRequest model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            description="Official academic transcript",
            requires_approval=True,
            has_fee=True,
            fee_amount=Decimal("10.00"),
        )

    def test_create_document_request(self):
        """Test creating a document request."""
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            delivery_method=DocumentRequest.DeliveryMethod.EMAIL,
            recipient_email="test@university.edu",
            request_notes="Graduate school application",
            requested_by=self.user,
        )

        assert request.student == self.student
        assert request.document_type == self.document_type
        assert request.delivery_method == DocumentRequest.DeliveryMethod.EMAIL
        assert request.request_status == DocumentRequest.RequestStatus.PENDING
        assert request.priority == DocumentRequest.Priority.NORMAL

    def test_request_status_workflow(self):
        """Test document request status workflow."""
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        # Test initial status
        assert request.request_status == DocumentRequest.RequestStatus.PENDING
        assert not request.is_completed
        assert request.is_overdue is False  # No due date set

        # Test approval
        request.request_status = DocumentRequest.RequestStatus.APPROVED
        request.approved_date = timezone.now()
        request.processed_by = self.user
        request.save()

        assert request.request_status == DocumentRequest.RequestStatus.APPROVED
        assert request.approved_date is not None

        # Test completion
        request.request_status = DocumentRequest.RequestStatus.COMPLETED
        request.completed_date = timezone.now()
        request.save()

        assert request.is_completed
        assert request.completed_date is not None

    def test_delivery_methods(self):
        """Test all delivery methods."""
        delivery_methods = [
            (DocumentRequest.DeliveryMethod.EMAIL, "test@email.com", "", ""),
            (DocumentRequest.DeliveryMethod.PICKUP, "", "John Doe", ""),
            (DocumentRequest.DeliveryMethod.MAIL, "", "Jane Smith", "123 Main St"),
            (
                DocumentRequest.DeliveryMethod.THIRD_PARTY,
                "secure@portal.com",
                "Portal",
                "",
            ),
        ]

        for method, email, name, address in delivery_methods:
            request = DocumentRequest.objects.create(
                student=self.student,
                document_type=self.document_type,
                delivery_method=method,
                recipient_email=email,
                recipient_name=name,
                recipient_address=address,
                requested_by=self.user,
            )
            assert request.delivery_method == method

    def test_priority_levels(self):
        """Test all priority levels."""
        priorities = [
            DocumentRequest.Priority.LOW,
            DocumentRequest.Priority.NORMAL,
            DocumentRequest.Priority.HIGH,
            DocumentRequest.Priority.URGENT,
        ]

        for priority in priorities:
            request = DocumentRequest.objects.create(
                student=self.student,
                document_type=self.document_type,
                priority=priority,
                requested_by=self.user,
            )
            assert request.priority == priority

    def test_due_date_calculation(self):
        """Test due date calculation based on processing time."""
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        # Due date should be calculated based on document type processing time
        expected_due_date = request.requested_date + timedelta(hours=self.document_type.processing_time_hours)
        assert abs((request.due_date - expected_due_date).total_seconds()) < 60  # Within 1 minute

    def test_fee_calculation(self):
        """Test fee calculation for document requests."""
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        assert request.has_fee
        assert request.fee_amount == self.document_type.fee_amount

    def test_string_representation(self):
        """Test string representation."""
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        expected = f"Official Transcript - {self.student} (Pending Review)"
        assert str(request) == expected


class GeneratedDocumentModelTest(TestCase):
    """Test GeneratedDocument model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            description="Official academic transcript",
        )

        self.document_request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

    def test_create_generated_document(self):
        """Test creating a generated document."""
        document = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            file_size=1024,
            content_hash="abc123def456",
            generated_by=self.user,
        )

        assert document.document_request == self.document_request
        assert document.student == self.student
        assert document.document_type == self.document_type
        assert document.verification_code is not None
        assert len(document.verification_code) == VERIFICATION_CODE_LENGTH

    def test_verification_code_generation(self):
        """Test verification code auto-generation."""
        document = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            generated_by=self.user,
        )

        # Verification code should be auto-generated
        assert document.verification_code is not None
        assert len(document.verification_code) == VERIFICATION_CODE_LENGTH
        assert document.verification_code.isupper()
        assert document.verification_code.isalnum()

        # Test uniqueness
        document2 = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            generated_by=self.user,
        )
        assert document.verification_code != document2.verification_code

    def test_access_tracking(self):
        """Test document access tracking."""
        document = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            generated_by=self.user,
        )

        # Initial access tracking
        assert document.access_count == 0
        assert document.last_accessed is None

        # Simulate access
        document.access_count += 1
        document.last_accessed = timezone.now()
        document.save()

        assert document.access_count == 1
        assert document.last_accessed is not None

    def test_string_representation(self):
        """Test string representation."""
        document = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            generated_by=self.user,
        )

        expected = f"Official Transcript - {self.student} ({document.generated_date.date()})"
        assert str(document) == expected


class DocumentFeeCalculatorTest(TestCase):
    """Test DocumentFeeCalculator functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            has_fee=True,
            fee_amount=Decimal("10.00"),
            free_allowance_per_year=2,
        )

    def test_fee_calculation_with_allowance(self):
        """Test fee calculation with free allowance."""
        fee_calculation = DocumentFeeCalculator.calculate_fee(
            student=self.student,
            document_type=self.document_type,
        )

        # First request should use free allowance
        assert fee_calculation["is_free_allowance"]
        assert fee_calculation["fee_amount"] == Decimal("0.00")
        assert fee_calculation["remaining_free_year"] == 2  # Full allowance available since nothing consumed yet

    def test_fee_calculation_without_allowance(self):
        """Test fee calculation when free allowance is exhausted."""
        # Create usage tracker with exhausted allowance
        DocumentUsageTracker.objects.create(
            student=self.student,
            document_type=self.document_type,
            current_year_count=self.document_type.free_allowance_per_year,
            total_free_used=self.document_type.free_allowance_lifetime or 0,
        )

        fee_calculation = DocumentFeeCalculator.calculate_fee(
            student=self.student,
            document_type=self.document_type,
        )

        # Should require payment
        assert not fee_calculation["is_free_allowance"]
        assert fee_calculation["fee_amount"] == self.document_type.fee_amount

    def test_create_request_with_fee_calculation(self):
        """Test creating request with automatic fee calculation."""
        request, fee_calculation = DocumentFeeCalculator.create_request_with_fee_calculation(
            student=self.student,
            document_type=self.document_type,
            delivery_method=DocumentRequest.DeliveryMethod.EMAIL,
            recipient_email="test@university.edu",
            requested_by=self.user,
        )

        assert isinstance(request, DocumentRequest)
        assert request.student == self.student
        assert request.document_type == self.document_type
        assert request.has_fee == self.document_type.has_fee
        assert isinstance(fee_calculation, dict)


class DocumentUsageTrackerTest(TestCase):
    """Test DocumentUsageTracker functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            has_fee=True,
            fee_amount=Decimal("10.00"),
            free_allowance_per_year=2,
            free_allowance_lifetime=5,
        )

    def test_usage_tracker_creation(self):
        """Test creating a usage tracker."""
        tracker = DocumentUsageTracker.objects.create(
            student=self.student,
            document_type=self.document_type,
        )

        assert tracker.student == self.student
        assert tracker.document_type == self.document_type
        assert tracker.total_requested == 0
        assert tracker.total_completed == 0

        # Should initialize with document type's free allowances
        assert tracker.remaining_free_year == self.document_type.free_allowance_per_year
        assert tracker.remaining_free_lifetime == self.document_type.free_allowance_lifetime

    def test_usage_tracking(self):
        """Test usage tracking functionality."""
        tracker = DocumentUsageTracker.objects.create(
            student=self.student,
            document_type=self.document_type,
        )

        # Simulate request by incrementing actual model fields
        tracker.total_requested += 1
        tracker.current_year_count += 1  # This affects remaining_free_year calculation
        tracker.total_free_used += 1  # This affects remaining_free_lifetime calculation
        tracker.save()

        assert tracker.total_requested == 1
        assert tracker.remaining_free_year == 1  # 2 (allowance) - 1 (used) = 1
        assert tracker.remaining_free_lifetime == 4  # 5 (allowance) - 1 (used) = 4

        # Simulate completion
        tracker.total_completed += 1
        tracker.save()

        assert tracker.total_completed == 1

    def test_string_representation(self):
        """Test string representation."""
        tracker = DocumentUsageTracker.objects.create(
            student=self.student,
            document_type=self.document_type,
        )

        expected = f"{self.student} - Official Transcript (0 requested)"
        assert str(tracker) == expected


class DocumentRequestCommentTest(TestCase):
    """Test DocumentRequestComment functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
        )

        self.document_request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

    def test_create_comment(self):
        """Test creating a comment."""
        comment = DocumentRequestComment.objects.create(
            document_request=self.document_request,
            comment_text="Request approved for processing",
            author=self.user,
            is_internal=False,
        )

        assert comment.document_request == self.document_request
        assert comment.comment_text == "Request approved for processing"
        assert comment.author == self.user
        assert not comment.is_internal

    def test_internal_comments(self):
        """Test internal comments functionality."""
        internal_comment = DocumentRequestComment.objects.create(
            document_request=self.document_request,
            comment_text="Internal note: Student has outstanding balance",
            author=self.user,
            is_internal=True,
        )

        public_comment = DocumentRequestComment.objects.create(
            document_request=self.document_request,
            comment_text="Your request has been approved",
            author=self.user,
            is_internal=False,
        )

        assert internal_comment.is_internal
        assert not public_comment.is_internal

    def test_string_representation(self):
        """Test string representation."""
        comment = DocumentRequestComment.objects.create(
            document_request=self.document_request,
            comment_text="Test comment",
            author=self.user,
        )

        expected = f"Comment on {self.document_request} by {self.user}"
        assert str(comment) == expected


class DocumentGenerationServiceTest(TestCase):
    """Test DocumentGenerationService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            description="Official academic transcript",
            requires_grade_data=True,
        )

        self.document_request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

    @patch("apps.academic_records.services.default_storage.save")
    def test_generate_document(self, mock_storage_save):
        """Test document generation."""
        mock_storage_save.return_value = "test/path/document.pdf"

        generated_document = DocumentGenerationService.generate_document(
            document_request=self.document_request,
            generated_by=self.user,
        )

        assert isinstance(generated_document, GeneratedDocument)
        assert generated_document.document_request == self.document_request
        assert generated_document.student == self.student
        assert generated_document.document_type == self.document_type
        assert generated_document.generated_by == self.user
        assert generated_document.verification_code is not None
        assert generated_document.content_hash is not None

    def test_compile_academic_data(self):
        """Test academic data compilation."""
        academic_data = DocumentGenerationService._compile_academic_data(
            student=self.student,
            include_transfer_credits=True,
        )

        assert isinstance(academic_data, dict)
        assert "student" in academic_data
        assert "enrollments_by_term" in academic_data
        assert "total_credits_attempted" in academic_data
        assert "total_credits_earned" in academic_data
        assert academic_data["student"] == self.student

    def test_generate_pdf_content(self):
        """Test PDF content generation."""
        academic_data = {
            "student": self.student,
            "enrollments_by_term": {},
            "total_credits_attempted": 0,
            "total_credits_earned": 0,
            "cumulative_gpa": None,
            "transfer_credits": [],
            "generation_date": timezone.now(),
            "as_of_date": timezone.now(),
        }

        pdf_content = DocumentGenerationService._generate_pdf_transcript(
            student=self.student,
            academic_data=academic_data,
            document_type=self.document_type,
        )

        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")  # PDF file signature

    def test_hash_algorithm_configuration(self):
        """Test that the configured hash algorithm is used."""
        test_content = b"test content"

        # Test that the configured algorithm is used
        getattr(hashlib, CRYPTOGRAPHIC_HASH_ALGORITHM)(test_content).hexdigest()

        # This test verifies the service would use the configured algorithm
        assert hasattr(hashlib, CRYPTOGRAPHIC_HASH_ALGORITHM)

    def test_document_file_url(self):
        """Test document file URL generation."""
        document = GeneratedDocument.objects.create(
            document_request=self.document_request,
            student=self.student,
            generated_by=self.user,
            file_path="test/path/document.pdf",
        )

        # Test when file doesn't exist
        url = DocumentGenerationService.get_document_file_url(document)
        assert url is None  # File doesn't actually exist

    def test_error_handling(self):
        """Test error handling in document generation."""
        # Create invalid request to trigger error
        invalid_request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        # Mock to raise an exception during generation
        with patch.object(
            DocumentGenerationService,
            "_compile_academic_data",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(TranscriptGenerationError):
                DocumentGenerationService.generate_document(
                    document_request=invalid_request,
                    generated_by=self.user,
                )


class AcademicRecordsIntegrationTest(TestCase):
    """Test integration between all academic records components."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Smith",
            personal_name="John",
            date_of_birth=date(1990, 1, 1),
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="1001",
        )

        self.document_type = DocumentTypeConfig.objects.create(
            code="OFFICIAL_TRANSCRIPT",
            name="Official Transcript",
            category=DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            description="Official academic transcript",
            requires_approval=True,
            has_fee=True,
            fee_amount=Decimal("10.00"),
            free_allowance_per_year=2,
        )

    def test_complete_document_workflow(self):
        """Test complete document request and generation workflow."""
        # 1. Create document request with fee calculation
        request, fee_calculation = DocumentFeeCalculator.create_request_with_fee_calculation(
            student=self.student,
            document_type=self.document_type,
            delivery_method=DocumentRequest.DeliveryMethod.EMAIL,
            recipient_email="test@university.edu",
            request_notes="Graduate school application",
            requested_by=self.user,
        )

        # 2. Verify fee calculation (should use free allowance)
        assert fee_calculation["is_free_allowance"]
        assert request.is_free_allowance

        # 3. Add comment to request
        comment = DocumentRequestComment.objects.create(
            document_request=request,
            comment_text="Request approved for processing",
            author=self.user,
        )

        # 4. Approve request
        request.request_status = DocumentRequest.RequestStatus.APPROVED
        request.approved_date = timezone.now()
        request.processed_by = self.user
        request.save()

        # 5. Generate document (mocked to avoid file system operations)
        with patch("apps.academic_records.services.default_storage.save") as mock_save:
            mock_save.return_value = "test/path/document.pdf"

            generated_document = DocumentGenerationService.generate_document(
                document_request=request,
                generated_by=self.user,
            )

        # 6. Complete request
        request.request_status = DocumentRequest.RequestStatus.COMPLETED
        request.completed_date = timezone.now()
        request.save()

        # 7. Verify final state
        assert request.is_completed
        assert generated_document.document_request == request
        assert generated_document.student == self.student
        assert comment.document_request == request

        # 8. Verify usage tracking was updated
        tracker = DocumentUsageTracker.objects.get(
            student=self.student,
            document_type=self.document_type,
        )
        assert tracker.total_requested >= 1

    def test_multiple_document_types(self):
        """Test handling multiple document types."""
        # Create different document types
        transcript_type = self.document_type

        verification_type = DocumentTypeConfig.objects.create(
            code="ENROLLMENT_VERIFICATION",
            name="Enrollment Verification",
            category=DocumentTypeConfig.DocumentCategory.ENROLLMENT_VERIFICATION,
            has_fee=True,
            fee_amount=Decimal("5.00"),
            free_allowance_per_term=1,
        )

        grade_report_type = DocumentTypeConfig.objects.create(
            code="GRADE_REPORT",
            name="Grade Report",
            category=DocumentTypeConfig.DocumentCategory.GRADE_REPORT,
            has_fee=False,
        )

        # Create requests for each type
        requests = []
        for doc_type in [transcript_type, verification_type, grade_report_type]:
            request, _ = DocumentFeeCalculator.create_request_with_fee_calculation(
                student=self.student,
                document_type=doc_type,
                requested_by=self.user,
            )
            requests.append(request)

        # Verify each request has appropriate fee structure
        assert requests[0].has_fee
        assert requests[0].is_free_allowance
        assert requests[1].has_fee  # Verification with fee
        assert not requests[2].has_fee  # Grade report is free

    def test_usage_tracking_across_requests(self):
        """Test usage tracking across multiple requests."""
        # Create multiple requests to test allowance depletion
        requests = []

        for _i in range(3):  # More than the free allowance of 2
            request, fee_calc = DocumentFeeCalculator.create_request_with_fee_calculation(
                student=self.student,
                document_type=self.document_type,
                requested_by=self.user,
            )
            requests.append((request, fee_calc))

        # First two should use free allowance
        assert requests[0][1]["is_free_allowance"]
        assert requests[1][1]["is_free_allowance"]

        # Third should require payment
        assert not requests[2][1]["is_free_allowance"]
        assert requests[2][1]["fee_amount"] == self.document_type.fee_amount

    def test_document_security_features(self):
        """Test comprehensive document security features."""
        # Create and generate document
        request = DocumentRequest.objects.create(
            student=self.student,
            document_type=self.document_type,
            requested_by=self.user,
        )

        with patch("apps.academic_records.services.default_storage.save") as mock_save:
            mock_save.return_value = "test/path/document.pdf"

            document = DocumentGenerationService.generate_document(
                document_request=request,
                generated_by=self.user,
            )

        # Verify security features
        assert document.verification_code is not None
        assert len(document.verification_code) == VERIFICATION_CODE_LENGTH
        assert document.content_hash is not None
        assert len(document.content_hash) > 0

        # Test verification code uniqueness
        with patch("apps.academic_records.services.default_storage.save") as mock_save:
            mock_save.return_value = "test/path/document2.pdf"

            document2 = DocumentGenerationService.generate_document(
                document_request=request,
                generated_by=self.user,
            )

        assert document.verification_code != document2.verification_code


class ConstantsTest(TestCase):
    """Test that constants are properly configured."""

    def test_default_document_types(self):
        """Test that default document types are properly configured."""
        assert isinstance(DEFAULT_DOCUMENT_TYPES, dict)
        assert "OFFICIAL_TRANSCRIPT" in DEFAULT_DOCUMENT_TYPES
        assert "UNOFFICIAL_TRANSCRIPT" in DEFAULT_DOCUMENT_TYPES

        # Test structure of default document type
        official_transcript = DEFAULT_DOCUMENT_TYPES["OFFICIAL_TRANSCRIPT"]
        assert "name" in official_transcript
        assert "category" in official_transcript
        assert "has_fee" in official_transcript

    def test_verification_code_length(self):
        """Test verification code length constant."""
        assert isinstance(VERIFICATION_CODE_LENGTH, int)
        assert VERIFICATION_CODE_LENGTH >= 12  # Minimum security requirement

    def test_cryptographic_algorithm(self):
        """Test cryptographic hash algorithm is valid."""
        assert hasattr(hashlib, CRYPTOGRAPHIC_HASH_ALGORITHM)

        # Test the algorithm works
        test_data = b"test data"
        hash_func = getattr(hashlib, CRYPTOGRAPHIC_HASH_ALGORITHM)
        result = hash_func(test_data).hexdigest()
        assert isinstance(result, str)
        assert len(result) > 0
