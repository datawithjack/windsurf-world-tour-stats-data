"""
Pydantic Models for API Responses

Defines response schemas for all API endpoints.
"""

from datetime import date, datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field, HttpUrl, field_validator


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

    # Athlete Participation Counts (from EVENT_INFO_VIEW)
    total_athletes: Optional[int] = Field(None, description="Total unique athletes who competed in event")
    total_men: Optional[int] = Field(None, description="Total male athletes who competed")
    total_women: Optional[int] = Field(None, description="Total female athletes who competed")

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
# Athlete Event Stats Models (for Athlete Stats Tab)
# ============================================================================

class AthleteListItem(BaseModel):
    """
    Athlete summary for event athlete list

    Used in dropdown selector for athlete stats tab.
    """
    athlete_id: int = Field(..., description="Unified athlete ID")
    name: str = Field(..., description="Full athlete name")
    country: str = Field(..., description="Country name")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    overall_position: int = Field(..., description="Final placement in event (1 = winner)")
    sail_number: Optional[str] = Field(None, description="Competition sail number")
    profile_image: Optional[str] = Field(None, description="URL to athlete profile photo")
    total_heats: int = Field(..., description="Number of heats competed in")
    best_heat_score: float = Field(..., description="Highest single heat score")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "athlete_id": 456,
                "name": "Sarah Degrieck",
                "country": "Belgium",
                "country_code": "BE",
                "overall_position": 1,
                "sail_number": "BEL-8",
                "profile_image": "https://cdn.example.com/athletes/456.jpg",
                "total_heats": 8,
                "best_heat_score": 24.50
            }
        }


class AthleteListMetadata(BaseModel):
    """
    Metadata for athlete list response
    """
    total_athletes: int = Field(..., description="Total number of athletes in response")
    generated_at: datetime = Field(..., description="Timestamp when data was generated (ISO 8601)")

    class Config:
        from_attributes = True


class AthleteListResponse(BaseModel):
    """
    Event athlete list response

    Contains all athletes who competed in a specific event and division.
    """
    event_id: int = Field(..., description="Event database ID")
    event_name: str = Field(..., description="Event name")
    sex: str = Field(..., description="Gender division ('Women' or 'Men')")
    athletes: List[AthleteListItem] = Field(..., description="List of athletes (sorted by overall_position)")
    metadata: AthleteListMetadata = Field(..., description="Response metadata")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": 123,
                "event_name": "2025 Tenerife Grand Slam",
                "sex": "Women",
                "athletes": [
                    {
                        "athlete_id": 456,
                        "name": "Sarah Degrieck",
                        "country": "Belgium",
                        "country_code": "BE",
                        "overall_position": 1,
                        "sail_number": "BEL-8",
                        "profile_image": "https://cdn.example.com/athletes/456.jpg",
                        "total_heats": 8,
                        "best_heat_score": 24.50
                    }
                ],
                "metadata": {
                    "total_athletes": 26,
                    "generated_at": "2025-11-14T10:30:00Z"
                }
            }
        }


class AthleteProfile(BaseModel):
    """
    Athlete profile information for stats detail view
    """
    name: str = Field(..., description="Full athlete name")
    country: str = Field(..., description="Country name")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    profile_image: Optional[str] = Field(None, description="URL to athlete profile photo")
    sponsors: Optional[str] = Field(None, description="Comma-separated list of sponsors")
    sail_number: Optional[str] = Field(None, description="Competition sail number")

    class Config:
        from_attributes = True


class BestHeatScore(BaseModel):
    """
    Best heat score with context
    """
    score: float = Field(..., description="Total heat score")
    heat: str = Field(..., description="Heat identifier")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    opponents: Optional[List[str]] = Field(None, description="List of opponent names in that heat")

    class Config:
        from_attributes = True


class BestJumpScore(BaseModel):
    """
    Best jump score with context
    """
    score: float = Field(..., description="Jump score")
    heat: str = Field(..., description="Heat identifier")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    move: str = Field(..., description="Move type name (decoded from codes like B, F, P)")
    opponents: Optional[List[str]] = Field(None, description="List of opponent names in that heat")

    class Config:
        from_attributes = True


