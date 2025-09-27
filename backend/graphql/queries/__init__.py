"""GraphQL query resolvers for the Naga SIS system."""

from .student import StudentQueries
from .academic import AcademicQueries
from .finance import FinanceQueries
from .analytics import AnalyticsQueries
from .dashboard import DashboardQueries

__all__ = [
    "StudentQueries",
    "AcademicQueries",
    "FinanceQueries",
    "AnalyticsQueries",
    "DashboardQueries",
]