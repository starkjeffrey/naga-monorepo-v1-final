"""Unit tests for common app models.

Tests all models in the common app including:
- Holiday management
- Audit logging
- Base model behaviors
- Utility functions

These tests verify business logic, validation, and model methods in isolation.
"""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from apps.common.models import Holiday
from apps.common.models import SystemAuditLog as AuditLog

# Only import functions that exist in the utils package
from apps.common.utils import get_current_date


@pytest.mark.django_db
class TestHolidayModel:
    """Test Holiday model validation and business logic."""

    @pytest.mark.parametrize(
        "name,date_val,holiday_type,is_academic,should_pass",
        [
            # Valid cases
            ("New Year", date(2024, 1, 1), "PUBLIC", True, True),
            ("Spring Break", date(2024, 3, 15), "ACADEMIC", True, True),
            ("Staff Day", date(2024, 6, 1), "ADMINISTRATIVE", False, True),
            # Invalid cases - past dates should fail
            ("Past Holiday", date(2020, 1, 1), "PUBLIC", True, False),
            # Edge cases
            ("Today Holiday", date.today(), "PUBLIC", True, True),
            ("Tomorrow Holiday", date.today() + timedelta(days=1), "PUBLIC", True, True),
        ],
    )
    def test_holiday_validation(self, name, date_val, holiday_type, is_academic, should_pass):
        """Test holiday model validation with various inputs."""
        from apps.common.models import Holiday

        holiday = Holiday(name=name, date=date_val, holiday_type=holiday_type, is_academic=is_academic)

        if should_pass:
            holiday.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                holiday.full_clean()

    def test_holiday_str_representation(self):
        """Test string representation of Holiday model."""
        holiday = Holiday(name="Khmer New Year", date=date(2024, 4, 13), holiday_type="PUBLIC")
        assert str(holiday) == "Khmer New Year (2024-04-13)"

    def test_holiday_ordering(self):
        """Test that holidays are ordered by date."""
        holiday1 = Holiday.objects.create(name="Holiday 1", date=date(2024, 3, 1), holiday_type="PUBLIC")
        holiday2 = Holiday.objects.create(name="Holiday 2", date=date(2024, 1, 1), holiday_type="PUBLIC")
        holiday3 = Holiday.objects.create(name="Holiday 3", date=date(2024, 2, 1), holiday_type="PUBLIC")

        holidays = Holiday.objects.all()
        assert holidays[0] == holiday2  # January
        assert holidays[1] == holiday3  # February
        assert holidays[2] == holiday1  # March

    @pytest.mark.parametrize(
        "holiday_type,expected_choices",
        [
            ("PUBLIC", True),
            ("ACADEMIC", True),
            ("ADMINISTRATIVE", True),
            ("RELIGIOUS", True),
            ("INVALID_TYPE", False),
        ],
    )
    def test_holiday_type_choices(self, holiday_type, expected_choices):
        """Test that only valid holiday types are accepted."""
        holiday = Holiday(name="Test Holiday", date=date(2024, 12, 25), holiday_type=holiday_type)

        if expected_choices:
            holiday.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                holiday.full_clean()

    def test_holiday_affects_classes(self):
        """Test is_academic flag determines if holiday affects classes."""
        academic_holiday = Holiday.objects.create(
            name="Academic Holiday", date=date(2024, 5, 1), holiday_type="ACADEMIC", is_academic=True
        )

        admin_holiday = Holiday.objects.create(
            name="Admin Holiday", date=date(2024, 5, 2), holiday_type="ADMINISTRATIVE", is_academic=False
        )

        assert academic_holiday.is_academic
        assert not admin_holiday.is_academic

    def test_holiday_date_uniqueness(self):
        """Test that multiple holidays can exist on same date."""
        date_val = date(2024, 12, 25)

        Holiday.objects.create(name="Christmas", date=date_val, holiday_type="RELIGIOUS")

        # Should allow another holiday on same date
        Holiday.objects.create(name="Public Holiday", date=date_val, holiday_type="PUBLIC")

        assert Holiday.objects.filter(date=date_val).count() == 2


