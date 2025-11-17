"""
Base Pydantic schemas for database entities.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


class AuditSchema(BaseSchema):
    """Base schema with audit fields."""

    id: int = Field(..., description="Entity ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="User who created the entity")
    updated_by: Optional[str] = Field(
        None, description="User who last updated the entity"
    )
    version: int = Field(default=1, description="Entity version")


class SoftDeleteSchema(AuditSchema):
    """Schema with soft delete fields."""

    is_deleted: bool = Field(default=False, description="Whether the entity is deleted")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    deleted_by: Optional[str] = Field(None, description="User who deleted the entity")


class PaginationSchema(BaseSchema):
    """Pagination schema."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")


class PaginatedResponseSchema(BaseSchema):
    """Paginated response schema."""

    items: list = Field(..., description="List of items")
    pagination: PaginationSchema = Field(..., description="Pagination information")


class ErrorSchema(BaseSchema):
    """Error schema."""

    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class SuccessSchema(BaseSchema):
    """Success response schema."""

    success: bool = Field(
        default=True, description="Whether the operation was successful"
    )
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


class ValidationErrorSchema(BaseSchema):
    """Validation error schema."""

    field: str = Field(..., description="Field name")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(..., description="Invalid value")


class BulkOperationSchema(BaseSchema):
    """Bulk operation schema."""

    total: int = Field(..., description="Total number of items")
    processed: int = Field(..., description="Number of processed items")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: Optional[list[ValidationErrorSchema]] = Field(
        None, description="Validation errors"
    )


class DatabaseStatsSchema(BaseSchema):
    """Database statistics schema."""

    connected: bool = Field(..., description="Whether database is connected")
    db_type: str = Field(..., description="Database type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    pool_size: Optional[int] = Field(None, description="Connection pool size")
    active_connections: Optional[int] = Field(
        None, description="Number of active connections"
    )
    idle_connections: Optional[int] = Field(
        None, description="Number of idle connections"
    )


class HealthCheckSchema(BaseSchema):
    """Health check schema."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    database: DatabaseStatsSchema = Field(..., description="Database statistics")
    services: Optional[Dict[str, str]] = Field(
        None, description="Other service statuses"
    )
