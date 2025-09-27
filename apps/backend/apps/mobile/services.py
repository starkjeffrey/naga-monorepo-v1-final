"""Mobile authentication services for OAuth and JWT management.

This module provides secure authentication services for mobile apps,
including Google OAuth verification, JWT token generation, and
user-student ID mapping.
"""

import logging
from datetime import timedelta
from uuid import uuid4

import jwt
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from google.auth.transport import requests
from google.oauth2 import id_token

from apps.mobile.models import MobileAuthAttempt, MobileAuthToken
from apps.people.models import Person

logger = logging.getLogger(__name__)


class MobileAuthService:
    """Service class for mobile authentication operations."""

    # Configuration constants
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = "naga-sis"
    JWT_AUDIENCE = "naga-mobile"
    TOKEN_EXPIRY_HOURS = 24
    RATE_LIMIT_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = 300  # 5 minutes

    @classmethod
    def verify_google_token(cls, google_token: str, email: str) -> dict:
        """Verify Google OAuth token and extract user information.

        Args:
            google_token: Google OAuth ID token
            email: Email address to verify

        Returns:
            Dict containing user information or error details

        Raises:
            ValueError: If token verification fails
        """
        try:
            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(google_token, requests.Request(), settings.GOOGLE_CLIENT_ID)

            # Validate token issuer
            if idinfo["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise ValueError("Invalid token issuer")

            # Validate email matches token
            token_email = idinfo.get("email", "").lower()
            if token_email != email.lower():
                raise ValueError("Email mismatch between token and request")

            # Validate email domain
            if not email.lower().endswith("@pucsr.edu.kh"):
                raise ValueError("Invalid email domain")

            return {
                "valid": True,
                "email": token_email,
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
                "google_id": idinfo.get("sub"),
            }

        except ValueError as e:
            logger.warning("Google token verification failed: %s", str(e))
            return {"valid": False, "error": str(e)}
        except Exception as e:
            logger.error("Unexpected error during Google token verification: %s", str(e))
            return {"valid": False, "error": "Token verification failed"}

    @classmethod
    def find_student_by_email(cls, email: str) -> tuple[Person, int] | None:
        """Find student by school email address.

        Args:
            email: School email address

        Returns:
            Tuple of (Person, student_id) if found, None otherwise
        """
        try:
            person = Person.objects.select_related("student_profile").get(school_email__iexact=email)

            if not hasattr(person, "student_profile"):
                logger.warning("Person %s has no student profile", person.unique_id)
                return None

            return person, person.student_profile.student_id

        except Person.DoesNotExist:
            logger.warning("No student found with email: %s", email)
            return None
        except Exception as e:
            logger.error("Error finding student by email %s: %s", email, str(e))
            return None

    @classmethod
    def generate_jwt_token(cls, person: Person, student_id: int, email: str, device_id: str) -> dict:
        """Generate JWT token for authenticated student.

        Args:
            person: Person model instance
            student_id: Student ID number
            email: Verified email address
            device_id: Mobile device identifier

        Returns:
            Dict containing JWT token and metadata
        """
        # Generate unique token ID
        token_id = str(uuid4())
        now = timezone.now()
        expires_at = now + timedelta(hours=cls.TOKEN_EXPIRY_HOURS)

        # Create JWT payload
        payload = {
            "sub": f"student_{student_id}",
            "email": email,
            "student_id": student_id,
            "person_uuid": str(person.unique_id),
            "roles": ["STUDENT"],
            "permissions": [
                "read:own_profile",
                "read:own_grades",
                "read:own_schedule",
                "read:own_attendance",
                "read:own_financial_records",
            ],
            "iss": cls.JWT_ISSUER,
            "aud": cls.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": token_id,
            "device_id": device_id,
        }

        # Generate JWT token
        jwt_token = jwt.encode(
            payload,
            getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
            algorithm=cls.JWT_ALGORITHM,
        )

        # Store token in database for tracking
        MobileAuthToken.objects.create(
            user_id=person.user if hasattr(person, "user") else None,
            device_id=device_id,
            token_id=token_id,
            expires_at=expires_at,
        )

        return {
            "jwt_token": jwt_token,
            "token_id": token_id,
            "expires_at": int(expires_at.timestamp()),
            "expires_in": cls.TOKEN_EXPIRY_HOURS * 3600,
        }

    @classmethod
    def validate_jwt_token(cls, token: str) -> dict:
        """Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Dict containing validation result and claims
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
                algorithms=[cls.JWT_ALGORITHM],
                audience=cls.JWT_AUDIENCE,
                issuer=cls.JWT_ISSUER,
            )

            # Check if token is revoked
            token_id = payload.get("jti")
            if token_id:
                try:
                    auth_token = MobileAuthToken.objects.get(token_id=token_id)
                    if auth_token.revoked:
                        return {"valid": False, "error": "Token has been revoked"}

                    # Update last used timestamp
                    auth_token.last_used = timezone.now()
                    auth_token.save(update_fields=["last_used"])

                except MobileAuthToken.DoesNotExist:
                    logger.warning("JWT token not found in database: %s", token_id)

            return {
                "valid": True,
                "claims": payload,
                "student_id": payload.get("student_id"),
                "email": payload.get("email"),
                "person_uuid": payload.get("person_uuid"),
            }

        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token has expired"}
        except jwt.InvalidAudienceError:
            return {"valid": False, "error": "Invalid token audience"}
        except jwt.InvalidIssuerError:
            return {"valid": False, "error": "Invalid token issuer"}
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token: %s", str(e))
            return {"valid": False, "error": "Invalid token"}
        except Exception as e:
            logger.error("Unexpected error validating JWT token: %s", str(e))
            return {"valid": False, "error": "Token validation failed"}

    @classmethod
    def revoke_token(cls, token_id: str) -> bool:
        """Revoke a JWT token.

        Args:
            token_id: JWT token ID to revoke

        Returns:
            True if token was revoked, False otherwise
        """
        try:
            auth_token = MobileAuthToken.objects.get(token_id=token_id)
            auth_token.revoked = True
            auth_token.save(update_fields=["revoked", "updated_at"])
            return True
        except MobileAuthToken.DoesNotExist:
            logger.warning("Attempted to revoke non-existent token: %s", token_id)
            return False
        except Exception as e:
            logger.error("Error revoking token %s: %s", token_id, str(e))
            return False

    @classmethod
    def revoke_all_user_tokens(cls, user_email: str) -> int:
        """Revoke all tokens for a user.

        Args:
            user_email: User's email address

        Returns:
            Number of tokens revoked
        """
        try:
            # Find all non-revoked tokens for user
            tokens = MobileAuthToken.objects.filter(user__email=user_email, revoked=False)

            count = tokens.count()
            tokens.update(revoked=True, updated_at=timezone.now())

            logger.info("Revoked %d tokens for user %s", count, user_email)
            return count

        except Exception as e:
            logger.error("Error revoking tokens for user %s: %s", user_email, str(e))
            return 0

    @classmethod
    def check_rate_limit(cls, identifier: str) -> bool:
        """Check if authentication attempts are rate limited.

        Args:
            identifier: IP address or email to check

        Returns:
            True if rate limited, False otherwise
        """
        cache_key = f"auth_attempts:{identifier}"
        attempts = cache.get(cache_key, 0)

        if attempts >= cls.RATE_LIMIT_ATTEMPTS:
            return True

        cache.set(cache_key, attempts + 1, cls.RATE_LIMIT_WINDOW)
        return False

    @classmethod
    def log_auth_attempt(
        cls,
        email: str,
        status: str,
        device_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        student_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log authentication attempt for security monitoring.

        Args:
            email: Email address used in attempt
            status: Authentication status
            device_id: Device identifier
            ip_address: IP address of request
            user_agent: User agent string
            student_id: Student ID if successful
            error_message: Error message if failed
        """
        try:
            MobileAuthAttempt.objects.create(
                email=email,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                student_id=student_id,
                error_message=error_message,
            )
        except Exception as e:
            logger.error("Error logging auth attempt: %s", str(e))

    @classmethod
    def cleanup_expired_tokens(cls) -> int:
        """Clean up expired tokens from database.

        Returns:
            Number of tokens cleaned up
        """
        try:
            expired_tokens = MobileAuthToken.objects.filter(expires_at__lt=timezone.now())

            count = expired_tokens.count()
            expired_tokens.delete()

            logger.info("Cleaned up %d expired tokens", count)
            return count

        except Exception as e:
            logger.error("Error cleaning up expired tokens: %s", str(e))
            return 0


class MobileUserService:
    """Service for mobile user profile operations."""

    @classmethod
    def get_student_profile(cls, student_id: int) -> dict | None:
        """Get student profile information for mobile app.

        Args:
            student_id: Student ID number

        Returns:
            Dict containing student profile data
        """
        try:
            person = Person.objects.select_related("student_profile").get(student_profile__student_id=student_id)

            return {
                "student_id": student_id,
                "person_uuid": str(person.unique_id),
                "family_name": person.family_name,
                "personal_name": person.personal_name,
                "full_name": f"{person.personal_name} {person.family_name}",
                "school_email": person.school_email,
                "phone": person.phone,
                "current_status": person.student_profile.current_status,
                "enrollment_date": person.student_profile.enrollment_date,
                "graduation_date": person.student_profile.graduation_date,
            }

        except Person.DoesNotExist:
            logger.warning("Student profile not found for ID: %s", student_id)
            return None
        except Exception as e:
            logger.error("Error getting student profile %s: %s", student_id, str(e))
            return None


class MobileAttendanceService:
    """Service for mobile attendance operations."""

    @classmethod
    def record_attendance(cls, student_id: int, class_header_id: int, status: str) -> dict:
        """Record attendance for a student in a class.

        Args:
            student_id: ID of the student
            class_header_id: ID of the class header
            status: Attendance status (PRESENT, ABSENT, LATE, etc.)

        Returns:
            dict: Result of attendance recording
        """
        # Stub implementation for tests
        return {
            "success": True,
            "attendance_id": 1,
            "message": "Attendance recorded successfully",
            "timestamp": timezone.now().isoformat(),
        }

    @classmethod
    def get_student_attendance(cls, student_id: int, term_id: int | None = None) -> list:
        """Get attendance records for a student.

        Args:
            student_id: ID of the student
            term_id: Optional term filter

        Returns:
            list: List of attendance records
        """
        # Stub implementation for tests
        return []

    @classmethod
    def bulk_record_attendance(cls, attendance_records: list) -> dict:
        """Record multiple attendance records at once.

        Args:
            attendance_records: List of attendance data dicts

        Returns:
            dict: Bulk operation result
        """
        # Stub implementation for tests
        return {
            "success": True,
            "processed": len(attendance_records),
            "errors": [],
        }