@pytest.mark.django_db
class TestAuditLogModel:
    """Test AuditLog model for tracking changes."""

    def test_audit_log_creation(self, user):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user=user,
            action="CREATE",
            model_name="TestModel",
            object_id=123,
            changes={"field": "value"},
            ip_address="127.0.0.1",
            user_agent="TestBrowser/1.0",
        )

        assert log.user == user
        assert log.action == "CREATE"
        assert log.model_name == "TestModel"
        assert log.object_id == "123"
        assert log.changes == {"field": "value"}

    @pytest.mark.parametrize("action", ["CREATE", "UPDATE", "DELETE", "VIEW"])
    def test_audit_log_action_types(self, action, user):
        """Test different action types for audit log."""
        log = AuditLog.objects.create(user=user, action=action, model_name="TestModel", object_id=1)

        assert log.action == action

    def test_audit_log_timestamp(self, user):
        """Test that audit log timestamp is set automatically."""
        with freeze_time("2024-01-15 10:30:00"):
            log = AuditLog.objects.create(user=user, action="CREATE", model_name="TestModel", object_id=1)

            assert log.timestamp.date() == date(2024, 1, 15)
            assert log.timestamp.hour == 10
            assert log.timestamp.minute == 30

    def test_audit_log_without_user(self):
        """Test audit log can be created without user (system actions)."""
        log = AuditLog.objects.create(
            user=None, action="SYSTEM", model_name="CronJob", object_id=1, changes={"status": "completed"}
        )

        assert log.user is None
        assert log.action == "SYSTEM"

    def test_audit_log_large_changes(self):
        """Test audit log with large change dictionary."""
        large_changes = {f"field_{i}": f"value_{i}" * 100 for i in range(100)}

        log = AuditLog.objects.create(action="UPDATE", model_name="TestModel", object_id=1, changes=large_changes)

        assert len(log.changes) == 100

    def test_audit_log_ordering(self):
        """Test audit logs are ordered by timestamp descending."""
        with freeze_time("2024-01-15 10:00:00"):
            log1 = AuditLog.objects.create(action="CREATE", model_name="Model1", object_id=1)

        with freeze_time("2024-01-15 11:00:00"):
            log2 = AuditLog.objects.create(action="UPDATE", model_name="Model2", object_id=2)

        with freeze_time("2024-01-15 09:00:00"):
            log3 = AuditLog.objects.create(action="DELETE", model_name="Model3", object_id=3)

        logs = AuditLog.objects.all()
        assert logs[0] == log2  # Most recent first
        assert logs[1] == log1
        assert logs[2] == log3  # Oldest last


class TestCommonUtils:
    """Test utility functions in common app."""

    # TODO: Implement get_current_academic_year utility function
    # @pytest.mark.parametrize(
    #     "test_date,expected_year",
    #     [
    #         (date(2024, 1, 15), "2023-2024"),  # Spring semester
    #         (date(2024, 9, 1), "2024-2025"),  # Fall semester
    #         (date(2024, 6, 1), "2023-2024"),  # Summer
    #         (date(2024, 8, 31), "2023-2024"),  # End of academic year
    #         (date(2024, 9, 1), "2024-2025"),  # Start of new academic year
    #     ],
    # )
    # def test_get_current_academic_year(self, test_date, expected_year):
    #     """Test academic year calculation for different dates."""
    #     with freeze_time(test_date):
    #         assert get_current_academic_year() == expected_year

    # TODO: Implement calculate_age utility function
    # @pytest.mark.parametrize(
    #     "birth_date,reference_date,expected_age",
    #     [
    #         (date(2000, 1, 1), date(2024, 1, 1), 24),
    #         (date(2000, 1, 1), date(2023, 12, 31), 23),
    #         (date(2000, 12, 31), date(2024, 12, 30), 23),
    #         (date(2000, 12, 31), date(2024, 12, 31), 24),
    #         (date(2004, 2, 29), date(2024, 2, 28), 19),  # Leap year
    #         (date(2004, 2, 29), date(2024, 3, 1), 20),  # Leap year
    #     ],
    # )
    # def test_calculate_age(self, birth_date, reference_date, expected_age):
    #     """Test age calculation with various dates including edge cases."""
    #     with freeze_time(reference_date):
    #         assert calculate_age(birth_date) == expected_age

    # TODO: Implement format_currency utility function
    # @pytest.mark.parametrize(
    #     "amount,currency,expected",
    #     [
    #         (Decimal("1234.56"), "USD", "$1,234.56"),
    #         (Decimal("1234.50"), "USD", "$1,234.50"),
    #         (Decimal("1234"), "USD", "$1,234.00"),
    #         (Decimal("0.99"), "USD", "$0.99"),
    #         (Decimal("-100.50"), "USD", "-$100.50"),
    #         (Decimal("1000000.00"), "USD", "$1,000,000.00"),
    #         (1234.56, "USD", "$1,234.56"),  # Float input
    #         (1234, "USD", "$1,234.00"),  # Integer input
    #     ],
    # )
    # def test_format_currency(self, amount, currency, expected):
    #     """Test currency formatting with various amounts."""
    #     assert format_currency(amount, currency) == expected

    @pytest.mark.parametrize(
        "phone,is_valid",
        [
            ("+855123456789", True),  # Valid Cambodia number
            ("+85512345678", True),  # Valid Cambodia mobile
            ("0123456789", True),  # Local format
            ("+1234567890", True),  # International
            ("123-456-7890", False),  # Invalid format
            ("abc123", False),  # Letters
            ("", False),  # Empty
            (None, False),  # None
            ("+855", False),  # Too short
            ("+8551234567890123", False),  # Too long
        ],
    )
    # TODO: Move validate_phone_number from apps/common/utils.py to utils package
    # def test_validate_phone_number(self, phone, is_valid):
    #     """Test phone number validation."""
    #     if is_valid:
    #         validate_phone_number(phone)  # Should not raise
    #     else:
    #         with pytest.raises(ValidationError):
    #             validate_phone_number(phone)

    # TODO: Implement is_valid_email utility function
    # @pytest.mark.parametrize(
    #     "email,is_valid",
    #     [
    #         ("test@example.com", True),
    #         ("user.full_name@example.co.uk", True),
    #         ("user+tag@example.com", True),
    #         ("user@subdomain.example.com", True),
    #         ("invalid.email", False),
    #         ("@example.com", False),
    #         ("user@", False),
    #         ("user @example.com", False),
    #         ("", False),
    #         (None, False),
    #     ],
    # )
    # def test_is_valid_email(self, email, is_valid):
    #     """Test email validation."""
    #     assert is_valid_email(email) == is_valid

    # TODO: Move generate_unique_code from apps/common/utils.py to utils package
    # def test_generate_unique_code(self):
    #     """Test unique code generation."""
    #     codes = set()
    #     for _ in range(100):
    #         code = generate_unique_code()
    #         assert len(code) == 8  # Default length
    #         assert code.isalnum()
    #         assert code.isupper()
    #         codes.add(code)

    #     # All codes should be unique
    #     assert len(codes) == 100

    # def test_generate_unique_code_with_prefix(self):
    #     """Test unique code generation with prefix."""
    #     code = generate_unique_code(prefix="INV", length=12)
    #     assert code.startswith("INV")
    #     assert len(code) == 12

    @freeze_time("2024-01-15")
    def test_get_current_date(self):
        """Test getting current date."""
        assert get_current_date() == date(2024, 1, 15)


