"""
Pydantic Models for API Responses

Defines response schemas for all API endpoints.
"""

from datetime import date, datetime
from typing import Optional, List
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
    events: List[Event] = Field(..., description="List of events")
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
# Athlete Models
# ============================================================================

class AthleteSummary(BaseModel):
    """
    Athlete career summary model

    Aggregated career statistics for a single athlete.
    """
    athlete_id: int = Field(..., description="Unified athlete ID")
    athlete_name: str = Field(..., description="Athlete primary name")
    nationality: Optional[str] = Field(None, description="Athlete nationality")
    year_of_birth: Optional[int] = Field(None, description="Year of birth")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL (PWA or LiveHeats)")
    pwa_sail_number: Optional[str] = Field(None, description="PWA sail number")

    # Career statistics
    total_events: int = Field(..., description="Total events competed in")
    best_finish: Optional[int] = Field(None, description="Best placement achieved")
    first_year: Optional[int] = Field(None, description="First year competing")
    last_year: Optional[int] = Field(None, description="Most recent year competing")

    # Podium statistics
    wins: int = Field(0, description="Number of 1st place finishes")
    second_places: int = Field(0, description="Number of 2nd place finishes")
    third_places: int = Field(0, description="Number of 3rd place finishes")
    total_podiums: int = Field(0, description="Total podium finishes (1st-3rd)")

    # Additional info
    divisions_competed: Optional[str] = Field(None, description="Divisions competed in (comma-separated)")
    data_sources: Optional[str] = Field(None, description="Data sources (comma-separated)")
    match_stage: Optional[str] = Field(None, description="Match quality stage")
    match_score: Optional[int] = Field(None, description="Match quality score")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "athlete_id": 5,
                "athlete_name": "Sarah-Quita Offringa",
                "nationality": "Aruba",
                "year_of_birth": 1991,
                "profile_picture_url": "https://www.pwaworldtour.com/...",
                "pwa_sail_number": "ARU-23",
                "total_events": 29,
                "best_finish": 1,
                "first_year": 2016,
                "last_year": 2025,
                "wins": 10,
                "second_places": 8,
                "third_places": 7,
                "total_podiums": 25,
                "divisions_competed": "Wave Women",
                "data_sources": "PWA, Live Heats",
                "match_stage": "Exact",
                "match_score": 100
            }
        }


class AthleteResult(BaseModel):
    """
    Athlete competition result model

    Single result from a competition with athlete and event details.
    """
    result_id: int = Field(..., description="Result database ID")
    result_source: str = Field(..., description="Data source: 'PWA' or 'Live Heats'")

    # Athlete information
    athlete_id: int = Field(..., description="Unified athlete ID")
    athlete_name: str = Field(..., description="Athlete primary name")
    nationality: Optional[str] = Field(None, description="Athlete nationality")
    year_of_birth: Optional[int] = Field(None, description="Year of birth")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    pwa_sail_number: Optional[str] = Field(None, description="PWA sail number")

    # Event information
    event_db_id: int = Field(..., description="Event database ID")
    event_id: int = Field(..., description="Source-specific event ID")
    event_name: str = Field(..., description="Event name")
    event_year: int = Field(..., description="Event year")
    country_code: Optional[str] = Field(None, description="Event country code")
    stars: Optional[int] = Field(None, description="Event star rating")
    event_image_url: Optional[str] = Field(None, description="Event image URL")

    # Result details
    division_label: str = Field(..., description="Division name")
    division_code: Optional[str] = Field(None, description="Division code")
    sex: Optional[str] = Field(None, description="Gender category")
    placement: str = Field(..., description="Final placement/rank")

    # Metadata
    result_scraped_at: Optional[datetime] = Field(None, description="When result was scraped")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "result_id": 1,
                "result_source": "PWA",
                "athlete_id": 5,
                "athlete_name": "Sarah-Quita Offringa",
                "nationality": "Aruba",
                "year_of_birth": 1991,
                "profile_picture_url": "https://www.pwaworldtour.com/...",
                "pwa_sail_number": "ARU-23",
                "event_db_id": 1,
                "event_id": 15228,
                "event_name": "Chile, Matanzas",
                "event_year": 2025,
                "country_code": "CL",
                "stars": 5,
                "event_image_url": "https://www.pwaworldtour.com/...",
                "division_label": "Wave Women",
                "division_code": "W",
                "sex": "Female",
                "placement": "1",
                "result_scraped_at": "2025-01-15T10:30:00"
            }
        }


class AthleteSummariesResponse(BaseModel):
    """
    Paginated athlete summaries list response
    """
    athletes: List[AthleteSummary] = Field(..., description="List of athlete summaries")
    pagination: PaginationMeta = Field(..., description="Pagination information")


class AthleteResultsResponse(BaseModel):
    """
    Paginated athlete results list response
    """
    results: List[AthleteResult] = Field(..., description="List of competition results")
    pagination: PaginationMeta = Field(..., description="Pagination information")


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
