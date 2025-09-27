"""
Comprehensive Integration Tests for Staff-Web V2 API
Tests complete workflows across all modules with real database interactions
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

# Import models from all apps
from apps.people.models import Person, StudentProfile
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.grading.models import Grade, Assignment
from apps.attendance.models import AttendanceRecord
from apps.finance.models import Payment, Invoice, Currency
from apps.scheduling.models import ClassHeader, TimeSlot, Room
from apps.curriculum.models import Course, Program
from apps.scholarships.models import Scholarship, ScholarshipApplication


class BaseAPIIntegrationTest(APITestCase):
    """Base class for API integration tests with common setup."""

    def setUp(self):
        """Set up test data for integration tests."""
        # Create test user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test person and student
        self.test_person = Person.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@test.com",
            date_of_birth="1995-05-15"
        )

        self.test_student = StudentProfile.objects.create(
            person=self.test_person,
            student_id="ST12345",
            status="active",
            enrollment_start_date=datetime.now().date()
        )

        # Create test program and course
        self.test_program = Program.objects.create(
            name="Computer Science",
            code="CS",
            description="Computer Science Program"
        )

        self.test_course = Course.objects.create(
            name="Introduction to Programming",
            code="CS101",
            credit_hours=3,
            description="Basic programming concepts"
        )

        # Create test class header
        self.test_class_header = ClassHeader.objects.create(
            course=self.test_course,
            instructor=None,  # Can be set in specific tests
            capacity=30
        )

        # Create test enrollment
        self.test_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.test_student,
            class_header=self.test_class_header,
            status="enrolled"
        )

        # Create test assignment
        self.test_assignment = Assignment.objects.create(
            class_header=self.test_class_header,
            name="Test Assignment",
            assignment_type="homework",
            max_score=100,
            weight=0.2
        )

        # Create test currency
        self.test_currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )

        # Authenticate client
        self.client.force_authenticate(user=self.user)


class StudentManagementIntegrationTest(BaseAPIIntegrationTest):
    """Integration tests for Student Management API endpoints."""

    def test_complete_student_workflow(self):
        """Test complete student management workflow."""

        # 1. Search for students
        search_url = reverse('api-v2:students-search')
        search_data = {
            "query": "John",
            "fuzzy_search": True,
            "page": 1,
            "page_size": 10
        }

        response = self.client.post(search_url, search_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        # 2. Get detailed student information
        detail_url = reverse('api-v2:student-detail', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_id'], "ST12345")

        # 3. Get student analytics
        analytics_url = reverse('api-v2:student-analytics', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.get(analytics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success_prediction', response.data)

        # 4. Get student timeline
        timeline_url = reverse('api-v2:student-timeline', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('events', response.data)

        # 5. Upload student photo
        photo_data = SimpleUploadedFile(
            "test_photo.jpg",
            b"fake_image_content",
            content_type="image/jpeg"
        )
        photo_url = reverse('api-v2:student-photo-upload', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.post(photo_url, {'photo': photo_data, 'is_primary': True}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bulk_student_operations(self):
        """Test bulk operations on multiple students."""

        # Create additional test students
        additional_students = []
        for i in range(3):
            person = Person.objects.create(
                first_name=f"Student{i}",
                last_name="Test",
                email=f"student{i}@test.com"
            )
            student = StudentProfile.objects.create(
                person=person,
                student_id=f"ST1234{i}",
                status="active"
            )
            additional_students.append(student)

        # Test bulk status update
        bulk_url = reverse('api-v2:student-bulk-actions')
        bulk_data = {
            "action": "update_status",
            "target_ids": [str(s.unique_id) for s in additional_students],
            "parameters": {"status": "inactive"},
            "dry_run": True
        }

        response = self.client.post(bulk_url, bulk_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success_count'], 3)

        # Test bulk export
        export_data = {
            "action": "export_data",
            "target_ids": [str(s.unique_id) for s in additional_students],
            "parameters": {"format": "csv"},
            "dry_run": True
        }

        response = self.client.post(bulk_url, export_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AcademicManagementIntegrationTest(BaseAPIIntegrationTest):
    """Integration tests for Academic Management API endpoints."""

    def test_grade_management_workflow(self):
        """Test complete grade management workflow."""

        # 1. Get grade spreadsheet data
        spreadsheet_url = reverse('api-v2:grade-spreadsheet', kwargs={'class_id': self.test_class_header.unique_id})
        response = self.client.get(spreadsheet_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('assignments', response.data)
        self.assertIn('students', response.data)

        # 2. Bulk update grades
        grade_data = [{
            "student_id": str(self.test_student.unique_id),
            "assignment_id": str(self.test_assignment.unique_id),
            "score": 95,
            "notes": "Excellent work",
            "last_modified": datetime.now().isoformat()
        }]

        bulk_update_url = reverse('api-v2:grade-bulk-update', kwargs={'class_id': self.test_class_header.unique_id})
        response = self.client.post(bulk_update_url, grade_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success_count'], 1)

        # Verify grade was created
        grade = Grade.objects.filter(
            enrollment=self.test_enrollment,
            assignment=self.test_assignment
        ).first()
        self.assertIsNotNone(grade)
        self.assertEqual(grade.score, 95)

    def test_schedule_conflict_detection(self):
        """Test schedule conflict detection system."""

        # Create overlapping time slots
        time_slot1 = TimeSlot.objects.create(
            day_of_week="Monday",
            start_time="09:00:00",
            end_time="10:30:00"
        )

        time_slot2 = TimeSlot.objects.create(
            day_of_week="Monday",
            start_time="09:30:00",  # Overlapping
            end_time="11:00:00"
        )

        # Create room
        room = Room.objects.create(
            room_number="101",
            building="Main",
            capacity=25
        )

        # Create conflicting classes
        class1 = ClassHeader.objects.create(
            course=self.test_course,
            capacity=20
        )

        class2 = ClassHeader.objects.create(
            course=self.test_course,
            capacity=20
        )

        # Test conflict detection
        conflicts_url = reverse('api-v2:schedule-conflicts')
        response = self.client.get(conflicts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transcript_generation(self):
        """Test transcript generation functionality."""

        # Create grade for transcript
        Grade.objects.create(
            enrollment=self.test_enrollment,
            assignment=self.test_assignment,
            score=90,
            entered_by=self.user
        )

        # Generate transcript
        transcript_url = reverse('api-v2:generate-transcript', kwargs={'student_id': self.test_student.unique_id})
        params = {"template": "official", "include_unofficial": False}

        response = self.client.get(transcript_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('transcript_data', response.data)
        self.assertIn('student', response.data['transcript_data'])

    def test_qr_attendance_processing(self):
        """Test QR code attendance processing."""

        # Test QR attendance
        qr_url = reverse('api-v2:qr-attendance')
        qr_data = {
            "qr_data": f"{self.test_class_header.unique_id}:{self.test_student.unique_id}:{datetime.now().isoformat()}",
            "location": "Room 101"
        }

        response = self.client.post(qr_url, qr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'present')

        # Verify attendance record was created
        attendance = AttendanceRecord.objects.filter(
            student=self.test_student,
            class_header=self.test_class_header
        ).first()
        self.assertIsNotNone(attendance)


class FinancialManagementIntegrationTest(BaseAPIIntegrationTest):
    """Integration tests for Financial Management API endpoints."""

    def test_pos_transaction_workflow(self):
        """Test complete POS transaction workflow."""

        # 1. Process POS transaction
        pos_url = reverse('api-v2:pos-transaction')
        transaction_data = {
            "amount": 150.00,
            "payment_method": "cash",
            "description": "Tuition Payment",
            "student_id": str(self.test_student.unique_id),
            "line_items": [
                {
                    "description": "Tuition Fee",
                    "quantity": 1,
                    "unit_price": 150.00,
                    "total_amount": 150.00
                }
            ]
        }

        response = self.client.post(pos_url, transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('transaction_id', response.data)
        self.assertEqual(response.data['status'], 'completed')

        # Verify payment was created
        payment = Payment.objects.filter(
            invoice__student=self.test_student,
            amount=Decimal('150.00')
        ).first()
        self.assertIsNotNone(payment)

    def test_financial_analytics_dashboard(self):
        """Test financial analytics dashboard."""

        # Create some financial data
        invoice = Invoice.objects.create(
            student=self.test_student,
            amount=Decimal('500.00'),
            currency=self.test_currency,
            due_date=datetime.now().date(),
            status='pending'
        )

        Payment.objects.create(
            invoice=invoice,
            amount=Decimal('300.00'),
            currency=self.test_currency,
            payment_method='credit_card',
            status='completed'
        )

        # Test analytics dashboard
        analytics_url = reverse('api-v2:financial-analytics')
        params = {"date_range": 30, "include_forecasts": True}

        response = self.client.get(analytics_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', response.data)
        self.assertIn('pending_payments', response.data)

    def test_payment_reminder_automation(self):
        """Test automated payment reminder system."""

        # Create overdue invoice
        overdue_invoice = Invoice.objects.create(
            student=self.test_student,
            amount=Decimal('200.00'),
            currency=self.test_currency,
            due_date=datetime.now().date() - timedelta(days=5),
            status='pending'
        )

        # Setup payment reminders
        reminder_url = reverse('api-v2:payment-reminders')
        reminder_data = {
            "student_ids": [str(self.test_student.unique_id)],
            "reminder_days": [7, 3, 1],
            "template": "default"
        }

        response = self.client.post(reminder_url, reminder_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class InnovationAIIntegrationTest(BaseAPIIntegrationTest):
    """Integration tests for Innovation AI/ML API endpoints."""

    def test_ai_prediction_workflow(self):
        """Test complete AI prediction workflow."""

        # Create some historical data for predictions
        Grade.objects.create(
            enrollment=self.test_enrollment,
            assignment=self.test_assignment,
            score=85
        )

        AttendanceRecord.objects.create(
            student=self.test_student,
            class_header=self.test_class_header,
            date=datetime.now().date(),
            status='present'
        )

        # 1. Test success prediction
        prediction_url = reverse('api-v2:ai-predictions')
        prediction_data = {
            "model_type": "success_prediction",
            "input_data": {
                "student_id": str(self.test_student.unique_id)
            }
        }

        response = self.client.post(prediction_url, prediction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('prediction', response.data)
        self.assertIn('confidence', response.data)

        # 2. Test risk assessment
        risk_data = {
            "model_type": "risk_assessment",
            "input_data": {
                "student_id": str(self.test_student.unique_id)
            }
        }

        response = self.client.post(prediction_url, risk_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('prediction', response.data)

        # 3. Test grade prediction
        grade_prediction_data = {
            "model_type": "grade_prediction",
            "input_data": {
                "student_id": str(self.test_student.unique_id),
                "assignment_id": str(self.test_assignment.unique_id)
            }
        }

        response = self.client.post(prediction_url, grade_prediction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('prediction', response.data)

    def test_document_ocr_processing(self):
        """Test document OCR processing workflow."""

        # Create test document
        test_document = SimpleUploadedFile(
            "test_transcript.pdf",
            b"fake_pdf_content",
            content_type="application/pdf"
        )

        # Test OCR processing
        ocr_url = reverse('api-v2:document-ocr')
        response = self.client.post(ocr_url, {'document': test_document}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('extracted_text', response.data)
        self.assertIn('confidence_score', response.data)

    def test_workflow_automation(self):
        """Test workflow automation system."""

        # 1. List available workflows
        workflows_url = reverse('api-v2:automation-workflows')
        response = self.client.get(workflows_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # 2. Execute workflow
        if response.data:
            workflow_id = response.data[0]['workflow_id']
            execute_url = reverse('api-v2:execute-workflow', kwargs={'workflow_id': workflow_id})
            execute_data = {
                "parameters": {
                    "student_id": str(self.test_student.unique_id)
                }
            }

            response = self.client.post(execute_url, execute_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('execution_id', response.data)

    def test_custom_analytics_dashboard(self):
        """Test custom analytics dashboard."""

        dashboard_url = reverse('api-v2:custom-dashboard')
        params = {"metrics": ["enrollment_trends", "grade_distribution", "revenue_forecast"]}

        response = self.client.get(dashboard_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # Check that each chart has required fields
        for chart in response.data:
            self.assertIn('title', chart)
            self.assertIn('type', chart)
            self.assertIn('data', chart)


class CrossModuleIntegrationTest(BaseAPIIntegrationTest):
    """Integration tests that span multiple modules."""

    def test_complete_student_lifecycle(self):
        """Test complete student lifecycle across all modules."""

        # 1. Student enrollment and basic setup
        self.assertEqual(self.test_enrollment.status, 'enrolled')

        # 2. Academic activities (grades and attendance)
        Grade.objects.create(
            enrollment=self.test_enrollment,
            assignment=self.test_assignment,
            score=88
        )

        AttendanceRecord.objects.create(
            student=self.test_student,
            class_header=self.test_class_header,
            date=datetime.now().date(),
            status='present'
        )

        # 3. Financial transactions
        invoice = Invoice.objects.create(
            student=self.test_student,
            amount=Decimal('300.00'),
            currency=self.test_currency,
            due_date=datetime.now().date()
        )

        Payment.objects.create(
            invoice=invoice,
            amount=Decimal('300.00'),
            currency=self.test_currency,
            payment_method='cash',
            status='completed'
        )

        # 4. AI predictions based on all data
        prediction_url = reverse('api-v2:ai-predictions')
        prediction_data = {
            "model_type": "success_prediction",
            "input_data": {
                "student_id": str(self.test_student.unique_id)
            }
        }

        response = self.client.post(prediction_url, prediction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The prediction should now be based on actual academic and financial data
        self.assertGreater(response.data['confidence'], 0.5)

        # 5. Generate comprehensive analytics
        analytics_url = reverse('api-v2:student-analytics', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.get(analytics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Analytics should reflect all the data we created
        self.assertGreater(response.data['attendance_rate'], 0)
        self.assertGreater(response.data['grade_average'], 0)

    def test_real_time_collaboration_simulation(self):
        """Test real-time collaboration features simulation."""

        # Simulate multiple users updating grades simultaneously
        grade_data = [
            {
                "student_id": str(self.test_student.unique_id),
                "assignment_id": str(self.test_assignment.unique_id),
                "score": 92,
                "notes": "Great improvement",
                "last_modified": datetime.now().isoformat()
            }
        ]

        bulk_update_url = reverse('api-v2:grade-bulk-update', kwargs={'class_id': self.test_class_header.unique_id})

        # First update
        response1 = self.client.post(bulk_update_url, grade_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Simulate concurrent update (should handle gracefully)
        grade_data[0]['score'] = 94
        grade_data[0]['notes'] = "Excellent work"

        response2 = self.client.post(bulk_update_url, grade_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_performance_under_load(self):
        """Test system performance with multiple concurrent operations."""

        # Create multiple students for load testing
        students = []
        for i in range(10):
            person = Person.objects.create(
                first_name=f"LoadTest{i}",
                last_name="Student",
                email=f"loadtest{i}@test.com"
            )
            student = StudentProfile.objects.create(
                person=person,
                student_id=f"LT{i:04d}",
                status="active"
            )
            students.append(student)

        # Test bulk search performance
        search_url = reverse('api-v2:students-search')
        search_data = {
            "query": "LoadTest",
            "fuzzy_search": True,
            "page": 1,
            "page_size": 50
        }

        response = self.client.post(search_url, search_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 10)

        # Test bulk analytics
        for student in students[:5]:  # Test with subset
            analytics_url = reverse('api-v2:student-analytics', kwargs={'student_id': student.unique_id})
            response = self.client.get(analytics_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class SecurityIntegrationTest(BaseAPIIntegrationTest):
    """Security-focused integration tests."""

    def test_authentication_required(self):
        """Test that authentication is required for protected endpoints."""

        # Create unauthenticated client
        unauth_client = APIClient()

        # Test various endpoints without authentication
        endpoints = [
            reverse('api-v2:students-search'),
            reverse('api-v2:student-detail', kwargs={'student_id': self.test_student.unique_id}),
            reverse('api-v2:financial-analytics'),
            reverse('api-v2:ai-predictions'),
        ]

        for endpoint in endpoints:
            response = unauth_client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_input_validation_and_sanitization(self):
        """Test input validation and sanitization."""

        # Test SQL injection prevention
        search_url = reverse('api-v2:students-search')
        malicious_data = {
            "query": "'; DROP TABLE students; --",
            "fuzzy_search": True
        }

        response = self.client.post(search_url, malicious_data, format='json')
        # Should not cause an error and should sanitize input
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test XSS prevention
        xss_data = {
            "query": "<script>alert('xss')</script>",
            "fuzzy_search": True
        }

        response = self.client.post(search_url, xss_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test oversized payload
        large_data = {
            "query": "A" * 10000,  # Very large query
            "fuzzy_search": True
        }

        response = self.client.post(search_url, large_data, format='json')
        # Should either process safely or return appropriate error
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE])

    def test_data_access_controls(self):
        """Test that users can only access appropriate data."""

        # Create another student
        other_person = Person.objects.create(
            first_name="Other",
            last_name="Student",
            email="other@test.com"
        )
        other_student = StudentProfile.objects.create(
            person=other_person,
            student_id="OTHER001",
            status="active"
        )

        # Test that user can access allowed student data
        detail_url = reverse('api-v2:student-detail', kwargs={'student_id': self.test_student.unique_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test access to other student (should be allowed for staff)
        other_detail_url = reverse('api-v2:student-detail', kwargs={'student_id': other_student.unique_id})
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])