class BestWaveScore(BaseModel):
    """
    Best wave score with context
    """
    score: float = Field(..., description="Wave score")
    heat: str = Field(..., description="Heat identifier")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    opponents: Optional[List[str]] = Field(None, description="List of opponent names in that heat")

    class Config:
        from_attributes = True


class AthleteSummaryStats(BaseModel):
    """
    Summary statistics for athlete in event
    """
    overall_position: int = Field(..., description="Final placement in event (1 = winner)")
    best_heat_score: BestHeatScore = Field(..., description="Best overall heat score with context")
    best_jump_score: BestJumpScore = Field(..., description="Best individual jump score with context")
    best_wave_score: BestWaveScore = Field(..., description="Best individual wave score with context")

    class Config:
        from_attributes = True


class MoveTypeScore(BaseModel):
    """
    Move type statistics
    """
    move_type: str = Field(..., description="Move type name (e.g., 'Forward Loop', 'Backloop', 'Wave')")
    best_score: float = Field(..., description="Best score achieved for this move type")
    average_score: float = Field(..., description="Average score for this move type")
    fleet_average: Optional[float] = Field(None, description="Fleet average score for this move type (counting scores only)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "move_type": "Forward Loop",
                "best_score": 7.10,
                "average_score": 5.65,
                "fleet_average": 4.85
            }
        }


class HeatScore(BaseModel):
    """
    Heat score breakdown
    """
    heat_number: str = Field(..., description="Heat identifier (e.g., '19a', '23a')")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    score: Optional[float] = Field(None, description="Total heat score (null if incomplete)")
    place: Optional[int] = Field(None, description="Placement in heat (1=1st, 2=2nd, etc.)")
    elimination_type: Optional[str] = Field(None, description="Either 'Single' or 'Double' (null if unknown)")

    class Config:
        from_attributes = True


class JumpScore(BaseModel):
    """
    Individual jump score
    """
    heat_number: str = Field(..., description="Heat identifier where jump was performed")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    move: str = Field(..., description="Move type performed (decoded from codes like B, F, P)")
    score: float = Field(..., description="Individual jump score")
    counting: bool = Field(..., description="Whether this score counted toward heat total")

    class Config:
        from_attributes = True


class WaveScore(BaseModel):
    """
    Individual wave score
    """
    heat_number: str = Field(..., description="Heat identifier where wave was ridden")
    round_name: Optional[str] = Field(None, description="Round name (e.g., 'Final', 'Semi-Finals')")
    score: float = Field(..., description="Individual wave score")
    counting: bool = Field(..., description="Whether this score counted toward heat total")
    wave_index: Optional[int] = Field(None, description="Wave index number (optional)")

    class Config:
        from_attributes = True


class AthleteStatsMetadata(BaseModel):
    """
    Metadata for athlete stats response
    """
    total_heats: int = Field(..., description="Total number of heats competed in")
    total_jumps: int = Field(..., description="Total number of jump attempts")
    total_waves: int = Field(..., description="Total number of wave attempts")
    generated_at: datetime = Field(..., description="Timestamp when data was generated (ISO 8601)")

    class Config:
        from_attributes = True


