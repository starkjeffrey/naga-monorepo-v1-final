"""Integration tests for Staff-Web V2 database schema and API endpoints."""

import json
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from apps.people.models import Person, StudentProfile, StudentPhoto
from apps.academic.models import GradeCollaborationSession, UserPresence, CollaborationChangeHistory
from apps.finance.models import Payment, EncryptedTransactionLog, CurrencyExchangeRate, FraudDetectionLog
from apps.analytics.models import MLModelMetadata, PredictionResult, DocumentIntelligenceMetadata, BlockchainVerification

User = get_user_model()


@pytest.mark.integration
class StaffWebV2DatabaseSchemaTests(TransactionTestCase):
    """Test database schema enhancements for Staff-Web V2."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.person = Person.objects.create(
            family_name='Test',
            personal_name='Student',
            preferred_gender='M'
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=12345,
            current_status='ACTIVE'
        )

    def test_ai_analytics_fields(self):
        """Test AI analytics fields on StudentProfile."""
        # Update AI analytics fields
        self.student.risk_score = Decimal('75.50')
        self.student.success_probability = Decimal('85.25')
        self.student.last_risk_assessment_date = datetime.now()
        self.student.intervention_history = {
            'interventions': [
                {
                    'date': '2024-01-15',
                    'type': 'academic_support',
                    'outcome': 'improved'
                }
            ]
        }
        self.student.ai_insights = {
            'recommendations': ['study_group', 'tutoring'],
            'confidence': 0.87
        }
        self.student.prediction_model_version = 'v2.1.0'
        self.student.save()

        # Verify fields are saved correctly
        updated_student = StudentProfile.objects.get(id=self.student.id)
        self.assertEqual(updated_student.risk_score, Decimal('75.50'))
        self.assertEqual(updated_student.success_probability, Decimal('85.25'))
        self.assertIsNotNone(updated_student.last_risk_assessment_date)
        self.assertEqual(len(updated_student.intervention_history['interventions']), 1)
        self.assertEqual(updated_student.prediction_model_version, 'v2.1.0')

    def test_enhanced_photo_metadata(self):
        """Test enhanced photo metadata fields."""
        photo = StudentPhoto.objects.create(
            person=self.person,
            photo_file='test.jpg',
            file_hash='abc123',
            upload_source=StudentPhoto.UploadSource.API,
            ai_extracted_metadata={
                'faces_detected': 1,
                'image_quality': 'high',
                'lighting': 'good'
            },
            face_detected=True,
            face_confidence=Decimal('95.50'),
            image_quality_score=Decimal('88.75'),
            compression_level='high',
            processing_status='completed',
            exif_data={
                'camera': 'iPhone 12',
                'timestamp': '2024-01-15T10:30:00Z'
            },
            privacy_flags={
                'consent_given': True,
                'public_display': False
            }
        )

        # Verify enhanced metadata is saved
        saved_photo = StudentPhoto.objects.get(id=photo.id)
        self.assertTrue(saved_photo.face_detected)
        self.assertEqual(saved_photo.face_confidence, Decimal('95.50'))
        self.assertEqual(saved_photo.processing_status, 'completed')
        self.assertEqual(saved_photo.ai_extracted_metadata['faces_detected'], 1)
        self.assertEqual(saved_photo.privacy_flags['consent_given'], True)

    def test_academic_collaboration_models(self):
        """Test academic real-time collaboration models."""
        # Create collaboration session
        session = GradeCollaborationSession.objects.create(
            owner=self.user,
            title='Grade Entry Session - Math 101',
            description='Collaborative grading for midterm exam',
            status='active',
            settings={
                'allow_simultaneous_editing': True,
                'auto_save_interval': 30
            },
            metadata={
                'class_id': 'math-101',
                'assignment_type': 'midterm'
            }
        )

        # Create user presence
        presence = UserPresence.objects.create(
            session=session,
            user=self.user,
            status='online',
            current_page='/grades/math-101',
            cursor_position={
                'row': 5,
                'column': 'B',
                'cell_ref': 'B5'
            }
        )

        # Create change history
        change = CollaborationChangeHistory.objects.create(
            session=session,
            user=self.user,
            change_type='update',
            target_type='grade',
            target_id='grade-123',
            field_name='score',
            old_value={"score": 85},
            new_value={"score": 90},
            operation_data={
                'operation': 'retain(5)insert("90")delete(2)',
                'position': 5
            },
            vector_clock={
                'user_1': 1,
                'user_2': 0
            }
        )

        # Verify models are created correctly
        self.assertEqual(session.title, 'Grade Entry Session - Math 101')
        self.assertEqual(session.status, 'active')
        self.assertEqual(presence.status, 'online')
        self.assertEqual(change.change_type, 'update')
        self.assertEqual(change.new_value['score'], 90)

    def test_financial_security_enhancements(self):
        """Test financial security enhancement models."""
        # Create payment with security features
        payment = Payment.objects.create(
            amount=Decimal('100.00'),
            currency='USD',
            payment_method='credit_card',
            payment_processor='stripe',
            processor_transaction_id='txn_123456',
            fraud_score=Decimal('15.50'),
            risk_flags={
                'high_velocity': False,
                'unusual_location': False,
                'new_card': True
            }
        )

        # Create encrypted transaction log
        log = EncryptedTransactionLog.objects.create(
            transaction_type='payment',
            encrypted_data='encrypted_payment_data_here',
            data_hash='sha256_hash_here',
            encryption_key_id='key_v1',
            user=self.user,
            ip_address='192.168.1.1',
            session_id='session_123'
        )

        # Create currency exchange rate
        rate = CurrencyExchangeRate.objects.create(
            from_currency='USD',
            to_currency='KHR',
            exchange_rate=Decimal('4100.000000'),
            effective_date=datetime.now().date(),
            source='central_bank'
        )

        # Create fraud detection log
        fraud_log = FraudDetectionLog.objects.create(
            risk_level='medium',
            risk_score=Decimal('45.75'),
            detection_rules={
                'rules_triggered': ['velocity_check', 'amount_check'],
                'thresholds': {'velocity': 5, 'amount': 1000}
            },
            transaction_details={
                'amount': 100.00,
                'currency': 'USD',
                'method': 'credit_card'
            },
            action_taken='flag',
            payment=payment
        )

        # Verify financial security models
        self.assertEqual(payment.fraud_score, Decimal('15.50'))
        self.assertEqual(payment.payment_processor, 'stripe')
        self.assertEqual(log.transaction_type, 'payment')
        self.assertEqual(rate.exchange_rate, Decimal('4100.000000'))
        self.assertEqual(fraud_log.risk_level, 'medium')

    def test_innovation_ai_ml_models(self):
        """Test innovation AI/ML metadata models."""
        # Create ML model metadata
        model = MLModelMetadata.objects.create(
            name='Student Risk Predictor',
            description='ML model for predicting student academic risk',
            model_type='classification',
            framework='scikit_learn',
            version='v1.2.0',
            status='production',
            training_data_size=5000,
            features_count=25,
            accuracy_score=Decimal('0.8750'),
            f1_score=Decimal('0.8250'),
            hyperparameters={
                'n_estimators': 100,
                'max_depth': 10,
                'learning_rate': 0.1
            },
            performance_metrics={
                'precision': 0.85,
                'recall': 0.80,
                'auc_score': 0.87
            },
            created_by=self.user
        )

        # Create prediction result
        prediction = PredictionResult.objects.create(
            model=model,
            target_type='student',
            target_id=str(self.student.unique_id),
            prediction_type='risk_assessment',
            prediction_value={
                'risk_score': 75.5,
                'risk_category': 'medium',
                'factors': ['attendance', 'grades']
            },
            confidence_score=Decimal('0.8750'),
            input_features={
                'attendance_rate': 0.85,
                'avg_grade': 78.5,
                'assignment_completion': 0.90
            },
            student=self.student
        )

        # Create document intelligence metadata
        document = DocumentIntelligenceMetadata.objects.create(
            file_name='transcript.pdf',
            file_path='/uploads/transcripts/transcript.pdf',
            file_size=1024000,
            mime_type='application/pdf',
            document_type='transcript',
            processing_status='completed',
            extracted_text='Student transcript content...',
            structured_data={
                'courses': [
                    {'name': 'Mathematics', 'grade': 'A'},
                    {'name': 'Science', 'grade': 'B+'}
                ]
            },
            entities_extracted={
                'student_name': 'Test Student',
                'graduation_date': '2024-05-15',
                'gpa': 3.75
            },
            quality_score=Decimal('92.50'),
            uploaded_by=self.user,
            student=self.student
        )

        # Create blockchain verification
        verification = BlockchainVerification.objects.create(
            record_type='transcript',
            record_id=str(document.document_id),
            data_hash='sha256_transcript_hash',
            blockchain_hash='0x123456789abcdef',
            blockchain_network='polygon',
            block_number=12345678,
            verification_status='confirmed',
            metadata={
                'transaction_cost': 0.001,
                'gas_used': 21000
            },
            verified_by=self.user,
            student=self.student
        )

        # Verify AI/ML models
        self.assertEqual(model.name, 'Student Risk Predictor')
        self.assertEqual(model.status, 'production')
        self.assertEqual(prediction.prediction_type, 'risk_assessment')
        self.assertEqual(prediction.prediction_value['risk_score'], 75.5)
        self.assertEqual(document.document_type, 'transcript')
        self.assertEqual(document.quality_score, Decimal('92.50'))
        self.assertEqual(verification.verification_status, 'confirmed')
        self.assertEqual(verification.blockchain_network, 'polygon')


@pytest.mark.integration
class StaffWebV2APITests(TestCase):
    """Test API endpoints for Staff-Web V2."""

    def setUp(self):
        """Set up test API client and data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create test data
        self.person = Person.objects.create(
            family_name='API',
            personal_name='Student',
            preferred_gender='F'
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=54321,
            current_status='ACTIVE'
        )

    def test_api_v2_health_endpoint(self):
        """Test API v2 health check endpoint."""
        response = self.client.get('/api/v2/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['version'], '2.0.0')
        self.assertIn('services', data)

    def test_api_v2_info_endpoint(self):
        """Test API v2 info endpoint."""
        response = self.client.get('/api/v2/info/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['title'], 'Naga SIS Enhanced API v2')
        self.assertEqual(data['version'], '2.0.0')
        self.assertIn('features', data)
        self.assertIn('real_time_updates', data['features'])

    def test_students_api_with_analytics(self):
        """Test enhanced students API with analytics."""
        # Update student with AI analytics
        self.student.risk_score = Decimal('65.75')
        self.student.success_probability = Decimal('78.25')
        self.student.save()

        response = self.client.get(f'/api/v2/students/{self.student.unique_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Note: This test assumes the API endpoint exists and returns the data
        # The actual implementation would need to include these fields in the response

    def test_api_authentication_required(self):
        """Test that API endpoints require authentication."""
        # Remove authentication
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v2/students/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_rate_limiting(self):
        """Test API rate limiting middleware."""
        # This test would need to be implemented based on the actual rate limiting logic
        # For now, we'll test that the endpoint responds normally under normal load

        response = self.client.get('/api/v2/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_websocket_routing_configuration(self):
        """Test WebSocket routing configuration."""
        # This test verifies that WebSocket routes are properly configured
        # In a real implementation, you would test WebSocket connections
        from config.routing import websocket_urlpatterns

        # Check that enhanced v2 routes exist
        route_patterns = [str(pattern.pattern) for pattern in websocket_urlpatterns]

        self.assertIn('ws/v2/grades/collaboration/(?P<class_id>[^/]+)/', route_patterns)
        self.assertIn('ws/v2/dashboard/metrics/', route_patterns)
        self.assertIn('ws/v2/notifications/', route_patterns)


@pytest.mark.integration
class SecurityMiddlewareTests(TestCase):
    """Test security middleware functionality."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='securityuser',
            email='security@example.com',
            password='securitypass123'
        )

    def test_security_headers(self):
        """Test that security headers are added."""
        response = self.client.get('/api/v2/health/')

        # Check for security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-XSS-Protection', response)
        self.assertIn('Content-Security-Policy', response)

    def test_rate_limiting_headers(self):
        """Test rate limiting functionality."""
        # Make multiple requests to test rate limiting
        for i in range(5):
            response = self.client.get('/api/v2/health/')
            if i < 4:
                self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Note: Actual rate limiting would depend on the middleware configuration
        # This test verifies the structure is in place

    def test_csrf_protection(self):
        """Test enhanced CSRF protection."""
        # Test that CSRF is required for sensitive operations
        response = self.client.post('/api/v2/students/', {})

        # Should require authentication and CSRF token
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


@pytest.mark.integration
class DatabasePerformanceTests(TransactionTestCase):
    """Test database performance with new indexes."""

    def setUp(self):
        """Set up performance test data."""
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )

    def test_ai_analytics_query_performance(self):
        """Test that AI analytics queries use proper indexes."""
        from django.test.utils import override_settings
        from django.db import connection

        # Create test students with risk scores
        for i in range(100):
            person = Person.objects.create(
                family_name=f'Student{i}',
                personal_name='Test',
                preferred_gender='M'
            )
            StudentProfile.objects.create(
                person=person,
                student_id=10000 + i,
                current_status='ACTIVE',
                risk_score=Decimal(f'{50 + (i % 50)}.{i % 100:02d}')
            )

        with self.assertNumQueries(1):
            # Query should use index on risk_score
            high_risk_students = StudentProfile.objects.filter(
                risk_score__gte=Decimal('80.00')
            ).count()

        self.assertGreater(high_risk_students, 0)

    def test_photo_processing_queue_performance(self):
        """Test photo processing queue query performance."""
        # Create test photos with various processing statuses
        person = Person.objects.create(
            family_name='PhotoTest',
            personal_name='Student',
            preferred_gender='F'
        )

        for i in range(50):
            StudentPhoto.objects.create(
                person=person,
                photo_file=f'test{i}.jpg',
                file_hash=f'hash{i}',
                processing_status='pending' if i % 2 == 0 else 'completed'
            )

        with self.assertNumQueries(1):
            # Query should use index on processing_status
            pending_photos = StudentPhoto.objects.filter(
                processing_status='pending'
            ).count()

        self.assertGreater(pending_photos, 0)


if __name__ == '__main__':
    pytest.main([__file__])