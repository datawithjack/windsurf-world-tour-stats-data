"""
Head-to-Head API Routes

Endpoints for comparing two athletes' performance in an event.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from mysql.connector import Error
from datetime import datetime

from ..database import DatabaseManager, get_db
from ..models import (
    HeadToHeadResponse, AthleteHeadToHeadStats, HeadToHeadComparison, ComparisonMetric
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Head-to-Head"])


def calculate_comparison_metric(athlete1_value: float, athlete2_value: float) -> ComparisonMetric:
    """
    Calculate comparison metric between two athlete values.

    Args:
        athlete1_value: First athlete's metric value
        athlete2_value: Second athlete's metric value

    Returns:
        ComparisonMetric with winner, difference, and both values
    """
    difference = abs(athlete1_value - athlete2_value)

    if athlete1_value > athlete2_value:
        winner = "athlete1"
    elif athlete2_value > athlete1_value:
        winner = "athlete2"
    else:
        winner = "tie"

    return ComparisonMetric(
        winner=winner,
        difference=round(difference, 2),
        athlete1_value=round(athlete1_value, 2),
        athlete2_value=round(athlete2_value, 2)
    )


@router.get(
    "/{event_id}/head-to-head",
    response_model=HeadToHeadResponse,
    summary="Compare two athletes in an event",
    description="Get head-to-head statistics comparing two athletes' performance in a specific event"
)
async def get_head_to_head(
    event_id: int,
    athlete1_id: int = Query(..., description="First athlete's unified ID"),
    athlete2_id: int = Query(..., description="Second athlete's unified ID"),
    division: str = Query(..., description="Division ('Women' or 'Men')"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get head-to-head comparison between two athletes in an event

    Returns comprehensive statistics for both athletes including:
    - Heat scores (best, average)
    - Jump scores (best, average counting)
    - Wave scores (best, average counting)
    - Heat wins
    - Comparison metrics with winners and differences

    **Path Parameters:**
    - `event_id`: Database primary key (id column from PWA_IWT_EVENTS)

    **Query Parameters:**
    - `athlete1_id`: First athlete's unified ID (from ATHLETES table)
    - `athlete2_id`: Second athlete's unified ID (from ATHLETES table)
    - `division`: Division ('Women' or 'Men')

    **Returns:**
    - HeadToHeadResponse with both athletes' stats and comparison metrics

    **Errors:**
    - 400: Invalid division or same athlete specified twice
    - 404: Event not found or athlete(s) didn't compete in event
    - 500: Database error
    """

    try:
        # Validate division parameter
        if division not in ["Women", "Men"]:
            raise HTTPException(
                status_code=400,
                detail="division must be 'Women' or 'Men'"
            )

        # Validate athletes are different
        if athlete1_id == athlete2_id:
            raise HTTPException(
                status_code=400,
                detail="athlete1_id and athlete2_id must be different"
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

        # 2. Get statistics for both athletes
        athlete_stats = {}

        for athlete_key, athlete_id in [("athlete1", athlete1_id), ("athlete2", athlete2_id)]:
            # Get athlete profile and placement
            profile_query = """
                SELECT
                    a.id as athlete_id,
                    a.primary_name as name,
                    a.nationality,
                    CAST(r.place AS UNSIGNED) as place,
                    COALESCE(a.liveheats_image_url, a.pwa_profile_url) as profile_image
                FROM ATHLETES a
                JOIN ATHLETE_SOURCE_IDS asi ON a.id = asi.athlete_id
                JOIN PWA_IWT_RESULTS r ON r.source = asi.source AND r.athlete_id = asi.source_id
                JOIN PWA_IWT_EVENTS e ON r.source = e.source AND r.event_id = e.event_id
                WHERE a.id = %s AND e.id = %s AND r.sex = %s
                LIMIT 1
            """
            profile = db.execute_query(profile_query, (athlete_id, event_id, division), fetch_one=True)

            if not profile:
                raise HTTPException(
                    status_code=404,
                    detail=f"Athlete {athlete_id} did not compete in event {event_id} ({division} division)"
                )

            # Get heat score statistics
            heat_stats_query = """
                SELECT
                    ROUND(MAX(hr.result_total), 2) as heat_scores_best,
                    ROUND(AVG(hr.result_total), 2) as heat_scores_avg,
                    COUNT(CASE WHEN hr.place = 1 THEN 1 END) as heat_wins
                FROM PWA_IWT_HEAT_RESULTS hr
                JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON hr.source = asi.source AND hr.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s
            """
            heat_stats = db.execute_query(heat_stats_query, (athlete_id, event_id), fetch_one=True)

            # Get jump score statistics (only counting scores)
            jump_stats_query = """
                SELECT
                    ROUND(MAX(s.score), 2) as jumps_best,
                    ROUND(AVG(CASE WHEN COALESCE(s.counting, FALSE) = TRUE THEN s.score END), 2) as jumps_avg_counting
                FROM PWA_IWT_HEAT_SCORES s
                JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s AND s.type != 'Wave'
            """
            jump_stats = db.execute_query(jump_stats_query, (athlete_id, event_id), fetch_one=True)

            # Get wave score statistics (only counting scores)
            wave_stats_query = """
                SELECT
                    ROUND(MAX(s.score), 2) as waves_best,
                    ROUND(AVG(CASE WHEN COALESCE(s.counting, FALSE) = TRUE THEN s.score END), 2) as waves_avg_counting
                FROM PWA_IWT_HEAT_SCORES s
                JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s AND s.type = 'Wave'
            """
            wave_stats = db.execute_query(wave_stats_query, (athlete_id, event_id), fetch_one=True)

            # Combine all stats
            athlete_stats[athlete_key] = AthleteHeadToHeadStats(
                athlete_id=profile['athlete_id'],
                name=profile['name'],
                nationality=profile['nationality'],
                place=profile['place'],
                profile_image=profile['profile_image'],
                heat_scores_best=heat_stats['heat_scores_best'] or 0.0,
                heat_scores_avg=heat_stats['heat_scores_avg'] or 0.0,
                jumps_best=jump_stats['jumps_best'] or 0.0,
                jumps_avg_counting=jump_stats['jumps_avg_counting'] or 0.0,
                waves_best=wave_stats['waves_best'] or 0.0,
                waves_avg_counting=wave_stats['waves_avg_counting'] or 0.0,
                heat_wins=heat_stats['heat_wins'] or 0
            )

        # 3. Calculate comparison metrics
        athlete1 = athlete_stats["athlete1"]
        athlete2 = athlete_stats["athlete2"]

        comparison = HeadToHeadComparison(
            heat_scores_best=calculate_comparison_metric(
                athlete1.heat_scores_best, athlete2.heat_scores_best
            ),
            heat_scores_avg=calculate_comparison_metric(
                athlete1.heat_scores_avg, athlete2.heat_scores_avg
            ),
            jumps_best=calculate_comparison_metric(
                athlete1.jumps_best, athlete2.jumps_best
            ),
            jumps_avg_counting=calculate_comparison_metric(
                athlete1.jumps_avg_counting, athlete2.jumps_avg_counting
            ),
            waves_best=calculate_comparison_metric(
                athlete1.waves_best, athlete2.waves_best
            ),
            waves_avg_counting=calculate_comparison_metric(
                athlete1.waves_avg_counting, athlete2.waves_avg_counting
            ),
            heat_wins=calculate_comparison_metric(
                float(athlete1.heat_wins), float(athlete2.heat_wins)
            )
        )

        # 4. Build and return response
        return HeadToHeadResponse(
            event_id=event_id,
            event_name=event_name,
            division=division,
            athlete1=athlete1,
            athlete2=athlete2,
            comparison=comparison,
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Error as e:
        logger.error(f"Database error in get_head_to_head: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_head_to_head: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