@pytest.mark.django_db
class TestBaseModel:
    """Test BaseModel abstract class functionality."""

    def test_base_model_timestamps(self):
        """Test that BaseModel provides created_at and updated_at."""
        # Create a concrete model that inherits from BaseModel
        from apps.common.models import Holiday  # Using Holiday as it inherits BaseModel

        with freeze_time("2024-01-15 10:00:00"):
            holiday = Holiday.objects.create(name="Test Holiday", date=date(2024, 12, 25), holiday_type="PUBLIC")

            assert holiday.created_at.date() == date(2024, 1, 15)
            assert holiday.updated_at.date() == date(2024, 1, 15)

        # Update the model
        with freeze_time("2024-01-16 10:00:00"):
            holiday.full_name = "Updated Holiday"
            holiday.save()

            assert holiday.created_at.date() == date(2024, 1, 15)  # Unchanged
            assert holiday.updated_at.date() == date(2024, 1, 16)  # Updated

    def test_base_model_soft_delete(self):
        """Test soft delete functionality if implemented."""
        # This would test soft delete if BaseModel implements it
        pass  # Implement based on actual BaseModel implementation


# TODO: Implement validators module and tests
# @pytest.mark.django_db
# class TestCommonValidators:
#     """Test custom validators in common app."""

#     @pytest.mark.parametrize(
#         "value,should_pass",
#         [
#             ("valid_slug", True),
#             ("valid-slug-123", True),
#             ("INVALID", False),  # Uppercase
#             ("invalid slug", False),  # Space
#             ("invalid@slug", False),  # Special char
#             ("", False),  # Empty
#             ("-invalid", False),  # Starts with dash
#             ("invalid-", False),  # Ends with dash
#         ],
#     )
#     def test_slug_validator(self, value, should_pass):
#         """Test slug validation."""
#         from apps.common.validators import validate_slug

#         if should_pass:
#             validate_slug(value)  # Should not raise
#         else:
#             with pytest.raises(ValidationError):
#                 validate_slug(value)

#     @pytest.mark.parametrize(
#         "value,min_val,max_val,should_pass",
#         [
#             (5, 1, 10, True),
#             (1, 1, 10, True),
#             (10, 1, 10, True),
#             (0, 1, 10, False),
#             (11, 1, 10, False),
#             (-5, -10, 0, True),
#             (5.5, 1.0, 10.0, True),
#         ],
#     )
#     def test_range_validator(self, value, min_val, max_val, should_pass):
#         """Test range validation."""
#         from apps.common.validators import validate_range

#         if should_pass:
#             validate_range(value, min_val, max_val)
#         else:
#             with pytest.raises(ValidationError):
#                 validate_range(value, min_val, max_val)
