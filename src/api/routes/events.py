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
    MoveTypeStat, BestScoredBy, ScoreEntry, JumpScoreEntry, EventStatsMetadata,
    AthleteListResponse, AthleteListItem, AthleteListMetadata,
    AthleteStatsResponse, AthleteProfile, AthleteSummaryStats,
    BestHeatScore, BestJumpScore, BestWaveScore,
    MoveTypeScore, HeatScore, JumpScore, WaveScore, AthleteStatsMetadata
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
    - Complete lists of ALL heat, jump, and wave scores (sorted by score descending)

    Each score entry includes `athlete_id` (unified integer ID) for navigation to athlete profiles.
    Frontend handles pagination (10/25/50 rows) using the complete dataset.

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
        # Join through unified ATHLETES table to get correct sex when heat results sex field is empty
        best_heat_query = """
            SELECT
                ROUND(hr.result_total, 2) as score,
                hr.athlete_name,
                asi_hr.athlete_id,
                hr.heat_id as heat_number
            FROM PWA_IWT_HEAT_RESULTS hr
            INNER JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
            INNER JOIN ATHLETE_SOURCE_IDS asi_hr ON hr.source = asi_hr.source AND hr.athlete_id = asi_hr.source_id
            INNER JOIN PWA_IWT_RESULTS r ON r.source = e.source AND r.event_id = e.event_id
            INNER JOIN ATHLETE_SOURCE_IDS asi_r ON r.source = asi_r.source AND r.athlete_id = asi_r.source_id
            WHERE e.id = %s AND r.sex = %s AND asi_hr.athlete_id = asi_r.athlete_id
            ORDER BY hr.result_total DESC
            LIMIT 1
        """
        best_heat = db.execute_query(best_heat_query, (event_id, sex), fetch_one=True)

        # 3a. Get all heat scores tied for best and populate nested fields
        best_heat_score_obj = None
        if best_heat:
            best_heat_score_value = best_heat['score']
            all_best_heats_query = """
                SELECT
                    ROUND(hr.result_total, 2) as score,
                    hr.athlete_name,
                    asi_hr.athlete_id,
                    hr.heat_id as heat_number
                FROM PWA_IWT_HEAT_RESULTS hr
                INNER JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
                INNER JOIN ATHLETE_SOURCE_IDS asi_hr ON hr.source = asi_hr.source AND hr.athlete_id = asi_hr.source_id
                INNER JOIN PWA_IWT_RESULTS r ON r.source = e.source AND r.event_id = e.event_id
                INNER JOIN ATHLETE_SOURCE_IDS asi_r ON r.source = asi_r.source AND r.athlete_id = asi_r.source_id
                WHERE e.id = %s AND r.sex = %s AND asi_hr.athlete_id = asi_r.athlete_id
                  AND ROUND(hr.result_total, 2) = %s
                ORDER BY hr.athlete_name
            """
            all_best_heats = db.execute_query(all_best_heats_query, (event_id, sex, best_heat_score_value))

            # Create ScoreDetail with nested tied scores if multiple
            if all_best_heats and len(all_best_heats) > 1:
                # Convert all tied scores to ScoreDetail objects (excluding has_multiple_tied and all_tied_scores)
                all_tied = [ScoreDetail(**{**row, 'has_multiple_tied': False, 'all_tied_scores': None}) for row in all_best_heats]
                best_heat_score_obj = ScoreDetail(
                    **best_heat,
                    has_multiple_tied=True,
                    all_tied_scores=all_tied
                )
            else:
                best_heat_score_obj = ScoreDetail(**best_heat, has_multiple_tied=False, all_tied_scores=None)

        # 3b. Get all jump scores tied for best and populate nested fields
        best_jump_score_obj = None
        if best_jump:
            best_jump_score_value = best_jump['score']
            all_best_jumps_query = """
                SELECT
                    score,
                    athlete_name,
                    athlete_id,
                    heat_id as heat_number,
                    move_type
                FROM EVENT_STATS_VIEW
                WHERE event_db_id = %s AND sex = %s
                  AND move_type != 'Wave'
                  AND score = %s
                ORDER BY athlete_name
            """
            all_best_jumps = db.execute_query(all_best_jumps_query, (event_id, sex, best_jump_score_value))

            # Create JumpScoreDetail with nested tied scores if multiple
            if all_best_jumps and len(all_best_jumps) > 1:
                all_tied = [JumpScoreDetail(**{**row, 'has_multiple_tied': False, 'all_tied_scores': None}) for row in all_best_jumps]
                best_jump_score_obj = JumpScoreDetail(
                    **best_jump,
                    has_multiple_tied=True,
                    all_tied_scores=all_tied
                )
            else:
                best_jump_score_obj = JumpScoreDetail(**best_jump, has_multiple_tied=False, all_tied_scores=None)

        # 3c. Get all wave scores tied for best and populate nested fields
        best_wave_score_obj = None
        if best_wave:
            best_wave_score_value = best_wave['score']
            all_best_waves_query = """
                SELECT
                    score,
                    athlete_name,
                    athlete_id,
                    heat_id as heat_number
                FROM EVENT_STATS_VIEW
                WHERE event_db_id = %s AND sex = %s
                  AND move_type = 'Wave'
                  AND score = %s
                ORDER BY athlete_name
            """
            all_best_waves = db.execute_query(all_best_waves_query, (event_id, sex, best_wave_score_value))

            # Create ScoreDetail with nested tied scores if multiple
            if all_best_waves and len(all_best_waves) > 1:
                all_tied = [ScoreDetail(**{**row, 'has_multiple_tied': False, 'all_tied_scores': None}) for row in all_best_waves]
                best_wave_score_obj = ScoreDetail(
                    **best_wave,
                    has_multiple_tied=True,
                    all_tied_scores=all_tied
                )
            else:
                best_wave_score_obj = ScoreDetail(**best_wave, has_multiple_tied=False, all_tied_scores=None)

        # 4. Get all heat scores (sorted by score descending)
        heat_scores_query = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY hr.result_total DESC) as `rank`,
                hr.athlete_name,
                asi_hr.athlete_id,
                ROUND(hr.result_total, 2) as score,
                hr.heat_id as heat_number
            FROM PWA_IWT_HEAT_RESULTS hr
            INNER JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
            INNER JOIN ATHLETE_SOURCE_IDS asi_hr ON hr.source = asi_hr.source AND hr.athlete_id = asi_hr.source_id
            INNER JOIN PWA_IWT_RESULTS r ON r.source = e.source AND r.event_id = e.event_id
            INNER JOIN ATHLETE_SOURCE_IDS asi_r ON r.source = asi_r.source AND r.athlete_id = asi_r.source_id
            WHERE e.id = %s AND r.sex = %s AND asi_hr.athlete_id = asi_r.athlete_id
            ORDER BY hr.result_total DESC
        """
        heat_scores = db.execute_query(heat_scores_query, (event_id, sex))
        top_heat_scores = [ScoreEntry(**row) for row in heat_scores] if heat_scores else []

        # 5. Get all jump scores (non-Wave, sorted by score descending)
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

        # 6. Get all wave scores (sorted by score descending)
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
            best_heat_score=best_heat_score_obj,
            best_jump_score=best_jump_score_obj,
            best_wave_score=best_wave_score_obj
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


@router.get(
    "/{event_id}/athletes",
    response_model=AthleteListResponse,
    summary="List athletes in event",
    description="Get list of all athletes who competed in a specific event for a specific division"
)
async def list_event_athletes(
    event_id: int,
    sex: str = Query("Women", description="Gender division filter ('Women' or 'Men')"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get list of athletes who competed in an event

    Returns all athletes for a specific division (Men/Women) with basic stats:
    - Final placement
    - Total heats competed
    - Best heat score

    **Path Parameters:**
    - `event_id`: Database primary key (id column from PWA_IWT_EVENTS)

    **Query Parameters:**
    - `sex`: Gender division ('Women' or 'Men', default: 'Women')

    **Returns:**
    - AthleteListResponse with athletes sorted by overall_position ascending

    **Errors:**
    - 400: Invalid sex parameter
    - 404: Event not found
    - 500: Database error
    """

    try:
        # Validate sex parameter
        if sex not in ["Women", "Men"]:
            raise HTTPException(
                status_code=400,
                detail="sex must be 'Women' or 'Men'"
            )

        # 1. Verify event exists and get event name
        event_query = """
            SELECT id, event_name
            FROM PWA_IWT_EVENTS
            WHERE id = %s
        """
        event_result = db.execute_query(event_query, (event_id,), fetch_one=True)

        if not event_result:
            raise HTTPException(
                status_code=404,
                detail=f"Event with id {event_id} not found"
            )

        event_name = event_result['event_name']

        # 2. Get list of athletes who competed in this event
        athletes_query = """
            SELECT
                a.id as athlete_id,
                a.primary_name as name,
                a.nationality as country,
                a.nationality as country_code,
                CAST(r.place AS UNSIGNED) as overall_position,
                COALESCE(a.pwa_sail_number, r.sail_number) as sail_number,
                COALESCE(a.liveheats_image_url, a.pwa_profile_url) as profile_image,
                COUNT(DISTINCT hr.heat_id) as total_heats,
                ROUND(COALESCE(MAX(hr.result_total), 0), 2) as best_heat_score
            FROM PWA_IWT_RESULTS r
            JOIN PWA_IWT_EVENTS e ON r.source = e.source AND r.event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON r.source = asi.source AND r.athlete_id = asi.source_id
            JOIN ATHLETES a ON asi.athlete_id = a.id
            LEFT JOIN (
                SELECT hr.*, asi2.athlete_id as unified_athlete_id
                FROM PWA_IWT_HEAT_RESULTS hr
                JOIN ATHLETE_SOURCE_IDS asi2 ON hr.source = asi2.source AND hr.athlete_id = asi2.source_id
            ) hr ON hr.pwa_event_id = r.event_id AND hr.unified_athlete_id = a.id
            WHERE e.id = %s AND r.sex = %s
            GROUP BY a.id, a.primary_name, a.nationality, sail_number, profile_image, overall_position
            ORDER BY overall_position ASC
        """

        athletes_results = db.execute_query(athletes_query, (event_id, sex))

        # Convert to Pydantic models
        athletes = []
        if athletes_results:
            for row in athletes_results:
                athletes.append(AthleteListItem(
                    athlete_id=row['athlete_id'],
                    name=row['name'],
                    country=row['country'] or 'Unknown',
                    country_code=row['country_code'] or 'XX',
                    overall_position=row['overall_position'],
                    sail_number=row['sail_number'],
                    profile_image=row['profile_image'],
                    total_heats=row['total_heats'],
                    best_heat_score=row['best_heat_score']
                ))

        # Build metadata
        metadata = AthleteListMetadata(
            total_athletes=len(athletes),
            generated_at=datetime.utcnow()
        )

        return AthleteListResponse(
            event_id=event_id,
            event_name=event_name,
            sex=sex,
            athletes=athletes,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in list_event_athletes: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in list_event_athletes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{event_id}/athletes/{athlete_id}/stats",
    response_model=AthleteStatsResponse,
    summary="Get athlete statistics for event",
    description="Get comprehensive statistics for a specific athlete in a specific event"
)
async def get_athlete_event_stats(
    event_id: int,
    athlete_id: int,
    sex: str = Query(None, description="Gender division filter ('Women' or 'Men', optional - auto-detect)"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get detailed athlete statistics for an event

    Returns comprehensive performance statistics including:
    - Athlete profile
    - Summary stats (best heat, jump, wave with opponents)
    - Move type analysis (best/avg for each move)
    - All heat scores with elimination type
    - All jump scores (sorted desc)
    - All wave scores (sorted desc)

    **Path Parameters:**
    - `event_id`: Database primary key (id column from PWA_IWT_EVENTS)
    - `athlete_id`: Unified athlete ID (id from ATHLETES table)

    **Query Parameters:**
    - `sex`: Gender division ('Women' or 'Men', optional - will auto-detect if not provided)

    **Returns:**
    - AthleteStatsResponse with complete athlete statistics

    **Errors:**
    - 400: Invalid sex parameter or gender mismatch
    - 404: Event not found or athlete didn't compete in event
    - 500: Database error
    """

    try:
        # Validate sex parameter if provided
        if sex is not None and sex not in ["Women", "Men"]:
            raise HTTPException(
                status_code=400,
                detail="sex must be 'Women' or 'Men'"
            )

        # 1. Verify event exists
        event_query = """
            SELECT id, event_name
            FROM PWA_IWT_EVENTS
            WHERE id = %s
        """
        event_result = db.execute_query(event_query, (event_id,), fetch_one=True)

        if not event_result:
            raise HTTPException(
                status_code=404,
                detail=f"Event with id {event_id} not found"
            )

        event_name = event_result['event_name']

        # 2. Get athlete profile and result (auto-detect sex if not provided)
        if sex is None:
            # Auto-detect sex from results
            profile_query = """
                SELECT
                    a.id as athlete_id,
                    a.primary_name as name,
                    a.nationality as country,
                    a.nationality as country_code,
                    COALESCE(a.liveheats_image_url, a.pwa_profile_url) as profile_image,
                    a.pwa_sponsors as sponsors,
                    COALESCE(a.pwa_sail_number, r.sail_number) as sail_number,
                    CAST(r.place AS UNSIGNED) as overall_position,
                    r.sex
                FROM ATHLETES a
                JOIN ATHLETE_SOURCE_IDS asi ON a.id = asi.athlete_id
                JOIN PWA_IWT_RESULTS r ON r.source = asi.source AND r.athlete_id = asi.source_id
                JOIN PWA_IWT_EVENTS e ON r.source = e.source AND r.event_id = e.event_id
                WHERE a.id = %s AND e.id = %s
                LIMIT 1
            """
            profile_result = db.execute_query(profile_query, (athlete_id, event_id), fetch_one=True)
        else:
            # Use provided sex
            profile_query = """
                SELECT
                    a.id as athlete_id,
                    a.primary_name as name,
                    a.nationality as country,
                    a.nationality as country_code,
                    COALESCE(a.liveheats_image_url, a.pwa_profile_url) as profile_image,
                    a.pwa_sponsors as sponsors,
                    COALESCE(a.pwa_sail_number, r.sail_number) as sail_number,
                    CAST(r.place AS UNSIGNED) as overall_position,
                    r.sex
                FROM ATHLETES a
                JOIN ATHLETE_SOURCE_IDS asi ON a.id = asi.athlete_id
                JOIN PWA_IWT_RESULTS r ON r.source = asi.source AND r.athlete_id = asi.source_id
                JOIN PWA_IWT_EVENTS e ON r.source = e.source AND r.event_id = e.event_id
                WHERE a.id = %s AND e.id = %s AND r.sex = %s
                LIMIT 1
            """
            profile_result = db.execute_query(profile_query, (athlete_id, event_id, sex), fetch_one=True)

        if not profile_result:
            raise HTTPException(
                status_code=404,
                detail=f"Athlete {athlete_id} did not compete in event {event_id}" + (f" ({sex} division)" if sex else "")
            )

        # Extract sex from result
        detected_sex = profile_result['sex']

        # 3. Get best heat score with opponents
        best_heat_query = """
            SELECT
                hr.heat_id as heat,
                ROUND(hr.result_total, 2) as score,
                hp.round_name,
                GROUP_CONCAT(DISTINCT opp_hr.athlete_name ORDER BY opp_hr.athlete_name SEPARATOR ', ') as opponents_str
            FROM PWA_IWT_HEAT_RESULTS hr
            JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON hr.source = asi.source AND hr.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = hr.heat_id
            LEFT JOIN PWA_IWT_HEAT_RESULTS opp_hr
                ON opp_hr.heat_id = hr.heat_id
                AND opp_hr.athlete_id != hr.athlete_id
            WHERE asi.athlete_id = %s AND e.id = %s
            GROUP BY hr.heat_id, hr.result_total, hp.round_name
            ORDER BY hr.result_total DESC
            LIMIT 1
        """
        best_heat_result = db.execute_query(best_heat_query, (athlete_id, event_id), fetch_one=True)

        # 4. Get best jump score with opponents and move type
        best_jump_query = """
            SELECT
                s.heat_id as heat,
                ROUND(s.score, 2) as score,
                hp.round_name,
                COALESCE(st.Type_Name, s.type) as move,
                GROUP_CONCAT(DISTINCT opp_s.athlete_name ORDER BY opp_s.athlete_name SEPARATOR ', ') as opponents_str
            FROM PWA_IWT_HEAT_SCORES s
            JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = s.heat_id
            LEFT JOIN SCORE_TYPES st ON st.Type = s.type
            LEFT JOIN PWA_IWT_HEAT_SCORES opp_s
                ON opp_s.heat_id = s.heat_id
                AND opp_s.athlete_id != s.athlete_id
            WHERE asi.athlete_id = %s AND e.id = %s AND s.type != 'Wave'
            GROUP BY s.heat_id, s.score, s.type, hp.round_name, st.Type_Name
            ORDER BY s.score DESC
            LIMIT 1
        """
        best_jump_result = db.execute_query(best_jump_query, (athlete_id, event_id), fetch_one=True)

        # 5. Get best wave score with opponents
        best_wave_query = """
            SELECT
                s.heat_id as heat,
                ROUND(s.score, 2) as score,
                hp.round_name,
                GROUP_CONCAT(DISTINCT opp_s.athlete_name ORDER BY opp_s.athlete_name SEPARATOR ', ') as opponents_str
            FROM PWA_IWT_HEAT_SCORES s
            JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = s.heat_id
            LEFT JOIN PWA_IWT_HEAT_SCORES opp_s
                ON opp_s.heat_id = s.heat_id
                AND opp_s.athlete_id != s.athlete_id
            WHERE asi.athlete_id = %s AND e.id = %s AND s.type = 'Wave'
            GROUP BY s.heat_id, s.score, hp.round_name
            ORDER BY s.score DESC
            LIMIT 1
        """
        best_wave_result = db.execute_query(best_wave_query, (athlete_id, event_id), fetch_one=True)

        # 6. Get move type scores (includes Wave and all jump types)
        move_type_query = """
            SELECT
                COALESCE(st.Type_Name, s.type) as move_type,
                ROUND(MAX(s.score), 2) as best_score,
                ROUND(AVG(s.score), 2) as average_score,
                (
                    SELECT ROUND(AVG(s2.score), 2)
                    FROM PWA_IWT_HEAT_SCORES s2
                    JOIN PWA_IWT_EVENTS e2 ON s2.source = e2.source AND s2.pwa_event_id = e2.event_id
                    JOIN ATHLETE_SOURCE_IDS asi2 ON s2.source = asi2.source AND s2.athlete_id = asi2.source_id
                    JOIN ATHLETE_SOURCE_IDS asi3 ON asi3.athlete_id = asi2.athlete_id AND asi3.source = e2.source
                    JOIN PWA_IWT_RESULTS r2 ON r2.source = e2.source AND r2.event_id = e2.event_id
                        AND r2.athlete_id = asi3.source_id
                    WHERE e2.id = %s
                      AND r2.sex = %s
                      AND s2.type = s.type
                      AND COALESCE(s2.counting, FALSE) = TRUE
                ) as fleet_average
            FROM PWA_IWT_HEAT_SCORES s
            JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
            LEFT JOIN SCORE_TYPES st ON st.Type = s.type
            WHERE asi.athlete_id = %s AND e.id = %s
            GROUP BY s.type, st.Type_Name
            ORDER BY best_score DESC
        """
        move_type_results = db.execute_query(move_type_query, (event_id, detected_sex, athlete_id, event_id))

        # 7. Get all heat scores with elimination type
        heat_scores_query = """
            SELECT
                hr.heat_id as heat_number,
                hp.round_name,
                ROUND(hr.result_total, 2) as score,
                hr.place,
                CASE
                    WHEN hp.elimination_name IS NULL OR hp.elimination_name = '' THEN NULL
                    WHEN LOWER(hp.elimination_name) LIKE '%double elimination%' THEN 'Double'
                    WHEN LOWER(hp.elimination_name) LIKE '%elimination%' THEN 'Single'
                    ELSE NULL
                END as elimination_type
            FROM PWA_IWT_HEAT_RESULTS hr
            JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON hr.source = asi.source AND hr.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = hr.heat_id
            WHERE asi.athlete_id = %s AND e.id = %s
            ORDER BY hr.result_total DESC
        """
        heat_scores_results = db.execute_query(heat_scores_query, (athlete_id, event_id))

        # 8. Get all jump scores
        jump_scores_query = """
            SELECT
                s.heat_id as heat_number,
                hp.round_name,
                COALESCE(st.Type_Name, s.type) as move,
                ROUND(s.score, 2) as score,
                COALESCE(s.counting, FALSE) as counting
            FROM PWA_IWT_HEAT_SCORES s
            JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = s.heat_id
            LEFT JOIN SCORE_TYPES st ON st.Type = s.type
            WHERE asi.athlete_id = %s AND e.id = %s AND s.type != 'Wave'
            ORDER BY s.score DESC
        """
        jump_scores_results = db.execute_query(jump_scores_query, (athlete_id, event_id))

        # 9. Get all wave scores
        wave_scores_query = """
            SELECT
                s.heat_id as heat_number,
                hp.round_name,
                ROUND(s.score, 2) as score,
                COALESCE(s.counting, FALSE) as counting
            FROM PWA_IWT_HEAT_SCORES s
            JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
            LEFT JOIN PWA_IWT_HEAT_PROGRESSION hp ON hp.heat_id = s.heat_id
            WHERE asi.athlete_id = %s AND e.id = %s AND s.type = 'Wave'
            ORDER BY s.score DESC
        """
        wave_scores_results = db.execute_query(wave_scores_query, (athlete_id, event_id))

        # Build response models
        profile = AthleteProfile(
            name=profile_result['name'],
            country=profile_result['country'] or 'Unknown',
            country_code=profile_result['country_code'] or 'XX',
            profile_image=profile_result['profile_image'],
            sponsors=profile_result['sponsors'],
            sail_number=profile_result['sail_number']
        )

        # Parse opponents strings into lists
        def parse_opponents(opponents_str):
            if opponents_str:
                return [name.strip() for name in opponents_str.split(',')]
            return None

        best_heat_score = BestHeatScore(
            score=best_heat_result['score'],
            heat=best_heat_result['heat'],
            round_name=best_heat_result.get('round_name'),
            opponents=parse_opponents(best_heat_result.get('opponents_str'))
        ) if best_heat_result else BestHeatScore(score=0.0, heat='', round_name=None, opponents=None)

        best_jump_score = BestJumpScore(
            score=best_jump_result['score'],
            heat=best_jump_result['heat'],
            round_name=best_jump_result.get('round_name'),
            move=best_jump_result['move'],
            opponents=parse_opponents(best_jump_result.get('opponents_str'))
        ) if best_jump_result else BestJumpScore(score=0.0, heat='', round_name=None, move='', opponents=None)

        best_wave_score = BestWaveScore(
            score=best_wave_result['score'],
            heat=best_wave_result['heat'],
            round_name=best_wave_result.get('round_name'),
            opponents=parse_opponents(best_wave_result.get('opponents_str'))
        ) if best_wave_result else BestWaveScore(score=0.0, heat='', round_name=None, opponents=None)

        summary_stats = AthleteSummaryStats(
            overall_position=profile_result['overall_position'],
            best_heat_score=best_heat_score,
            best_jump_score=best_jump_score,
            best_wave_score=best_wave_score
        )

        move_type_scores = [MoveTypeScore(**row) for row in move_type_results] if move_type_results else []
        heat_scores = [HeatScore(**row) for row in heat_scores_results] if heat_scores_results else []

        # Handle None values in counting field
        jump_scores = []
        if jump_scores_results:
            for row in jump_scores_results:
                row['counting'] = bool(row['counting']) if row['counting'] is not None else False
                jump_scores.append(JumpScore(**row))

        wave_scores = []
        if wave_scores_results:
            for row in wave_scores_results:
                row['counting'] = bool(row['counting']) if row['counting'] is not None else False
                wave_scores.append(WaveScore(**row))

        metadata = AthleteStatsMetadata(
            total_heats=len(heat_scores),
            total_jumps=len(jump_scores),
            total_waves=len(wave_scores),
            generated_at=datetime.utcnow()
        )

        return AthleteStatsResponse(
            event_id=event_id,
            event_name=event_name,
            sex=detected_sex,
            athlete_id=athlete_id,
            profile=profile,
            summary_stats=summary_stats,
            move_type_scores=move_type_scores,
            heat_scores=heat_scores,
            jump_scores=jump_scores,
            wave_scores=wave_scores,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in get_athlete_event_stats: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_athlete_event_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
