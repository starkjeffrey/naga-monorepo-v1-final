"""Shared API schemas for django-ninja endpoints.

This module provides common response schemas, error handling patterns,
and data structures used across all v1 API endpoints.

Schema Categories:
- Response schemas: StandardResponse, PaginatedResponse, etc.
- Error schemas: ErrorResponse, ValidationError, etc.
- Common data schemas: Metadata, Status, etc.
"""

from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, Field

# Generic type for pagination
T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationErrorDetail(BaseModel):
    """Validation error detail schema."""

    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Validation error message")
    code: str | None = Field(None, description="Validation error code")


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    error: str = Field("Validation error", description="Error message")
    details: list[ValidationErrorDetail] = Field(..., description="Validation error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class StandardResponse(BaseModel):
    """Standard success response schema."""

    success: bool = Field(True, description="Operation success status")
    message: str | None = Field(None, description="Success message")
    data: dict[str, Any] | None = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field("healthy", description="Service status")
    version: str = Field("1.0.0", description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    services: dict[str, str] | None = Field(None, description="Service dependencies status")


class ApiInfoResponse(BaseModel):
    """API information response schema."""

    title: str = Field("Naga SIS API", description="API title")
    version: str = Field("1.0.0", description="API version")
    description: str = Field("Student Information System API", description="API description")
    docs_url: str = Field("/api/docs/", description="API documentation URL")
    contact: dict[str, str] | None = Field(None, description="Contact information")


class PaginationMeta(BaseModel):
    """Pagination metadata schema."""

    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_prev: bool = Field(..., description="Has previous page")
    has_next: bool = Field(..., description="Has next page")
    prev_num: int | None = Field(None, description="Previous page number")
    next_num: int | None = Field(None, description="Next page number")


class PaginatedResponse[T](BaseModel):
    """Generic paginated response schema."""

    data: list[T] = Field(..., description="Paginated data items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    success: bool = Field(True, description="Operation success status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class StatusResponse(BaseModel):
    """Generic status response schema."""

    status: str = Field(..., description="Operation status")
    message: str | None = Field(None, description="Status message")
    progress: int | None = Field(None, ge=0, le=100, description="Progress percentage")
    details: dict[str, Any] | None = Field(None, description="Additional status details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class FileUploadResponse(BaseModel):
    """File upload response schema."""

    filename: str = Field(..., description="Uploaded filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    file_url: str | None = Field(None, description="File access URL")
    success: bool = Field(True, description="Upload success status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Upload timestamp")


class BulkOperationResponse(BaseModel):
    """Bulk operation response schema."""

    total: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Error details")
    success: bool = Field(..., description="Overall operation success")
    timestamp: datetime = Field(default_factory=datetime.now, description="Operation timestamp")


# Common HTTP status code responses
HTTP_400_VALIDATION_ERROR = {400: {"model": ValidationErrorResponse, "description": "Validation error"}}

HTTP_401_UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "Authentication required"}}

HTTP_403_FORBIDDEN = {403: {"model": ErrorResponse, "description": "Permission denied"}}

HTTP_404_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Resource not found"}}

HTTP_500_INTERNAL_ERROR = {500: {"model": ErrorResponse, "description": "Internal server error"}}

# Combined common error responses
COMMON_ERROR_RESPONSES = {
    **HTTP_400_VALIDATION_ERROR,
    **HTTP_401_UNAUTHORIZED,
    **HTTP_403_FORBIDDEN,
    **HTTP_404_NOT_FOUND,
    **HTTP_500_INTERNAL_ERROR,
}


# Export schemas
__all__ = [
    "COMMON_ERROR_RESPONSES",
    "HTTP_400_VALIDATION_ERROR",
    "HTTP_401_UNAUTHORIZED",
    "HTTP_403_FORBIDDEN",
    "HTTP_404_NOT_FOUND",
    "HTTP_500_INTERNAL_ERROR",
    "ApiInfoResponse",
    "BulkOperationResponse",
    "ErrorResponse",
    "FileUploadResponse",
    "HealthResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "StandardResponse",
    "StatusResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
]
