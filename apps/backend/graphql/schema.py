"""Main GraphQL schema for the Naga SIS system.

This module combines all queries, mutations, and subscriptions into a single
Strawberry GraphQL schema with comprehensive type definitions and resolvers.
"""

import strawberry
from typing import Optional

from .queries.student import StudentQueries
from .queries.academic import AcademicQueries
from .queries.finance import FinanceQueries
from .queries.analytics import AnalyticsQueries
from .queries.dashboard import DashboardQueries
from .queries.enhanced_student import EnhancedStudentQueries

from .mutations.grades import GradeMutations
from .mutations.finance import FinanceMutations
from .mutations.enhanced_grades import EnhancedGradeMutations

from .subscriptions.real_time import RealTimeSubscriptions


@strawberry.type
class Query(
    StudentQueries,
    AcademicQueries,
    FinanceQueries,
    AnalyticsQueries,
    DashboardQueries,
    EnhancedStudentQueries
):
    """Root query type combining all domain queries."""

    @strawberry.field
    def health(self) -> str:
        """GraphQL health check endpoint."""
        return "GraphQL API is healthy"

    @strawberry.field
    def api_info(self) -> str:
        """API information."""
        return "Naga SIS GraphQL API v2.0"


@strawberry.type
class Mutation(
    GradeMutations,
    FinanceMutations,
    EnhancedGradeMutations
):
    """Root mutation type combining all domain mutations."""

    @strawberry.mutation
    def ping(self) -> str:
        """Simple ping mutation for testing."""
        return "pong"


@strawberry.type
class Subscription(
    RealTimeSubscriptions
):
    """Root subscription type for real-time features."""
    pass


# Create the main GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[
        # Add performance monitoring
        strawberry.extensions.QueryDepthLimiter(max_depth=10),
        # Add query complexity analysis
        # strawberry.extensions.QueryComplexityLimiter(max_complexity=1000),
    ]
)


# Export schema for Django integration
__all__ = ["schema"]