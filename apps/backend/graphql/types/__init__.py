"""GraphQL type definitions for the Naga SIS system."""

from .student import StudentType, StudentAnalytics, StudentSearchFilters
from .academic import CourseType, GradeType, ClassHeaderType, AssignmentType
from .finance import InvoiceType, PaymentType, FinancialMetrics
from .analytics import DashboardMetrics, ChartData
from .common import PageInfo, Connection

__all__ = [
    # Student types
    "StudentType",
    "StudentAnalytics",
    "StudentSearchFilters",
    # Academic types
    "CourseType",
    "GradeType",
    "ClassHeaderType",
    "AssignmentType",
    # Finance types
    "InvoiceType",
    "PaymentType",
    "FinancialMetrics",
    # Analytics types
    "DashboardMetrics",
    "ChartData",
    # Common types
    "PageInfo",
    "Connection",
]