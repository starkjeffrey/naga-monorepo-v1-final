"""Moodle integration services."""

import logging
import time
from typing import Any

import requests
from django.conf import settings

from .constants import SYNC_SETTINGS
from .exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConfigurationError,
    MoodleTimeoutError,
)
from .models import MoodleAPILog

logger = logging.getLogger(__name__)


class MoodleAPIClient:
    """Low-level Moodle Web Services API client."""

    def __init__(self):
        """Initialize Moodle API client with configuration."""
        if not hasattr(settings, "MOODLE_INTEGRATION"):
            raise MoodleConfigurationError("MOODLE_INTEGRATION not configured in settings")

        self.config = settings.MOODLE_INTEGRATION
        self.base_url = self.config.get("BASE_URL", "").rstrip("/")
        self.token = self.config.get("API_TOKEN", "")
        self.timeout = SYNC_SETTINGS["API_TIMEOUT_SECONDS"]

        if not self.base_url or not self.token:
            raise MoodleConfigurationError("Moodle BASE_URL and API_TOKEN must be configured")

    def call_function(self, function_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Make a call to Moodle Web Services API.

        Args:
            function_name: Moodle WS function name
            parameters: Function parameters

        Returns:
            API response data

        Raises:
            MoodleAPIError: For API communication errors
            MoodleAuthenticationError: For authentication failures
            MoodleTimeoutError: For timeout errors
        """
        start_time = time.time()
        url = f"{self.base_url}/webservice/rest/server.php"

        data = {
            "wstoken": self.token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
            **parameters,
        }

        try:
            response = requests.post(url, data=data, timeout=self.timeout)
            execution_time = int((time.time() - start_time) * 1000)

            # Log API call
            MoodleAPILog.objects.create(
                endpoint=function_name,
                method="POST",
                request_data=parameters,  # Don't log token
                response_data=response.json() if response.content else None,
                status_code=response.status_code,
                execution_time_ms=execution_time,
                error_message="" if response.ok else response.text,
            )

            if not response.ok:
                raise MoodleAPIError(f"HTTP {response.status_code}: {response.text}")

            result = response.json()

            # Check for Moodle-specific errors
            if isinstance(result, dict) and "exception" in result:
                error_msg = result.get("message", "Unknown Moodle error")
                if "Invalid token" in error_msg:
                    raise MoodleAuthenticationError(error_msg)
                raise MoodleAPIError(error_msg)

            return result

        except requests.exceptions.Timeout as e:
            raise MoodleTimeoutError(f"Moodle API timeout after {self.timeout}s") from e
        except requests.exceptions.RequestException as e:
            raise MoodleAPIError(f"Network error: {e}") from e

    def test_connection(self) -> bool:
        """Test connection to Moodle API.

        Returns:
            True if connection successful
        """
        try:
            result = self.call_function("core_webservice_get_site_info", {})
            return "sitename" in result
        except Exception as e:
            logger.error("Moodle connection test failed: %s", e)
            return False


class MoodleUserService:
    """Handle Moodle user management operations."""

    def __init__(self):
        self.api = MoodleAPIClient()

    def create_user(self, person) -> int | None:
        """Create a user in Moodle from SIS Person.

        Args:
            person: Person instance from people app

        Returns:
            Moodle user ID if successful, None otherwise
        """
        # TODO: Implement user creation logic
        # This will map Person fields to Moodle user fields
        logger.info("Creating Moodle user for person %s", person.id)
        return None

    def update_user(self, person, moodle_user_id: int) -> bool:
        """Update existing Moodle user.

        Args:
            person: Person instance
            moodle_user_id: Moodle user ID

        Returns:
            True if successful
        """
        # TODO: Implement user update logic
        logger.info("Updating Moodle user %s for person %s", moodle_user_id, person.id)
        return False

    def sync_person_to_moodle(self, person) -> bool:
        """Sync SIS person to Moodle (create or update).

        Args:
            person: Person instance

        Returns:
            True if successful
        """
        # TODO: Implement full person sync logic
        logger.info("Syncing person %s to Moodle", person.id)
        return False


class MoodleCourseService:
    """Handle Moodle course management operations."""

    def __init__(self):
        self.api = MoodleAPIClient()

    def create_course(self, course) -> int | None:
        """Create a course in Moodle from SIS Course.

        Args:
            course: Course instance from curriculum app

        Returns:
            Moodle course ID if successful
        """
        # TODO: Implement course creation logic
        logger.info("Creating Moodle course for SIS course %s", course.id)
        return None

    def sync_course_to_moodle(self, course) -> bool:
        """Sync SIS course to Moodle.

        Args:
            course: Course instance

        Returns:
            True if successful
        """
        # TODO: Implement course sync logic
        logger.info("Syncing course %s to Moodle", course.id)
        return False


class MoodleEnrollmentService:
    """Handle Moodle enrollment operations."""

    def __init__(self):
        self.api = MoodleAPIClient()

    def enroll_student(self, enrollment) -> bool:
        """Enroll student in Moodle course.

        Args:
            enrollment: Enrollment instance from enrollment app

        Returns:
            True if successful
        """
        # TODO: Implement enrollment logic
        logger.info("Enrolling student in Moodle for enrollment %s", enrollment.id)
        return False

    def unenroll_student(self, enrollment) -> bool:
        """Unenroll student from Moodle course.

        Args:
            enrollment: Enrollment instance

        Returns:
            True if successful
        """
        # TODO: Implement unenrollment logic
        logger.info("Unenrolling student from Moodle for enrollment %s", enrollment.id)
        return False


class MoodleGradeService:
    """Handle Moodle grade synchronization (future implementation)."""

    def __init__(self):
        self.api = MoodleAPIClient()

    def sync_grades_to_moodle(self, class_instance_id: int) -> bool:
        """Sync SIS grades to Moodle.

        Args:
            class_instance_id: Class instance ID

        Returns:
            True if successful
        """
        # TODO: Implement when grading app exists
        logger.info("Syncing grades to Moodle for class %s", class_instance_id)
        return False

    def import_grades_from_moodle(self, class_instance_id: int) -> bool:
        """Import grades from Moodle to SIS.

        Args:
            class_instance_id: Class instance ID

        Returns:
            True if successful
        """
        # TODO: Implement when grading app exists
        logger.info("Importing grades from Moodle for class %s", class_instance_id)
        return False
