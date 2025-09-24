"""Policy-specific exceptions for clear error handling."""


class PolicyError(Exception):
    """Base exception for policy-related errors."""


class PolicyNotFoundError(PolicyError):
    """Raised when a requested policy is not registered."""


class PolicyEvaluationError(PolicyError):
    """Raised when policy evaluation fails due to internal error."""


class PolicyViolationError(PolicyError):
    """Raised when a policy violation cannot be processed."""


class PolicyParameterError(PolicyError):
    """Raised when required policy parameters are missing or invalid."""
