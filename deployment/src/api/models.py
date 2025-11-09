"""
Pydantic Models for API Responses

Defines response schemas for all API endpoints.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Event Models
# ============================================================================

class Event(BaseModel):
    """
    Event response model

    Represents a single PWA/IWT windsurf competition event.
    """
    id: int = Field(..., description="Database primary key")
    source: str = Field(..., description="Data source: 'PWA' or 'Live Heats'")
    year: int = Field(..., description="Event year")
    event_id: int = Field(..., description="Source-specific event ID")
    event_name: str = Field(..., description="Event name/location")
    event_url: Optional[str] = Field(None, description="Event URL on source website")

    # Dates
    event_date: Optional[str] = Field(None, description="Event date string from source")
    start_date: Optional[date] = Field(None, description="Event start date")
    end_date: Optional[date] = Field(None, description="Event end date")
    day_window: Optional[int] = Field(None, description="Competition window in days")

    # Event Details
    event_section: Optional[str] = Field(None, description="Event section/category")
    event_status: Optional[int] = Field(None, description="Status code (1=Upcoming, 2=In Progress, 3=Completed)")
    competition_state: Optional[int] = Field(None, description="Competition state code")

    # Disciplines
    has_wave_discipline: bool = Field(..., description="Whether event includes wave discipline")
    all_disciplines: Optional[str] = Field(None, description="All disciplines (comma-separated)")

    # Location
    country_flag: Optional[str] = Field(None, description="Country flag emoji or code")
    country_code: Optional[str] = Field(None, description="ISO country code")

    # Rating
    stars: Optional[int] = Field(None, description="Event star rating (4-7)")

    # Media
    event_image_url: Optional[str] = Field(None, description="Event image URL")

    # Timestamps
    scraped_at: datetime = Field(..., description="When data was scraped")
    created_at: Optional[datetime] = Field(None, description="Database record creation time")
    updated_at: Optional[datetime] = Field(None, description="Database record last update time")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "source": "PWA",
                "year": 2025,
                "event_id": 15228,
                "event_name": "Chile, Matanzas",
                "event_url": "https://www.pwaworldtour.com/index.php?id=4&tx_pwatour_pi2[...",
                "event_date": "27 Jan - 4 Feb",
                "start_date": "2025-01-27",
                "end_date": "2025-02-04",
                "day_window": 8,
                "event_section": "WORLD CUP",
                "event_status": 3,
                "competition_state": 3,
                "has_wave_discipline": True,
                "all_disciplines": "Wave",
                "country_flag": "flag_cl.gif",
                "country_code": "CL",
                "stars": 5,
                "event_image_url": "https://www.pwaworldtour.com/fileadmin/...",
                "scraped_at": "2025-01-15T10:30:00",
                "created_at": "2025-01-15T10:35:00",
                "updated_at": "2025-01-15T10:35:00"
            }
        }


class PaginationMeta(BaseModel):
    """
    Pagination metadata

    Provides information about pagination state.
    """
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class EventsResponse(BaseModel):
    """
    Paginated events list response

    Contains events data and pagination metadata.
    """
    events: list[Event] = Field(..., description="List of events")
    pagination: PaginationMeta = Field(..., description="Pagination information")


# ============================================================================
# Health Check Model
# ============================================================================

class HealthResponse(BaseModel):
    """
    Health check response

    Provides API and database health status.
    """
    status: str = Field(..., description="Overall health status: 'healthy' or 'unhealthy'")
    api_version: str = Field(..., description="API version")
    database: dict = Field(..., description="Database health information")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "api_version": "1.0.0",
                "database": {
                    "status": "healthy",
                    "database": "mysql://admin@localhost:3306/jfa_heatwave_db",
                    "environment": "development"
                }
            }
        }


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Error response model

    Standard error response format for all API errors.
    """
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid parameter value",
                "detail": "Parameter 'year' must be between 2016 and 2025"
            }
        }
