"""Common GraphQL types and utilities."""

from typing import Generic, List, Optional, TypeVar
import strawberry
from datetime import datetime

T = TypeVar("T")


@strawberry.type
class PageInfo:
    """Pagination information for connections."""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None
    total_count: int


@strawberry.type
class Edge(Generic[T]):
    """Edge type for GraphQL connections."""
    node: T
    cursor: str


@strawberry.type
class Connection(Generic[T]):
    """GraphQL connection type for pagination."""
    edges: List[Edge[T]]
    page_info: PageInfo


@strawberry.input
class DateRangeInput:
    """Date range filter input."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@strawberry.input
class PaginationInput:
    """Pagination input for queries."""
    first: Optional[int] = 25
    after: Optional[str] = None
    last: Optional[int] = None
    before: Optional[str] = None


@strawberry.type
class MetricValue:
    """A single metric value with metadata."""
    value: float
    label: str
    trend: Optional[str] = None  # "up", "down", "stable"
    change_percent: Optional[float] = None
    previous_value: Optional[float] = None


@strawberry.type
class TimeSeriesPoint:
    """Time series data point."""
    timestamp: datetime
    value: float
    label: Optional[str] = None


@strawberry.enum
class SortDirection:
    """Sort direction enumeration."""
    ASC = "asc"
    DESC = "desc"


@strawberry.input
class SortInput:
    """Sort input for queries."""
    field: str
    direction: SortDirection = SortDirection.ASC