"""Constants for the people app.

This module centralizes hardcoded values and thresholds to improve
maintainability and reduce magic numbers throughout the codebase.
"""

# Age validation constants
MIN_AGE_APPLY = 12  # Minimum age for application
MAX_AGE_APPLY = 65  # Maximum age for application
MAX_AGE_YEARS = 120  # Maximum reasonable age (for validation)

# Phone number validation constants
MIN_PHONE_DIGITS = 8  # Minimum phone number length
MAX_PHONE_DIGITS = 15  # Maximum phone number length

# Duplicate detection confidence thresholds
EXACT_NAME_MATCH_CONFIDENCE = 0.95  # Confidence for exact name matches
PHONE_MATCH_CONFIDENCE = 0.80  # Confidence for phone number matches
EMAIL_MATCH_CONFIDENCE = 0.90  # Confidence for email matches
SIMILAR_NAME_THRESHOLD = 0.85  # Threshold for similar name matching
FUZZY_MATCH_CONFIDENCE = 0.70  # Confidence for fuzzy/similar matches

# Name similarity calculation weights
NAME_SIMILARITY_WEIGHT = 0.6  # Weight for name similarity in overall score
PHONE_MATCH_WEIGHT = 0.3  # Weight for phone match in overall score
EMAIL_MATCH_WEIGHT = 0.1  # Weight for email match in overall score

# Student ID generation constants
STUDENT_ID_START = 100001  # Starting student ID for new installations
MAX_STUDENT_ID_DIGITS = 10  # Maximum number of digits in student ID

# Administrative limits
MAX_LEVEL_SKIP = 3  # Maximum levels a student can skip

# Test constants
TEST_STUDENT_ID = 12345  # Test student ID for unit tests

# Name validation constants
NAME_VALIDATION_REGEX = r"^[a-zA-Z\s\-']+$"  # Basic ASCII name validation
# For international support, consider: r"^[\p{L}\s\-']+$" with regex module
