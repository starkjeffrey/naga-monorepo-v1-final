"""Moodle integration exceptions."""


class MoodleError(Exception):
    """Base exception for Moodle integration errors."""

    def __init__(self, message, error_code=None, details=None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class MoodleAPIError(MoodleError):
    """Exception for Moodle API communication errors."""

    pass


class MoodleAuthenticationError(MoodleAPIError):
    """Exception for Moodle authentication failures."""

    pass


class MoodleValidationError(MoodleAPIError):
    """Exception for Moodle data validation errors."""

    pass


class MoodleConflictError(MoodleAPIError):
    """Exception for Moodle data conflicts (e.g., duplicate users)."""

    pass


class MoodleSyncError(MoodleError):
    """Exception for synchronization failures."""

    pass


class MoodleConfigurationError(MoodleError):
    """Exception for Moodle configuration issues."""

    pass


class MoodleTimeoutError(MoodleAPIError):
    """Exception for Moodle API timeout errors."""

    pass