class AthleteStatsResponse(BaseModel):
    """
    Detailed athlete statistics for event

    Complete performance statistics for a specific athlete in a specific event.
    """
    event_id: int = Field(..., description="Event database ID")
    event_name: str = Field(..., description="Event name")
    sex: str = Field(..., description="Gender division ('Women' or 'Men')")
    athlete_id: int = Field(..., description="Unified athlete ID")
    profile: AthleteProfile = Field(..., description="Athlete profile information")
    summary_stats: AthleteSummaryStats = Field(..., description="Summary statistics with best scores")
    move_type_scores: List[MoveTypeScore] = Field(..., description="Move type analysis (sorted by best_score DESC)")
    heat_scores: List[HeatScore] = Field(..., description="All heat scores (sorted by score DESC)")
    jump_scores: List[JumpScore] = Field(..., description="All jump scores (sorted by score DESC)")
    wave_scores: List[WaveScore] = Field(..., description="All wave scores (sorted by score DESC)")
    metadata: AthleteStatsMetadata = Field(..., description="Response metadata")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": 123,
                "event_name": "2025 Tenerife Grand Slam",
                "sex": "Women",
                "athlete_id": 456,
                "profile": {
                    "name": "Daida Ruano Moreno",
                    "country": "Spain",
                    "country_code": "ES",
                    "profile_image": "https://cdn.example.com/athletes/456.jpg",
                    "sponsors": "Bruch Boards, Severne Windsurfing, Maui Ultra Fins",
                    "sail_number": "E-64"
                },
                "summary_stats": {
                    "overall_position": 1,
                    "best_heat_score": {
                        "score": 23.58,
                        "heat": "23a",
                        "opponents": ["Kiefer Quintana", "Degrieck", "Offringa"]
                    },
                    "best_jump_score": {
                        "score": 7.10,
                        "heat": "19a",
                        "move": "Forward Loop",
                        "opponents": ["Katz", "Morales Navarro", "Wermeister"]
                    },
                    "best_wave_score": {
                        "score": 6.75,
                        "heat": "23a",
                        "opponents": ["Kiefer Quintana", "Degrieck", "Offringa"]
                    }
                },
                "move_type_scores": [
                    {
                        "move_type": "Forward Loop",
                        "best_score": 7.10,
                        "average_score": 5.65
                    }
                ],
                "heat_scores": [
                    {
                        "heat_number": "23a",
                        "score": 23.58,
                        "elimination_type": "Single"
                    }
                ],
                "jump_scores": [
                    {
                        "heat_number": "19a",
                        "move": "Forward Loop",
                        "score": 7.10,
                        "counting": True
                    }
                ],
                "wave_scores": [
                    {
                        "heat_number": "23a",
                        "score": 6.75,
                        "counting": True,
                        "wave_index": 1014
                    }
                ],
                "metadata": {
                    "total_heats": 5,
                    "total_jumps": 9,
                    "total_waves": 8,
                    "generated_at": "2025-11-14T11:15:00Z"
                }
            }
        }


# ============================================================================
# Event Stats Models
# ============================================================================

class ScoreDetail(BaseModel):
    """
    Score detail with athlete information

    Base model for best scores in summary statistics.
    """
    score: Optional[float] = Field(None, description="Score value (rounded to 2 decimal places)")
    athlete_name: Optional[str] = Field(None, description="Athlete name")
    athlete_id: Optional[int] = Field(None, description="Unified athlete ID")
    heat_number: Optional[str] = Field(None, description="Heat number/identifier")

    # Multiple best scores
    has_multiple_tied: bool = Field(False, description="True if multiple athletes are tied for this best score")
    all_tied_scores: Optional[List['ScoreDetail']] = Field(None, description="All scores tied for this best score (if multiple)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "score": 24.50,
                "athlete_name": "Degrieck",
                "athlete_id": 456,
                "heat_number": "21a",
                "has_multiple_tied": False,
                "all_tied_scores": None
            }
        }


class JumpScoreDetail(BaseModel):
    """
    Jump score detail with move type

    Extends ScoreDetail with move type information for jump scores.
    """
    score: Optional[float] = Field(None, description="Score value (rounded to 2 decimal places)")
    athlete_name: Optional[str] = Field(None, description="Athlete name")
    athlete_id: Optional[int] = Field(None, description="Unified athlete ID")
    heat_number: Optional[str] = Field(None, description="Heat number/identifier")
    move_type: Optional[str] = Field(None, description="Jump move type (e.g., 'Forward Loop', 'Backloop')")

    # Multiple best scores
    has_multiple_tied: bool = Field(False, description="True if multiple athletes are tied for this best score")
    all_tied_scores: Optional[List['JumpScoreDetail']] = Field(None, description="All jump scores tied for this best score (if multiple)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "score": 7.10,
                "athlete_name": "Ruano Moreno",
                "athlete_id": 789,
                "heat_number": "19a",
                "move_type": "Forward Loop",
                "has_multiple_tied": False,
                "all_tied_scores": None
            }
        }


class BestScoredBy(BaseModel):
    """
    Information about who scored the best for a move type

    Used in MoveTypeStat to indicate the athlete who achieved the best score.
    """
    athlete_name: Optional[str] = Field(None, description="Athlete name")
    athlete_id: Optional[int] = Field(None, description="Unified athlete ID")
    heat_number: Optional[str] = Field(None, description="Heat number/identifier")
    score: Optional[float] = Field(None, description="Score value")

    class Config:
        from_attributes = True


