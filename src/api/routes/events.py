"""
Events API Routes

Endpoints for retrieving windsurf competition event data.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from mysql.connector import Error

from ..database import DatabaseManager, get_db
from ..models import (
    Event, EventsResponse, PaginationMeta,
    EventStatsResponse, SummaryStats, ScoreDetail, JumpScoreDetail,
    MoveTypeStat, BestScoredBy, ScoreEntry, JumpScoreEntry, EventStatsMetadata
)
from ..config import settings
from datetime import datetime

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
            FROM EVENT_INFO_VIEW
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
                id, source, year, event_id, event_name, event_url,
                event_date, start_date, end_date, day_window,
                event_section, event_status, competition_state,
                has_wave_discipline, all_disciplines,
                country_flag, country_code, stars, event_image_url,
                total_athletes, total_men, total_women
            FROM EVENT_INFO_VIEW
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
                id, source, year, event_id, event_name, event_url,
                event_date, start_date, end_date, day_window,
                event_section, event_status, competition_state,
                has_wave_discipline, all_disciplines,
                country_flag, country_code, stars, event_image_url,
                total_athletes, total_men, total_women
            FROM EVENT_INFO_VIEW
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


@router.get(
    "/{event_id}/stats",
    response_model=EventStatsResponse,
    summary="Get event statistics",
    description="Get comprehensive statistics for a specific event including best scores, move type analysis, and top scores tables"
)
async def get_event_stats(
    event_id: int,
    sex: str = Query("Women", description="Gender division filter ('Women' or 'Men')"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get event statistics

    Returns pre-aggregated statistics for an event including:
    - Summary stats (best heat, jump, and wave scores)
    - Move type statistics (best and average for each move type)
    - Complete lists of all heat, jump, and wave scores (sorted descending)

    **Path Parameters:**
    - `event_id`: Database primary key (id column from PWA_IWT_EVENTS)

    **Query Parameters:**
    - `sex`: Gender division ('Women' or 'Men', default: 'Women')

    **Returns:**
    - EventStatsResponse with complete statistics

    **Errors:**
    - 400: Invalid sex parameter
    - 404: Event not found or no data for specified division
    - 500: Database error
    """

    try:
        # Validate sex parameter
        if sex not in ["Women", "Men"]:
            raise HTTPException(
                status_code=400,
                detail="sex must be 'Women' or 'Men'"
            )

        # 1. Verify event exists and get event name (using the view)
        event_query = """
            SELECT DISTINCT event_db_id, event_name
            FROM EVENT_STATS_VIEW
            WHERE event_db_id = %s
            LIMIT 1
        """
        event_result = db.execute_query(event_query, (event_id,), fetch_one=True)

        if not event_result:
            raise HTTPException(
                status_code=404,
                detail=f"Event with id {event_id} not found"
            )

        event_name = event_result['event_name']

        # 2. Get move type statistics with best scores (single query!)
        move_stats_query = """
            WITH RankedScores AS (
                SELECT
                    move_type,
                    score,
                    athlete_name,
                    athlete_id,
                    heat_id,
                    ROW_NUMBER() OVER (PARTITION BY move_type ORDER BY score DESC) as rn
                FROM EVENT_STATS_VIEW
                WHERE event_db_id = %s AND sex = %s
            )
            SELECT
                rs.move_type,
                rs.score as best_score,
                (SELECT ROUND(AVG(score), 2)
                 FROM EVENT_STATS_VIEW
                 WHERE event_db_id = %s AND sex = %s AND move_type = rs.move_type) as average_score,
                rs.athlete_name,
                rs.athlete_id,
                rs.heat_id as heat_number
            FROM RankedScores rs
            WHERE rs.rn = 1
            ORDER BY rs.score DESC
        """
        move_stats_results = db.execute_query(move_stats_query, (event_id, sex, event_id, sex))

        # Build move type stats and extract best scores for summary
        move_type_stats = []
        best_jump = None
        best_wave = None

        if move_stats_results:
            for stat in move_stats_results:
                # Build MoveTypeStat
                move_type_stats.append(MoveTypeStat(
                    move_type=stat['move_type'],
                    best_score=stat['best_score'],
                    average_score=stat['average_score'],
                    best_scored_by=BestScoredBy(
                        athlete_name=stat['athlete_name'],
                        athlete_id=stat['athlete_id'],
                        heat_number=stat['heat_number'],
                        score=stat['best_score']
                    )
                ))

                # Extract best jump (any non-Wave score)
                if stat['move_type'] != 'Wave' and (best_jump is None or stat['best_score'] > best_jump['score']):
                    best_jump = {
                        'score': stat['best_score'],
                        'athlete_name': stat['athlete_name'],
                        'athlete_id': stat['athlete_id'],
                        'heat_number': stat['heat_number'],
                        'move_type': stat['move_type']
                    }

                # Extract best wave
                if stat['move_type'] == 'Wave':
                    best_wave = {
                        'score': stat['best_score'],
                        'athlete_name': stat['athlete_name'],
                        'athlete_id': stat['athlete_id'],
                        'heat_number': stat['heat_number']
                    }

        # 3. Get best heat score (from heat results)
        best_heat_query = """
            SELECT
                ROUND(result_total, 2) as score,
                athlete_name,
                athlete_id,
                heat_id as heat_number
            FROM PWA_IWT_HEAT_RESULTS hr
            INNER JOIN PWA_IWT_EVENTS e ON hr.pwa_event_id = e.event_id
            WHERE e.id = %s AND hr.sex = %s
            ORDER BY result_total DESC
            LIMIT 1
        """
        best_heat = db.execute_query(best_heat_query, (event_id, sex), fetch_one=True)

        # 4. Get all heat scores
        heat_scores_query = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY result_total DESC) as `rank`,
                athlete_name,
                athlete_id,
                ROUND(result_total, 2) as score,
                heat_id as heat_number
            FROM PWA_IWT_HEAT_RESULTS hr
            INNER JOIN PWA_IWT_EVENTS e ON hr.pwa_event_id = e.event_id
            WHERE e.id = %s AND hr.sex = %s
            ORDER BY result_total DESC
        """
        heat_scores = db.execute_query(heat_scores_query, (event_id, sex))
        top_heat_scores = [ScoreEntry(**row) for row in heat_scores] if heat_scores else []

        # 5. Get all jump scores (non-Wave)
        jump_scores_query = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY score DESC) as `rank`,
                athlete_name,
                athlete_id,
                score,
                move_type,
                heat_id as heat_number
            FROM EVENT_STATS_VIEW
            WHERE event_db_id = %s
              AND sex = %s
              AND move_type != 'Wave'
            ORDER BY score DESC
        """
        jump_scores = db.execute_query(jump_scores_query, (event_id, sex))
        top_jump_scores = [JumpScoreEntry(**row) for row in jump_scores] if jump_scores else []

        # 6. Get all wave scores
        wave_scores_query = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY score DESC) as `rank`,
                athlete_name,
                athlete_id,
                score,
                heat_id as heat_number
            FROM EVENT_STATS_VIEW
            WHERE event_db_id = %s
              AND sex = %s
              AND move_type = 'Wave'
            ORDER BY score DESC
        """
        wave_scores = db.execute_query(wave_scores_query, (event_id, sex))
        top_wave_scores = [ScoreEntry(**row) for row in wave_scores] if wave_scores else []

        # 7. Get metadata
        metadata_query = """
            SELECT
                COUNT(DISTINCT heat_id) as total_heats,
                COUNT(DISTINCT athlete_id) as total_athletes
            FROM EVENT_STATS_VIEW
            WHERE event_db_id = %s AND sex = %s
        """
        metadata_result = db.execute_query(metadata_query, (event_id, sex), fetch_one=True)

        metadata = EventStatsMetadata(
            total_heats=metadata_result['total_heats'] if metadata_result else 0,
            total_athletes=metadata_result['total_athletes'] if metadata_result else 0,
            generated_at=datetime.utcnow()
        )

        # Build summary stats
        summary_stats = SummaryStats(
            best_heat_score=ScoreDetail(**best_heat) if best_heat else None,
            best_jump_score=JumpScoreDetail(**best_jump) if best_jump else None,
            best_wave_score=ScoreDetail(**best_wave) if best_wave else None
        )

        # Return complete response
        return EventStatsResponse(
            event_id=event_id,
            event_name=event_name,
            sex=sex,
            summary_stats=summary_stats,
            move_type_stats=move_type_stats,
            top_heat_scores=top_heat_scores,
            top_jump_scores=top_jump_scores,
            top_wave_scores=top_wave_scores,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in get_event_stats: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_event_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
