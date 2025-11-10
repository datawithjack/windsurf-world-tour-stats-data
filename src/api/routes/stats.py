"""
Site Statistics API Routes

Endpoints for retrieving site-wide statistics and metrics.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error

from ..database import DatabaseManager, get_db
from ..models import SiteStat, SiteStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get(
    "",
    response_model=SiteStatsResponse,
    summary="Get site-wide statistics",
    description="Retrieve aggregated statistics across all windsurf event data from SITE_STATS_VIEW"
)
async def get_site_stats(
    db: DatabaseManager = Depends(get_db)
):
    """
    Get site-wide statistics

    Returns all metrics from the SITE_STATS_VIEW database view, including
    statistics about events, athletes, results, and other aggregated data.

    **Returns:**
    - List of all available site statistics (metric/value pairs)
    - Timestamp when the statistics were retrieved

    **Example metrics:**
    - total_events: Total number of events in database
    - total_athletes: Total number of unified athlete profiles
    - total_results: Total competition results
    - And any other metrics defined in SITE_STATS_VIEW
    """
    try:
        # Query the SITE_STATS_VIEW
        query = """
            SELECT metric, value
            FROM SITE_STATS_VIEW
        """

        logger.info("Fetching site statistics from SITE_STATS_VIEW")
        results = db.execute_query(query)

        # Convert to Pydantic models
        stats = [SiteStat(**row) for row in results] if results else []

        logger.info(f"Retrieved {len(stats)} site statistics")

        return SiteStatsResponse(
            stats=stats,
            generated_at=datetime.utcnow()
        )

    except Error as e:
        logger.error(f"Database error fetching site statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve site statistics from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching site statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while retrieving site statistics"
        )