class MoveTypeStat(BaseModel):
    """
    Move type statistics

    Aggregated statistics for a specific move type (e.g., Wave, Forward Loop).
    """
    move_type: Optional[str] = Field(None, description="Move type name")
    best_score: float = Field(..., description="Highest score for this move type")
    average_score: Optional[float] = Field(None, description="Average score for this move type (rounded to 2 decimals)")
    best_scored_by: BestScoredBy = Field(..., description="Athlete who scored the best")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "move_type": "Wave",
                "best_score": 7.50,
                "average_score": 2.95,
                "best_scored_by": {
                    "athlete_name": "Degrieck",
                    "athlete_id": "456",
                    "heat_number": "21a",
                    "score": 7.50
                }
            }
        }


class ScoreEntry(BaseModel):
    """
    Score table entry

    Single entry in the top scores tables with rank.
    """
    rank: int = Field(..., description="Rank position (sequential, starting at 1)")
    athlete_name: Optional[str] = Field(None, description="Athlete name")
    athlete_id: Optional[int] = Field(None, description="Unified athlete ID (for navigation to athlete profile)")
    score: Optional[float] = Field(None, description="Score value (rounded to 2 decimal places)")
    heat_number: Optional[str] = Field(None, description="Heat number/identifier")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "rank": 1,
                "athlete_name": "Degrieck",
                "athlete_id": 456,
                "score": 24.50,
                "heat_number": "21a"
            }
        }


class JumpScoreEntry(ScoreEntry):
    """
    Jump score table entry

    Extends ScoreEntry with move type for jump scores.
    """
    move_type: Optional[str] = Field(None, description="Jump move type (e.g., 'Forward Loop', 'Backloop')")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "rank": 1,
                "athlete_name": "Ruano Moreno",
                "athlete_id": 789,
                "score": 7.10,
                "move_type": "Forward Loop",
                "heat_number": "19a"
            }
        }


class SummaryStats(BaseModel):
    """
    Summary statistics

    Best scores across all categories for an event.
    Each best score object contains has_multiple_tied flag and all_tied_scores list if applicable.
    """
    best_heat_score: Optional[ScoreDetail] = Field(None, description="Best overall heat score (includes tied scores if multiple)")
    best_jump_score: Optional[JumpScoreDetail] = Field(None, description="Best individual jump score (includes tied scores if multiple)")
    best_wave_score: Optional[ScoreDetail] = Field(None, description="Best individual wave score (includes tied scores if multiple)")

    class Config:
        from_attributes = True


class EventStatsMetadata(BaseModel):
    """
    Event statistics metadata

    Metadata about the event statistics data.
    """
    total_heats: int = Field(..., description="Total number of heats")
    total_athletes: int = Field(..., description="Total number of athletes")
    generated_at: datetime = Field(..., description="Timestamp when stats were generated (ISO 8601)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "total_heats": 52,
                "total_athletes": 26,
                "generated_at": "2025-11-09T17:45:00Z"
            }
        }


