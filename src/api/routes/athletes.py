"""
Athletes API Routes

Endpoints for retrieving athlete profiles, career statistics, and competition results.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from mysql.connector import Error

from ..database import DatabaseManager, get_db
from ..models import (
    AthleteSummary, AthleteSummariesResponse,
    AthleteResult, AthleteResultsResponse,
    PaginationMeta
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/athletes", tags=["Athletes"])


@router.get(
    "/summary",
    response_model=AthleteSummariesResponse,
    summary="List athlete career summaries",
    description="Get paginated list of athletes with career statistics (wins, podiums, events competed)"
)
async def list_athlete_summaries(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Items per page (max {settings.MAX_PAGE_SIZE})"
    ),

    # Filters
    nationality: Optional[str] = Query(None, description="Filter by nationality"),
    min_events: Optional[int] = Query(None, ge=1, description="Minimum number of events competed"),
    min_wins: Optional[int] = Query(None, ge=0, description="Minimum number of wins"),
    has_podiums: Optional[bool] = Query(None, description="Only athletes with podium finishes"),

    # Sorting
    sort_by: str = Query(
        "total_events",
        description="Sort field: 'total_events', 'wins', 'total_podiums', 'athlete_name'"
    ),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),

    # Database dependency
    db: DatabaseManager = Depends(get_db)
):
    """
    Get paginated list of athlete career summaries

    Returns aggregated statistics for each athlete across all competitions.

    **Filters:**
    - `nationality`: Filter by athlete nationality
    - `min_events`: Minimum events competed
    - `min_wins`: Minimum number of wins
    - `has_podiums`: Only show athletes with podium finishes (1st-3rd)

    **Sorting:**
    - `sort_by`: Field to sort by (total_events, wins, total_podiums, athlete_name)
    - `sort_order`: asc or desc

    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 500)
    """

    try:
        # Build WHERE clause
        where_conditions = []
        params = []

        if nationality is not None:
            where_conditions.append("nationality = %s")
            params.append(nationality)

        if min_events is not None:
            where_conditions.append("total_events >= %s")
            params.append(min_events)

        if min_wins is not None:
            where_conditions.append("wins >= %s")
            params.append(min_wins)

        if has_podiums:
            where_conditions.append("total_podiums > 0")

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Validate and build ORDER BY clause
        valid_sort_fields = {
            'total_events', 'wins', 'total_podiums', 'athlete_name',
            'best_finish', 'first_year', 'last_year'
        }
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"
            )

        sort_order_upper = sort_order.upper()
        if sort_order_upper not in ['ASC', 'DESC']:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_order. Must be 'asc' or 'desc'"
            )

        order_clause = f"{sort_by} {sort_order_upper}"

        # Count total items
        count_query = f"""
            SELECT COUNT(*) as total
            FROM ATHLETE_SUMMARY_VIEW
            WHERE {where_clause}
        """
        total = db.execute_count(count_query, tuple(params))

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        # Validate page number
        if page > total_pages and total > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Page {page} does not exist. Total pages: {total_pages}"
            )

        # Calculate offset
        offset = (page - 1) * page_size

        # Query athlete summaries
        query = f"""
            SELECT
                athlete_id, athlete_name, nationality, year_of_birth,
                profile_picture_url, pwa_sail_number,
                total_events, best_finish, first_year, last_year,
                wins, second_places, third_places, total_podiums,
                divisions_competed, data_sources, match_stage, match_score
            FROM ATHLETE_SUMMARY_VIEW
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """

        results = db.execute_query(query, tuple(params + [page_size, offset]))

        # Convert to Pydantic models
        athletes = [AthleteSummary(**row) for row in results] if results else []

        # Build pagination metadata
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )

        return AthleteSummariesResponse(athletes=athletes, pagination=pagination)

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in list_athlete_summaries: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in list_athlete_summaries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/results",
    response_model=AthleteResultsResponse,
    summary="List competition results with athlete details",
    description="Get paginated list of competition results enriched with athlete profiles and event information"
)
async def list_athlete_results(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Items per page (max {settings.MAX_PAGE_SIZE})"
    ),

    # Filters
    athlete_id: Optional[int] = Query(None, description="Filter by unified athlete ID"),
    athlete_name: Optional[str] = Query(None, description="Filter by athlete name (partial match)"),
    nationality: Optional[str] = Query(None, description="Filter by nationality"),
    event_year: Optional[int] = Query(None, ge=2016, le=2030, description="Filter by event year"),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    country_code: Optional[str] = Query(None, description="Filter by event country code"),
    division: Optional[str] = Query(None, description="Filter by division (partial match)"),
    sex: Optional[str] = Query(None, description="Filter by gender category"),
    podium_only: Optional[bool] = Query(None, description="Only show podium finishes (1st-3rd)"),

    # Database dependency
    db: DatabaseManager = Depends(get_db)
):
    """
    Get paginated list of competition results with athlete profiles

    Returns enriched competition results combining athlete data and event details.

    **Filters:**
    - `athlete_id`: Specific athlete (unified ID)
    - `athlete_name`: Athlete name (partial match)
    - `nationality`: Filter by athlete nationality
    - `event_year`: Filter by event year
    - `event_id`: Specific event
    - `country_code`: Event country code
    - `division`: Division name (partial match)
    - `sex`: Gender category
    - `podium_only`: Only 1st-3rd place finishes

    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 500)
    """

    try:
        # Build WHERE clause
        where_conditions = []
        params = []

        if athlete_id is not None:
            where_conditions.append("athlete_id = %s")
            params.append(athlete_id)

        if athlete_name is not None:
            where_conditions.append("athlete_name LIKE %s")
            params.append(f"%{athlete_name}%")

        if nationality is not None:
            where_conditions.append("nationality = %s")
            params.append(nationality)

        if event_year is not None:
            where_conditions.append("event_year = %s")
            params.append(event_year)

        if event_id is not None:
            where_conditions.append("event_id = %s")
            params.append(event_id)

        if country_code is not None:
            where_conditions.append("country_code = %s")
            params.append(country_code.upper())

        if division is not None:
            where_conditions.append("division_label LIKE %s")
            params.append(f"%{division}%")

        if sex is not None:
            where_conditions.append("sex = %s")
            params.append(sex)

        if podium_only:
            where_conditions.append("CAST(placement AS UNSIGNED) <= 3")

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Count total items
        count_query = f"""
            SELECT COUNT(*) as total
            FROM ATHLETE_RESULTS_VIEW
            WHERE {where_clause}
        """
        total = db.execute_count(count_query, tuple(params))

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        # Validate page number
        if page > total_pages and total > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Page {page} does not exist. Total pages: {total_pages}"
            )

        # Calculate offset
        offset = (page - 1) * page_size

        # Query results
        query = f"""
            SELECT
                result_id, result_source,
                athlete_id, athlete_name, nationality, year_of_birth,
                profile_picture_url, pwa_sail_number,
                event_db_id, event_id, event_name, event_year,
                country_code, stars, event_image_url,
                division_label, division_code, sex, placement,
                result_scraped_at
            FROM ATHLETE_RESULTS_VIEW
            WHERE {where_clause}
            ORDER BY event_year DESC, event_id, CAST(placement AS UNSIGNED)
            LIMIT %s OFFSET %s
        """

        results = db.execute_query(query, tuple(params + [page_size, offset]))

        # Convert to Pydantic models
        athlete_results = [AthleteResult(**row) for row in results] if results else []

        # Build pagination metadata
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )

        return AthleteResultsResponse(results=athlete_results, pagination=pagination)

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in list_athlete_results: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in list_athlete_results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{athlete_id}/summary",
    response_model=AthleteSummary,
    summary="Get athlete career summary",
    description="Get career statistics for a specific athlete"
)
async def get_athlete_summary(
    athlete_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get career summary for a specific athlete

    **Path Parameters:**
    - `athlete_id`: Unified athlete ID

    **Returns:**
    - Athlete career statistics and profile

    **Errors:**
    - 404: Athlete not found
    - 500: Database error
    """

    try:
        query = """
            SELECT
                athlete_id, athlete_name, nationality, year_of_birth,
                profile_picture_url, pwa_sail_number,
                total_events, best_finish, first_year, last_year,
                wins, second_places, third_places, total_podiums,
                divisions_competed, data_sources, match_stage, match_score
            FROM ATHLETE_SUMMARY_VIEW
            WHERE athlete_id = %s
        """

        result = db.execute_query(query, (athlete_id,), fetch_one=True)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Athlete with id {athlete_id} not found"
            )

        return AthleteSummary(**result)

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in get_athlete_summary: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_athlete_summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
