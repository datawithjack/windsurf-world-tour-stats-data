"""
Events API Routes

Endpoints for retrieving windsurf competition event data.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from mysql.connector import Error

from ..database import DatabaseManager, get_db
from ..models import Event, EventsResponse, PaginationMeta
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=EventsResponse,
    summary="List all events",
    description="Get a paginated list of windsurf competition events with optional filters"
)
async def list_events(
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Items per page (max {settings.MAX_PAGE_SIZE})"
    ),

    # Filters
    year: Optional[int] = Query(None, ge=2016, le=2030, description="Filter by event year"),
    source: Optional[str] = Query(None, description="Filter by source ('PWA' or 'Live Heats')"),
    country_code: Optional[str] = Query(None, max_length=10, description="Filter by ISO country code (e.g., 'CL', 'US')"),
    stars: Optional[int] = Query(None, ge=1, le=7, description="Filter by star rating (4-7)"),
    wave_only: bool = Query(True, description="Only include wave discipline events"),

    # Database dependency
    db: DatabaseManager = Depends(get_db)
):
    """
    Get paginated list of events with optional filters

    Returns events sorted by year (desc) and start_date (desc).

    **Filters:**
    - `year`: Event year (2016-2030)
    - `source`: Data source ('PWA' or 'Live Heats')
    - `country_code`: ISO country code
    - `stars`: Star rating (4-7)
    - `wave_only`: Only wave discipline events (default: true)

    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 500)
    """

    try:
        # Build WHERE clause
        where_conditions = []
        params = []

        if wave_only:
            where_conditions.append("has_wave_discipline = %s")
            params.append(True)

        if year is not None:
            where_conditions.append("year = %s")
            params.append(year)

        if source is not None:
            where_conditions.append("source = %s")
            params.append(source)

        if country_code is not None:
            where_conditions.append("country_code = %s")
            params.append(country_code.upper())

        if stars is not None:
            where_conditions.append("stars = %s")
            params.append(stars)

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Count total items
        count_query = f"""
            SELECT COUNT(*) as total
            FROM PWA_IWT_EVENTS
            WHERE {where_clause}
        """
        total = db.execute_count(count_query, tuple(params))

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
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

        # Query events
        query = f"""
            SELECT
                id, source, scraped_at, year, event_id, event_name, event_url,
                event_date, start_date, end_date, day_window,
                event_section, event_status, competition_state,
                has_wave_discipline, all_disciplines,
                country_flag, country_code, stars, event_image_url,
                created_at, updated_at
            FROM PWA_IWT_EVENTS
            WHERE {where_clause}
            ORDER BY year DESC, start_date DESC, event_id DESC
            LIMIT %s OFFSET %s
        """

        results = db.execute_query(query, tuple(params + [page_size, offset]))

        # Convert to Pydantic models
        events = [Event(**row) for row in results] if results else []

        # Build pagination metadata
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )

        return EventsResponse(events=events, pagination=pagination)

    except Error as e:
        logger.error(f"Database error in list_events: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in list_events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{event_id}",
    response_model=Event,
    summary="Get event by ID",
    description="Retrieve a single event by its database ID"
)
async def get_event(
    event_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get a single event by database ID

    **Path Parameters:**
    - `event_id`: Database primary key (id column)

    **Returns:**
    - Event object with all details

    **Errors:**
    - 404: Event not found
    - 500: Database error
    """

    try:
        query = """
            SELECT
                id, source, scraped_at, year, event_id, event_name, event_url,
                event_date, start_date, end_date, day_window,
                event_section, event_status, competition_state,
                has_wave_discipline, all_disciplines,
                country_flag, country_code, stars, event_image_url,
                created_at, updated_at
            FROM PWA_IWT_EVENTS
            WHERE id = %s
        """

        result = db.execute_query(query, (event_id,), fetch_one=True)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Event with id {event_id} not found"
            )

        return Event(**result)

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in get_event: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
