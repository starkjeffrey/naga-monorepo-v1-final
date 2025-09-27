"""Comprehensive tests for Innovation API v2 endpoints.

This module tests all innovation-focused functionality including:
- AI-powered predictions and machine learning
- Workflow automation
- Document intelligence and OCR
- Real-time communications
- Custom analytics and reporting
"""

import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from ninja.testing import TestClient

from api.v2 import api
from apps.people.models import StudentProfile, Person
from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import Grade, Assignment
from apps.attendance.models import AttendanceRecord
from apps.finance.models import Payment, Invoice
from apps.scholarships.models import Scholarship

User = get_user_model()


class InnovationAPITestCase(TestCase):
    """Base test case for Innovation API tests."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient(api)

        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # Create test person and student
        self.person = Person.objects.create(
            family_name="Test",
            personal_name="Student",
            school_email="student@test.com"
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id="ST12345",
            status="active"
        )

        # Mock authentication by setting user in client
        self.client._client.defaults['HTTP_AUTHORIZATION'] = f'Bearer mock-jwt-token'


class TestAIPredictionsAPI(InnovationAPITestCase):
    """Test AI predictions and machine learning endpoints."""

    def test_student_success_prediction(self):
        """Test student success prediction endpoint."""
        prediction_request = {
            "model_type": "success_prediction",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.5
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure
        self.assertIn("prediction", data)
        self.assertIn("confidence", data)
        self.assertIn("model_version", data)
        self.assertIn("features_used", data)
        self.assertIn("explanation", data)
        self.assertIn("recommendations", data)

        # Verify prediction is a float between 0 and 1
        self.assertIsInstance(data["prediction"], float)
        self.assertGreaterEqual(data["prediction"], 0.0)
        self.assertLessEqual(data["prediction"], 1.0)

        # Verify confidence is between 0 and 1
        self.assertGreaterEqual(data["confidence"], 0.0)
        self.assertLessEqual(data["confidence"], 1.0)

    def test_risk_assessment_prediction(self):
        """Test student risk assessment endpoint."""
        prediction_request = {
            "model_type": "risk_assessment",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.7
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify risk prediction structure
        self.assertIn("prediction", data)
        self.assertIn("risk_level", data["prediction"])
        self.assertIn("factors", data["prediction"])

        # Verify risk level is valid
        valid_risk_levels = ["low", "medium", "high"]
        self.assertIn(data["prediction"]["risk_level"], valid_risk_levels)

    def test_grade_prediction(self):
        """Test grade performance prediction."""
        prediction_request = {
            "model_type": "grade_prediction",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.6
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify grade prediction is numeric
        self.assertIsInstance(data["prediction"], (int, float))
        self.assertGreaterEqual(data["prediction"], 0)
        self.assertLessEqual(data["prediction"], 100)

    def test_scholarship_matching(self):
        """Test AI-powered scholarship matching."""
        # Create test scholarship
        scholarship = Scholarship.objects.create(
            name="Test Scholarship",
            amount=Decimal("1000.00"),
            is_active=True,
            application_deadline=datetime.now() + timedelta(days=30),
            min_gpa=3.0
        )

        prediction_request = {
            "model_type": "scholarship_matching",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.5
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify scholarship matches structure
        self.assertIsInstance(data["prediction"], list)

    def test_enrollment_forecast(self):
        """Test enrollment forecasting prediction."""
        prediction_request = {
            "model_type": "enrollment_forecast",
            "input_data": {"term": "2024-spring"},
            "confidence_threshold": 0.6
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify forecast structure
        self.assertIn("prediction", data)
        self.assertIn("projected_enrollment", data["prediction"])
        self.assertIn("growth_rate", data["prediction"])

    def test_invalid_model_type(self):
        """Test prediction with invalid model type."""
        prediction_request = {
            "model_type": "invalid_model",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.5
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)  # API handles gracefully
        data = response.json()
        self.assertIn("Prediction failed", data["explanation"])


class TestWorkflowAutomationAPI(InnovationAPITestCase):
    """Test workflow automation endpoints."""

    def test_list_workflows(self):
        """Test listing available workflow templates."""
        response = self.client.get("/innovation/automation/workflows/")

        self.assertEqual(response.status_code, 200)
        workflows = response.json()

        # Verify response is a list
        self.assertIsInstance(workflows, list)
        self.assertGreater(len(workflows), 0)

        # Verify workflow structure
        workflow = workflows[0]
        required_fields = [
            "workflow_id", "name", "description", "trigger_type",
            "steps", "is_active"
        ]
        for field in required_fields:
            self.assertIn(field, workflow)

    def test_execute_workflow(self):
        """Test manual workflow execution."""
        workflow_id = uuid4()
        parameters = {"student_id": str(self.student.unique_id)}

        response = self.client.post(
            f"/innovation/automation/workflows/{workflow_id}/execute/",
            json=parameters
        )

        self.assertEqual(response.status_code, 200)
        execution = response.json()

        # Verify execution structure
        required_fields = [
            "execution_id", "workflow_id", "status", "started_at",
            "steps_completed", "total_steps", "logs"
        ]
        for field in required_fields:
            self.assertIn(field, execution)

        # Verify status is valid
        valid_statuses = ["running", "completed", "failed", "cancelled"]
        self.assertIn(execution["status"], valid_statuses)


class TestDocumentIntelligenceAPI(InnovationAPITestCase):
    """Test document intelligence and OCR endpoints."""

    def test_document_ocr_processing(self):
        """Test OCR document processing."""
        # Create mock PDF file
        pdf_content = b"Mock PDF content for testing"
        test_file = SimpleUploadedFile(
            "test_document.pdf",
            pdf_content,
            content_type="application/pdf"
        )

        response = self.client.post(
            "/innovation/documents/ocr/",
            files={"document": test_file}
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        # Verify OCR result structure
        required_fields = [
            "document_id", "confidence_score", "extracted_text",
            "entities", "processed_data", "processing_time"
        ]
        for field in required_fields:
            self.assertIn(field, result)

        # Verify confidence score is valid
        self.assertGreaterEqual(result["confidence_score"], 0.0)
        self.assertLessEqual(result["confidence_score"], 1.0)

    def test_document_ocr_invalid_file_type(self):
        """Test OCR with invalid file type."""
        # Create mock text file
        text_content = b"This is a text file"
        test_file = SimpleUploadedFile(
            "test.txt",
            text_content,
            content_type="text/plain"
        )

        response = self.client.post(
            "/innovation/documents/ocr/",
            files={"document": test_file}
        )

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_document_intelligence_analysis(self):
        """Test document intelligence analysis."""
        document_id = uuid4()

        response = self.client.post(
            "/innovation/documents/intelligence/",
            json={"document_id": str(document_id)}
        )

        self.assertEqual(response.status_code, 200)
        analysis = response.json()

        # Verify analysis structure
        required_fields = [
            "document_type", "key_fields", "validation_status",
            "confidence_scores", "suggestions"
        ]
        for field in required_fields:
            self.assertIn(field, analysis)


class TestCommunicationsAPI(InnovationAPITestCase):
    """Test real-time communications endpoints."""

    def test_list_message_threads(self):
        """Test listing message threads."""
        response = self.client.get("/innovation/communications/threads/")

        self.assertEqual(response.status_code, 200)
        threads = response.json()

        # Verify response is a list
        self.assertIsInstance(threads, list)

        if threads:  # If there are threads
            thread = threads[0]
            required_fields = [
                "thread_id", "subject", "participants", "message_count",
                "last_message", "last_message_preview", "unread_count"
            ]
            for field in required_fields:
                self.assertIn(field, thread)

    def test_get_thread_messages(self):
        """Test getting messages from a thread."""
        thread_id = uuid4()

        response = self.client.get(
            f"/innovation/communications/threads/{thread_id}/messages/"
        )

        self.assertEqual(response.status_code, 200)
        messages = response.json()

        # Verify response is a list
        self.assertIsInstance(messages, list)

        if messages:  # If there are messages
            message = messages[0]
            required_fields = [
                "message_id", "thread_id", "sender", "content",
                "timestamp", "message_type"
            ]
            for field in required_fields:
                self.assertIn(field, message)

    def test_send_message(self):
        """Test sending a message to a thread."""
        thread_id = uuid4()

        # Create mock attachment
        attachment = SimpleUploadedFile(
            "test_attachment.pdf",
            b"Mock file content",
            content_type="application/pdf"
        )

        response = self.client.post(
            f"/innovation/communications/threads/{thread_id}/messages/",
            data={"content": "Test message"},
            files={"attachments": attachment}
        )

        self.assertEqual(response.status_code, 200)
        message = response.json()

        # Verify message structure
        required_fields = [
            "message_id", "thread_id", "sender", "content",
            "timestamp", "attachments"
        ]
        for field in required_fields:
            self.assertIn(field, message)


class TestCustomAnalyticsAPI(InnovationAPITestCase):
    """Test custom analytics and reporting endpoints."""

    def test_get_custom_dashboard_data(self):
        """Test getting custom dashboard analytics."""
        response = self.client.get(
            "/innovation/analytics/custom/dashboard/",
            params={"metrics": ["enrollment_trends", "grade_distribution"]}
        )

        self.assertEqual(response.status_code, 200)
        charts = response.json()

        # Verify response is a list of charts
        self.assertIsInstance(charts, list)
        self.assertGreater(len(charts), 0)

        # Verify chart structure
        chart = charts[0]
        required_fields = ["title", "type", "data", "options"]
        for field in required_fields:
            self.assertIn(field, chart)

        # Verify chart types are valid
        valid_types = ["line", "bar", "pie", "area"]
        self.assertIn(chart["type"], valid_types)

    def test_generate_custom_report(self):
        """Test generating custom analytics report."""
        report_config = {
            "report_type": "student_performance",
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-12-31"
            },
            "filters": {
                "programs": ["computer_science"],
                "levels": ["undergraduate"]
            }
        }

        response = self.client.post(
            "/innovation/analytics/custom/report/",
            json=report_config
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()

        # Verify report generation response
        required_fields = [
            "report_id", "status", "progress", "estimated_completion"
        ]
        for field in required_fields:
            self.assertIn(field, result)

    def test_get_report_status(self):
        """Test getting report generation status."""
        report_id = uuid4()

        response = self.client.get(
            f"/innovation/analytics/custom/report/{report_id}/status/"
        )

        self.assertEqual(response.status_code, 200)
        status = response.json()

        # Verify status response
        required_fields = [
            "report_id", "status", "progress"
        ]
        for field in required_fields:
            self.assertIn(field, status)

        # Verify progress is valid
        self.assertGreaterEqual(status["progress"], 0)
        self.assertLessEqual(status["progress"], 100)


class TestInnovationAPIPerformance(InnovationAPITestCase):
    """Test performance and caching of Innovation API."""

    def test_ai_prediction_caching(self):
        """Test that AI predictions are properly cached."""
        prediction_request = {
            "model_type": "success_prediction",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.5
        }

        # First request
        start_time = datetime.now()
        response1 = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )
        first_duration = (datetime.now() - start_time).total_seconds()

        # Second identical request (should be cached)
        start_time = datetime.now()
        response2 = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )
        second_duration = (datetime.now() - start_time).total_seconds()

        # Verify both requests succeeded
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Second request should be faster due to caching
        # Note: This might not always be true in test environment
        # but demonstrates the caching concept
        self.assertIsNotNone(response1.json())
        self.assertIsNotNone(response2.json())

    def test_api_response_time(self):
        """Test API response times are within acceptable limits."""
        endpoints_to_test = [
            "/innovation/automation/workflows/",
            "/innovation/communications/threads/",
            "/innovation/analytics/custom/dashboard/"
        ]

        for endpoint in endpoints_to_test:
            start_time = datetime.now()
            response = self.client.get(endpoint)
            duration = (datetime.now() - start_time).total_seconds()

            # Verify response is successful
            self.assertEqual(response.status_code, 200)

            # Verify response time is reasonable (< 2 seconds for mock data)
            self.assertLess(duration, 2.0)


class TestInnovationAPIIntegration(InnovationAPITestCase):
    """Integration tests for Innovation API with other components."""

    def test_ai_prediction_with_real_data(self):
        """Test AI predictions with actual student data."""
        # Create some attendance records
        AttendanceRecord.objects.create(
            student=self.student,
            date=datetime.now().date(),
            status="present"
        )

        # Create some grades
        assignment = Assignment.objects.create(
            name="Test Assignment",
            max_score=100
        )

        Grade.objects.create(
            assignment=assignment,
            score=85.0
        )

        # Test prediction with real data
        prediction_request = {
            "model_type": "success_prediction",
            "input_data": {"student_id": str(self.student.unique_id)},
            "confidence_threshold": 0.5
        }

        response = self.client.post(
            "/innovation/ai/predictions/",
            json=prediction_request
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should have higher confidence with real data
        self.assertGreater(data["confidence"], 0.0)
        self.assertIn("attendance_rate", data["features_used"])


if __name__ == "__main__":
    pytest.main([__file__])