class EventStatsResponse(BaseModel):
    """
    Event statistics response

    Complete event statistics including summary, move type analysis, and top scores.
    """
    event_id: int = Field(..., description="Event database ID")
    event_name: str = Field(..., description="Event name")
    sex: str = Field(..., description="Gender division filter applied")
    summary_stats: SummaryStats = Field(..., description="Summary statistics (best scores)")
    move_type_stats: List[MoveTypeStat] = Field(..., description="Move type statistics (sorted by best_score DESC)")
    top_heat_scores: List[ScoreEntry] = Field(..., description="Top 10 heat scores (sorted DESC)")
    top_jump_scores: List[JumpScoreEntry] = Field(..., description="Top 10 jump scores (sorted DESC)")
    top_wave_scores: List[ScoreEntry] = Field(..., description="Top 10 wave scores (sorted DESC)")
    metadata: EventStatsMetadata = Field(..., description="Metadata about the statistics")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": 123,
                "event_name": "2025 Tenerife Grand Slam",
                "sex": "Women",
                "summary_stats": {
                    "best_heat_score": {
                        "score": 24.50,
                        "athlete_name": "Degrieck",
                        "athlete_id": "456",
                        "heat_number": "21a"
                    },
                    "best_jump_score": {
                        "score": 7.10,
                        "athlete_name": "Ruano Moreno",
                        "athlete_id": "789",
                        "heat_number": "19a",
                        "move_type": "Forward Loop"
                    },
                    "best_wave_score": {
                        "score": 7.50,
                        "athlete_name": "Degrieck",
                        "athlete_id": "456",
                        "heat_number": "21a"
                    }
                },
                "move_type_stats": [
                    {
                        "move_type": "Wave",
                        "best_score": 7.50,
                        "average_score": 2.95,
                        "best_scored_by": {
                            "athlete_name": "Degrieck",
                            "athlete_id": "456",
                            "heat_number": "21a",
                            "score": 7.50
                        }
                    }
                ],
                "top_heat_scores": [
                    {
                        "rank": 1,
                        "athlete_name": "Degrieck",
                        "athlete_id": "456",
                        "score": 24.50,
                        "heat_number": "21a"
                    }
                ],
                "top_jump_scores": [
                    {
                        "rank": 1,
                        "athlete_name": "Ruano Moreno",
                        "athlete_id": "789",
                        "score": 7.10,
                        "move_type": "Forward Loop",
                        "heat_number": "19a"
                    }
                ],
                "top_wave_scores": [
                    {
                        "rank": 1,
                        "athlete_name": "Degrieck",
                        "athlete_id": "456",
                        "score": 7.50,
                        "heat_number": "21a"
                    }
                ],
                "metadata": {
                    "total_heats": 52,
                    "total_athletes": 26,
                    "generated_at": "2025-11-09T17:45:00Z"
                }
            }
        }


# ============================================================================
# Site Stats Models
# ============================================================================

class SiteStat(BaseModel):
    """
    Site statistic model

    Single statistic from SITE_STATS_VIEW containing a metric name and value.
    """
    metric: str = Field(..., description="Statistic name/metric key")
    value: Union[str, int, float] = Field(..., description="Statistic value")

    @field_validator('value', mode='before')
    @classmethod
    def convert_value_to_string(cls, v):
        """Convert any value type to string for consistent API output"""
        if v is None:
            return ""
        return str(v)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "metric": "total_events",
                "value": "118"
            }
        }


class SiteStatsResponse(BaseModel):
    """
    Site statistics response

    Contains all site-wide statistics from SITE_STATS_VIEW.
    """
    stats: List[SiteStat] = Field(..., description="List of site statistics")
    generated_at: datetime = Field(..., description="Timestamp when stats were retrieved (ISO 8601)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "stats": [
                    {"metric": "total_events", "value": "118"},
                    {"metric": "total_athletes", "value": "359"},
                    {"metric": "total_results", "value": "2052"}
                ],
                "generated_at": "2025-11-10T10:30:00Z"
            }
        }


# ============================================================================
# Head-to-Head Models
# ============================================================================

class AthleteHeadToHeadStats(BaseModel):
    """
    Statistics for a single athlete in head-to-head comparison
    """
    athlete_id: int = Field(..., description="Unified athlete ID")
    name: str = Field(..., description="Athlete name")
    nationality: Optional[str] = Field(None, description="Athlete nationality")
    place: int = Field(..., description="Final placement in event")
    profile_image: Optional[str] = Field(None, description="Profile image URL")

    # Heat Score Statistics
    heat_scores_best: float = Field(..., description="Best overall heat score")
    heat_scores_avg: float = Field(..., description="Average heat score")

    # Jump Statistics
    jumps_best: float = Field(..., description="Best individual jump score")
    jumps_avg_counting: float = Field(..., description="Average counting jump score")

    # Wave Statistics
    waves_best: float = Field(..., description="Best individual wave score")
    waves_avg_counting: float = Field(..., description="Average counting wave score")

    # Heat Wins
    heat_wins: int = Field(..., description="Number of heats won")

    class Config:
        from_attributes = True


