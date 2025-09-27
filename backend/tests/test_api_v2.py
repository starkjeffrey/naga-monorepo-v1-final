"""Comprehensive test suite for the enhanced API v2.

This module provides extensive testing coverage for:
- All API v2 endpoints with various scenarios
- GraphQL queries, mutations, and subscriptions
- WebSocket functionality and real-time features
- Performance and caching behavior
- Security and authentication
"""

import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.people.models import Person, StudentProfile
from apps.curriculum.models import Course
from apps.scheduling.models import ClassHeader
from apps.grading.models import Assignment, Grade
from apps.enrollment.models import ClassHeaderEnrollment

from config.consumers import GradeEntryCollaborationConsumer


class BaseAPIv2TestCase(APITestCase):
    """Base test case for API v2 with common setup."""

    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Create test data
        self.person = Person.objects.create(
            family_name='Doe',
            personal_name='John',
            school_email='john.doe@example.com'
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id='STU001',
            status='enrolled',
            current_level='undergraduate'
        )

        self.course = Course.objects.create(
            code='MATH101',
            name='Introduction to Mathematics',
            credit_hours=3
        )

        cache.clear()  # Clear cache before each test

    def tearDown(self):
        """Clean up after each test."""
        cache.clear()


class StudentAPIv2Tests(BaseAPIv2TestCase):
    """Test suite for enhanced student API endpoints."""

    def test_student_search_basic(self):
        """Test basic student search functionality."""
        url = '/api/v2/students/search/'
        response = self.client.get(url, {
            'query': 'john',
            'page': 1,
            'page_size': 25
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

        if data:  # If results returned
            student = data[0]
            self.assertIn('unique_id', student)
            self.assertIn('student_id', student)
            self.assertIn('full_name', student)
            self.assertIn('match_score', student)

    def test_student_search_fuzzy(self):
        """Test fuzzy search functionality."""
        url = '/api/v2/students/search/'
        response = self.client.get(url, {
            'query': 'jhon',  # Misspelled name
            'fuzzy_search': 'true',
            'page': 1,
            'page_size': 10
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_student_detail(self):
        """Test student detail endpoint."""
        url = f'/api/v2/students/{self.student.unique_id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        expected_fields = [
            'unique_id', 'student_id', 'full_name', 'email',
            'program', 'level', 'status', 'analytics',
            'enrollments', 'payments', 'timeline'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

        # Check analytics structure
        if data.get('analytics'):
            analytics = data['analytics']
            self.assertIn('success_prediction', analytics)
            self.assertIn('risk_factors', analytics)
            self.assertIn('attendance_rate', analytics)

    def test_student_analytics(self):
        """Test student analytics endpoint."""
        url = f'/api/v2/students/{self.student.unique_id}/analytics/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        required_fields = [
            'success_prediction', 'risk_factors', 'performance_trend',
            'attendance_rate', 'payment_status', 'engagement_score'
        ]

        for field in required_fields:
            self.assertIn(field, data)

        # Validate data types
        self.assertIsInstance(data['success_prediction'], (int, float))
        self.assertIsInstance(data['risk_factors'], list)
        self.assertIsInstance(data['attendance_rate'], (int, float))

    def test_student_timeline(self):
        """Test student timeline endpoint."""
        url = f'/api/v2/students/{self.student.unique_id}/timeline/'
        response = self.client.get(url, {
            'page': 1,
            'page_size': 20,
            'event_types': ['enrollment', 'payment']
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('events', data)
        self.assertIn('total_count', data)
        self.assertIn('page', data)
        self.assertIn('has_next', data)

        # Check event structure
        if data['events']:
            event = data['events'][0]
            self.assertIn('type', event)
            self.assertIn('description', event)
            self.assertIn('timestamp', event)

    def test_bulk_student_actions(self):
        """Test bulk student actions endpoint."""
        url = '/api/v2/students/bulk-actions/'
        payload = {
            'action': 'update_status',
            'target_ids': [str(self.student.unique_id)],
            'parameters': {
                'status': 'active'
            },
            'dry_run': True
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('success_count', data)
        self.assertIn('failure_count', data)
        self.assertIn('total_count', data)
        self.assertEqual(data['total_count'], 1)

    def test_photo_upload(self):
        """Test student photo upload."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a mock image file
        image_content = b'fake_image_content'
        image_file = SimpleUploadedFile(
            "test_photo.jpg",
            image_content,
            content_type="image/jpeg"
        )

        url = f'/api/v2/students/{self.student.unique_id}/photos/upload/'
        response = self.client.post(url, {
            'photo': image_file,
            'is_primary': True
        }, format='multipart')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('photo_id', data)
        self.assertIn('url', data)
        self.assertIn('is_primary', data)
        self.assertIn('uploaded_at', data)


class AcademicAPIv2Tests(BaseAPIv2TestCase):
    """Test suite for enhanced academic API endpoints."""

    def setUp(self):
        super().setUp()

        # Create class header and assignment
        self.class_header = ClassHeader.objects.create(
            course=self.course,
            instructor=None,  # Will be set if instructor model exists
            term=None  # Will be set if term model exists
        )

        self.assignment = Assignment.objects.create(
            class_header=self.class_header,
            name='Midterm Exam',
            assignment_type='exam',
            max_score=100,
            weight=0.3
        )

        self.enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status='enrolled'
        )

    def test_grade_spreadsheet(self):
        """Test grade spreadsheet endpoint."""
        url = f'/api/v2/academics/grades/spreadsheet/{self.class_header.unique_id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        required_fields = [
            'class_id', 'assignments', 'students', 'grades', 'metadata'
        ]

        for field in required_fields:
            self.assertIn(field, data)

        # Check structure
        self.assertIsInstance(data['assignments'], list)
        self.assertIsInstance(data['students'], list)
        self.assertIsInstance(data['grades'], list)

        # Check metadata
        metadata = data['metadata']
        self.assertIn('class_name', metadata)
        self.assertIn('total_students', metadata)
        self.assertIn('completion_rate', metadata)

    def test_bulk_grade_update(self):
        """Test bulk grade update endpoint."""
        url = f'/api/v2/academics/grades/spreadsheet/{self.class_header.unique_id}/bulk-update/'
        payload = [
            {
                'student_id': str(self.student.unique_id),
                'assignment_id': str(self.assignment.unique_id),
                'score': 85.5,
                'notes': 'Good work',
                'last_modified': datetime.now().isoformat()
            }
        ]

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('success_count', data)
        self.assertIn('failure_count', data)
        self.assertIn('total_count', data)

    def test_schedule_conflicts(self):
        """Test schedule conflict detection."""
        url = '/api/v2/academics/schedule/conflicts/'
        response = self.client.get(url, {
            'term_id': 'some-term-id'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

        # If conflicts exist, check structure
        if data:
            conflict = data[0]
            self.assertIn('type', conflict)
            self.assertIn('severity', conflict)
            self.assertIn('message', conflict)
            self.assertIn('affected_items', conflict)
            self.assertIn('suggestions', conflict)

    def test_transcript_generation(self):
        """Test transcript generation."""
        url = f'/api/v2/academics/transcripts/generate/{self.student.unique_id}/'
        response = self.client.get(url, {
            'template': 'official',
            'include_unofficial': False
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('transcript_data', data)
        self.assertIn('download_url', data)
        self.assertIn('generated_at', data)

    def test_qr_attendance(self):
        """Test QR code attendance processing."""
        url = '/api/v2/academics/attendance/qr-scan/'
        payload = {
            'qr_data': f'{self.class_header.unique_id}:{self.student.unique_id}:2023-12-01T10:00:00',
            'location': 'Room 101',
            'timestamp': datetime.now().isoformat()
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('message', data)
        self.assertIn('status', data)
        self.assertIn('student_name', data)
        self.assertIn('class_name', data)

    def test_prerequisite_chain(self):
        """Test course prerequisite chain."""
        url = f'/api/v2/academics/courses/{self.course.unique_id}/prerequisites/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('course', data)
        self.assertIn('prerequisite_tree', data)
        self.assertIn('dependent_courses', data)


class FinanceAPIv2Tests(BaseAPIv2TestCase):
    """Test suite for enhanced finance API endpoints."""

    def test_pos_transaction(self):
        """Test POS transaction processing."""
        url = '/api/v2/finance/pos/transaction/'
        payload = {
            'amount': '150.00',
            'payment_method': 'credit_card',
            'student_id': str(self.student.unique_id),
            'description': 'Tuition payment',
            'line_items': [
                {
                    'description': 'Fall 2023 Tuition',
                    'quantity': 1,
                    'unit_price': '150.00',
                    'total_amount': '150.00'
                }
            ]
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('transaction_id', data)
        self.assertIn('payment_id', data)
        self.assertIn('amount', data)
        self.assertIn('status', data)
        self.assertIn('receipt_number', data)

    def test_financial_analytics(self):
        """Test financial analytics dashboard."""
        url = '/api/v2/finance/analytics/dashboard/'
        response = self.client.get(url, {
            'date_range': 30,
            'include_forecasts': True
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        required_fields = [
            'total_revenue', 'pending_payments', 'overdue_amount',
            'scholarship_total', 'payment_trends', 'payment_method_breakdown'
        ]

        for field in required_fields:
            self.assertIn(field, data)

    def test_scholarship_matching(self):
        """Test scholarship matching algorithm."""
        url = f'/api/v2/finance/scholarships/matching/{self.student.unique_id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('student_id', data)
        self.assertIn('total_matches', data)
        self.assertIn('matches', data)
        self.assertIn('student_profile', data)

    def test_payment_reminders(self):
        """Test payment reminder automation."""
        url = '/api/v2/finance/automation/payment-reminders/'
        payload = {
            'student_ids': [str(self.student.unique_id)],
            'reminder_days': [7, 3, 1],
            'template': 'default'
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('success', data)
        self.assertIn('results', data)
        self.assertTrue(data['success'])

    def test_revenue_forecast(self):
        """Test revenue forecasting."""
        url = '/api/v2/finance/reports/revenue-forecast/'
        response = self.client.get(url, {
            'months_ahead': 6,
            'confidence_level': 0.8
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('title', data)
        self.assertIn('type', data)
        self.assertIn('data', data)
        self.assertIn('options', data)


class GraphQLAPITests(BaseAPIv2TestCase):
    """Test suite for GraphQL API endpoints."""

    def test_graphql_health_query(self):
        """Test basic GraphQL health query."""
        query = """
        query {
            health
        }
        """

        response = self.client.post('/graphql/', {
            'query': query
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('errors', data)
        self.assertIn('data', data)
        self.assertEqual(data['data']['health'], 'GraphQL API is healthy')

    def test_graphql_dashboard_metrics(self):
        """Test GraphQL dashboard metrics query."""
        query = """
        query DashboardMetrics($dateRange: Int!) {
            dashboardMetrics(dateRangeDays: $dateRange) {
                studentMetrics {
                    totalCount { value label trend }
                    atRiskCount { value label trend }
                }
                academicMetrics {
                    gradesEntered
                    attendanceRate
                }
                financialMetrics {
                    totalRevenue { value label }
                    pendingPayments { value label }
                }
                lastUpdated
            }
        }
        """

        response = self.client.post('/graphql/', {
            'query': query,
            'variables': {'dateRange': 30}
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('errors', data)
        self.assertIn('data', data)

        metrics = data['data']['dashboardMetrics']
        self.assertIn('studentMetrics', metrics)
        self.assertIn('academicMetrics', metrics)
        self.assertIn('financialMetrics', metrics)

    def test_graphql_student_query(self):
        """Test GraphQL student query."""
        query = """
        query GetStudent($studentId: ID!) {
            student(studentId: $studentId) {
                uniqueId
                studentId
                person {
                    fullName
                    email
                }
                analytics {
                    successPrediction
                    riskFactors
                    attendanceRate
                }
            }
        }
        """

        response = self.client.post('/graphql/', {
            'query': query,
            'variables': {'studentId': str(self.student.unique_id)}
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('errors', data)
        self.assertIn('data', data)

        if data['data']['student']:  # Student found
            student = data['data']['student']
            self.assertIn('uniqueId', student)
            self.assertIn('studentId', student)
            self.assertIn('person', student)

    def test_graphql_grade_mutation(self):
        """Test GraphQL grade update mutation."""
        mutation = """
        mutation UpdateGrade($gradeUpdate: GradeUpdateInput!) {
            updateGrade(gradeUpdate: $gradeUpdate) {
                success
                message
                grade {
                    uniqueId
                    score
                }
            }
        }
        """

        variables = {
            'gradeUpdate': {
                'studentId': str(self.student.unique_id),
                'assignmentId': str(self.assignment.unique_id) if hasattr(self, 'assignment') else 'test-id',
                'score': 85.5,
                'notes': 'Good work'
            }
        }

        response = self.client.post('/graphql/', {
            'query': mutation,
            'variables': variables
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('errors', data)
        self.assertIn('data', data)

        result = data['data']['updateGrade']
        self.assertIn('success', result)
        self.assertIn('message', result)


class WebSocketTests(TransactionTestCase):
    """Test suite for WebSocket functionality."""

    async def test_grade_entry_collaboration(self):
        """Test collaborative grade entry WebSocket."""
        communicator = WebsocketCommunicator(
            GradeEntryCollaborationConsumer.as_asgi(),
            "ws/grades/live-entry/test-class-id/"
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Test sending a grade update
        await communicator.send_json_to({
            'type': 'grade_update',
            'student_id': 'test-student-id',
            'assignment_id': 'test-assignment-id',
            'value': 85.5,
            'field_name': 'score'
        })

        # Should receive the update back
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'grade_entry_update')
        self.assertEqual(response['value'], 85.5)

        await communicator.disconnect()

    async def test_field_locking(self):
        """Test field locking in collaborative editing."""
        communicator = WebsocketCommunicator(
            GradeEntryCollaborationConsumer.as_asgi(),
            "ws/grades/live-entry/test-class-id/"
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Test field lock
        await communicator.send_json_to({
            'type': 'field_lock',
            'student_id': 'test-student-id',
            'assignment_id': 'test-assignment-id',
            'field_name': 'score'
        })

        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'field_locked')

        # Test field unlock
        await communicator.send_json_to({
            'type': 'field_unlock',
            'student_id': 'test-student-id',
            'assignment_id': 'test-assignment-id',
            'field_name': 'score'
        })

        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'field_unlocked')

        await communicator.disconnect()


class CacheTests(BaseAPIv2TestCase):
    """Test suite for caching functionality."""

    def test_student_analytics_caching(self):
        """Test student analytics caching."""
        from config.cache_strategies import StudentCacheStrategy

        student_id = str(self.student.unique_id)

        # First call should miss cache
        analytics = StudentCacheStrategy.get_student_analytics(student_id)
        self.assertIsNone(analytics)

        # Set cache
        test_analytics = {
            'success_prediction': 0.85,
            'risk_factors': ['low_attendance'],
            'attendance_rate': 0.87
        }
        StudentCacheStrategy.set_student_analytics(student_id, test_analytics)

        # Second call should hit cache
        cached_analytics = StudentCacheStrategy.get_student_analytics(student_id)
        self.assertEqual(cached_analytics, test_analytics)

        # Invalidate cache
        StudentCacheStrategy.invalidate_student_analytics(student_id)
        invalidated_analytics = StudentCacheStrategy.get_student_analytics(student_id)
        self.assertIsNone(invalidated_analytics)

    def test_dashboard_metrics_caching(self):
        """Test dashboard metrics caching."""
        from config.cache_strategies import DashboardCacheStrategy

        # Test cache miss and set
        metrics = DashboardCacheStrategy.get_dashboard_metrics(30)
        self.assertIsNone(metrics)

        test_metrics = {
            'student_count': 1247,
            'revenue': 125670.50
        }
        DashboardCacheStrategy.set_dashboard_metrics(30, test_metrics)

        # Test cache hit
        cached_metrics = DashboardCacheStrategy.get_dashboard_metrics(30)
        self.assertEqual(cached_metrics, test_metrics)

    def test_api_endpoint_caching(self):
        """Test that API endpoints use caching appropriately."""
        # Make first request
        url = f'/api/v2/students/{self.student.unique_id}/analytics/'
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)

        # Make second request (should hit cache)
        with patch('apps.people.models.StudentProfile.objects.get') as mock_get:
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, 200)
            # Database should not be hit due to caching
            mock_get.assert_not_called()


class PerformanceTests(BaseAPIv2TestCase):
    """Test suite for API performance."""

    def test_student_search_performance(self):
        """Test student search response time."""
        import time

        url = '/api/v2/students/search/'
        start_time = time.time()

        response = self.client.get(url, {
            'query': 'john',
            'page': 1,
            'page_size': 25
        })

        end_time = time.time()
        response_time = end_time - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 1.0, "Search should complete within 1 second")

    def test_dashboard_metrics_performance(self):
        """Test dashboard metrics response time."""
        import time

        url = '/api/v2/analytics/dashboard/metrics/'
        start_time = time.time()

        response = self.client.get(url, {
            'date_range_days': 30
        })

        end_time = time.time()
        response_time = end_time - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 2.0, "Dashboard metrics should complete within 2 seconds")

    def test_bulk_operations_performance(self):
        """Test bulk operations performance."""
        import time

        url = '/api/v2/students/bulk-actions/'
        payload = {
            'action': 'update_status',
            'target_ids': [str(self.student.unique_id)] * 10,  # 10 students
            'parameters': {'status': 'active'},
            'dry_run': True
        }

        start_time = time.time()
        response = self.client.post(url, payload, format='json')
        end_time = time.time()
        response_time = end_time - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 3.0, "Bulk operations should complete within 3 seconds")


class SecurityTests(BaseAPIv2TestCase):
    """Test suite for API security."""

    def test_unauthenticated_access(self):
        """Test that unauthenticated requests are rejected."""
        # Remove authentication
        self.client.credentials()

        url = '/api/v2/students/search/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_invalid_token(self):
        """Test that invalid tokens are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token')

        url = '/api/v2/students/search/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_sql_injection_protection(self):
        """Test protection against SQL injection."""
        url = '/api/v2/students/search/'
        response = self.client.get(url, {
            'query': "'; DROP TABLE students; --"
        })

        # Should not cause an error and should return safely
        self.assertIn(response.status_code, [200, 400])

    def test_xss_protection(self):
        """Test protection against XSS attacks."""
        url = '/api/v2/communications/threads/'
        payload = {
            'subject': '<script>alert("xss")</script>',
            'participant_ids': [str(self.student.unique_id)],
            'initial_message': 'Test message'
        }

        response = self.client.post(url, payload, format='json')

        # Should not execute script
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            data = response.json()
            # Script tags should be escaped or removed
            self.assertNotIn('<script>', str(data))


# Test runner configuration
if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])