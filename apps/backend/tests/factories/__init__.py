"""
Centralized test factories for Naga SIS.

This module provides test data factories using factory_boy for consistent
test data generation across the entire test suite.

Note: Factories are imported lazily to avoid Django AppRegistryNotReady errors
during pytest discovery.
"""


# Lazy imports to avoid Django apps loading issues
def __getattr__(name: str):
    """Lazy loading of factories to avoid Django setup issues."""
    if name == "PersonFactory":
        from .people import PersonFactory

        return PersonFactory
    elif name == "StudentProfileFactory":
        from .people import StudentProfileFactory

        return StudentProfileFactory
    elif name == "TeacherProfileFactory":
        from .people import TeacherProfileFactory

        return TeacherProfileFactory
    elif name == "InvoiceFactory":
        from .finance import InvoiceFactory

        return InvoiceFactory
    elif name == "PaymentFactory":
        from .finance import PaymentFactory

        return PaymentFactory
    elif name == "PricingRuleFactory":
        from .finance import PricingRuleFactory

        return PricingRuleFactory
    elif name == "EnrollmentFactory":
        from .enrollment import EnrollmentFactory

        return EnrollmentFactory
    elif name == "CourseOfferingFactory":
        from .enrollment import CourseOfferingFactory

        return CourseOfferingFactory
    elif name == "CourseFactory":
        from .curriculum import CourseFactory

        return CourseFactory
    elif name == "MajorFactory":
        from .curriculum import MajorFactory

        return MajorFactory
    elif name == "TermFactory":
        from .curriculum import TermFactory

        return TermFactory
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Curriculum factories
    "CourseFactory",
    "CourseOfferingFactory",
    # Enrollment factories
    "EnrollmentFactory",
    # Finance factories
    "InvoiceFactory",
    "MajorFactory",
    "PaymentFactory",
    # People factories
    "PersonFactory",
    "PricingRuleFactory",
    "StudentProfileFactory",
    "TeacherProfileFactory",
    "TermFactory",
]