class ComparisonMetric(BaseModel):
    """
    Single comparison metric between two athletes
    """
    winner: str = Field(..., description="Which athlete won this metric ('athlete1', 'athlete2', or 'tie')")
    difference: float = Field(..., description="Absolute difference between values (always positive)")
    athlete1_value: float = Field(..., description="Athlete 1's value for this metric")
    athlete2_value: float = Field(..., description="Athlete 2's value for this metric")

    class Config:
        from_attributes = True


class HeadToHeadComparison(BaseModel):
    """
    Comparison calculations between two athletes
    """
    heat_scores_best: ComparisonMetric = Field(..., description="Best heat score comparison")
    heat_scores_avg: ComparisonMetric = Field(..., description="Average heat score comparison")
    jumps_best: ComparisonMetric = Field(..., description="Best jump score comparison")
    jumps_avg_counting: ComparisonMetric = Field(..., description="Average counting jump score comparison")
    waves_best: ComparisonMetric = Field(..., description="Best wave score comparison")
    waves_avg_counting: ComparisonMetric = Field(..., description="Average counting wave score comparison")
    heat_wins: ComparisonMetric = Field(..., description="Heat wins comparison (difference is count)")

    class Config:
        from_attributes = True


class HeadToHeadResponse(BaseModel):
    """
    Complete head-to-head comparison response
    """
    event_id: int = Field(..., description="Event database ID")
    event_name: str = Field(..., description="Event name")
    division: str = Field(..., description="Division (Men/Women)")

    athlete1: AthleteHeadToHeadStats = Field(..., description="First athlete's statistics")
    athlete2: AthleteHeadToHeadStats = Field(..., description="Second athlete's statistics")
    comparison: HeadToHeadComparison = Field(..., description="Comparison metrics with winners and differences")

    generated_at: datetime = Field(..., description="Timestamp when data was generated (ISO 8601)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": 123,
                "event_name": "2025 Sylt, Germany Grand Slam",
                "division": "Women",
                "athlete1": {
                    "athlete_id": 1,
                    "name": "Daida Ruano Moreno",
                    "nationality": "Spain",
                    "place": 1,
                    "profile_image": "https://example.com/photo.jpg",
                    "heat_scores_best": 31.0,
                    "heat_scores_avg": 24.5,
                    "jumps_best": 10.0,
                    "jumps_avg_counting": 7.8,
                    "waves_best": 7.0,
                    "waves_avg_counting": 5.89,
                    "heat_wins": 5
                },
                "athlete2": {
                    "athlete_id": 2,
                    "name": "Sarah-Quita Offringa",
                    "nationality": "Aruba",
                    "place": 2,
                    "profile_image": "https://example.com/photo2.jpg",
                    "heat_scores_best": 28.5,
                    "heat_scores_avg": 22.3,
                    "jumps_best": 9.5,
                    "jumps_avg_counting": 7.2,
                    "waves_best": 6.8,
                    "waves_avg_counting": 5.5,
                    "heat_wins": 4
                },
                "comparison": {
                    "heat_scores_best": {
                        "winner": "athlete1",
                        "difference": 2.5,
                        "athlete1_value": 31.0,
                        "athlete2_value": 28.5
                    },
                    "heat_scores_avg": {
                        "winner": "athlete1",
                        "difference": 2.2,
                        "athlete1_value": 24.5,
                        "athlete2_value": 22.3
                    },
                    "jumps_best": {
                        "winner": "athlete1",
                        "difference": 0.5,
                        "athlete1_value": 10.0,
                        "athlete2_value": 9.5
                    },
                    "jumps_avg_counting": {
                        "winner": "athlete1",
                        "difference": 0.6,
                        "athlete1_value": 7.8,
                        "athlete2_value": 7.2
                    },
                    "waves_best": {
                        "winner": "athlete1",
                        "difference": 0.2,
                        "athlete1_value": 7.0,
                        "athlete2_value": 6.8
                    },
                    "waves_avg_counting": {
                        "winner": "athlete1",
                        "difference": 0.39,
                        "athlete1_value": 5.89,
                        "athlete2_value": 5.5
                    },
                    "heat_wins": {
                        "winner": "athlete1",
                        "difference": 1.0,
                        "athlete1_value": 5.0,
                        "athlete2_value": 4.0
                    }
                },
                "generated_at": "2025-11-14T10:30:00Z"
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
