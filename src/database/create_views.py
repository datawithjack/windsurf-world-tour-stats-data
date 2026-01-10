"""
Create database views for windsurf competition data.

This script creates materialized views that join athlete profiles with event results,
providing enriched data for analysis and reporting.
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """Create connection to Oracle MySQL Heatwave database"""
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        connect_timeout=30
    )
    return conn

def create_athlete_results_view(cursor):
    """
    Create a view that combines athlete profiles with competition results.

    This view joins:
    - PWA_IWT_RESULTS (competition placements)
    - ATHLETES (unified athlete profiles)
    - ATHLETE_SOURCE_IDS (source ID mappings)
    - PWA_IWT_EVENTS (event details)

    Features:
    - Athlete primary name and nationality from unified profile
    - Profile picture (PWA if available, otherwise LiveHeats)
    - Event details (name, location, year, stars)
    - Result placement and division
    """

    print("\nCreating ATHLETE_RESULTS_VIEW...")

    # Drop view if exists
    cursor.execute("DROP VIEW IF EXISTS ATHLETE_RESULTS_VIEW")

    # Create view
    view_sql = """
    CREATE VIEW ATHLETE_RESULTS_VIEW AS
    SELECT
        -- Result identifiers
        r.id AS result_id,
        r.source AS result_source,

        -- Athlete information (from unified ATHLETES table)
        a.id AS athlete_id,
        a.primary_name AS athlete_name,
        a.nationality,
        a.year_of_birth,

        -- Profile pictures (PWA preferred, fallback to LiveHeats)
        COALESCE(a.pwa_profile_url, a.liveheats_image_url) AS profile_picture_url,
        a.pwa_profile_url AS pwa_picture_url,
        a.liveheats_image_url AS liveheats_picture_url,

        -- Additional athlete details
        a.pwa_sail_number,
        a.pwa_sponsors,
        a.match_stage,
        a.match_score,

        -- Event information
        e.id AS event_db_id,
        e.event_id,
        e.event_name,
        e.year AS event_year,
        e.event_date,
        e.start_date,
        e.end_date,
        e.country_code,
        e.stars,
        e.event_image_url,
        e.event_url,

        -- Result details
        r.division_label,
        r.division_code,
        r.sex,
        r.place AS placement,

        -- Source-specific IDs for reference
        r.athlete_id AS source_athlete_id,
        r.sail_number AS result_sail_number,

        -- Metadata
        r.scraped_at AS result_scraped_at,
        r.created_at AS result_created_at

    FROM PWA_IWT_RESULTS r

    -- Join to get source-specific athlete ID mapping
    LEFT JOIN ATHLETE_SOURCE_IDS asi
        ON r.source = asi.source
        AND r.athlete_id = asi.source_id

    -- Join to unified athlete profile
    LEFT JOIN ATHLETES a
        ON asi.athlete_id = a.id

    -- Join to event details
    LEFT JOIN PWA_IWT_EVENTS e
        ON r.source = e.source
        AND r.event_id = e.event_id

    WHERE r.athlete_id IS NOT NULL
      AND r.athlete_id != ''

    ORDER BY e.year DESC, e.event_id, r.division_code, CAST(r.place AS UNSIGNED)
    """

    cursor.execute(view_sql)
    print("  [OK] ATHLETE_RESULTS_VIEW created successfully")

def create_athlete_heat_results_view(cursor):
    """
    Create a view for heat-by-heat results with athlete profiles.

    Joins heat results with athlete data for detailed competition analysis.
    """

    print("\nCreating ATHLETE_HEAT_RESULTS_VIEW...")

    # Drop view if exists
    cursor.execute("DROP VIEW IF EXISTS ATHLETE_HEAT_RESULTS_VIEW")

    # Create view
    view_sql = """
    CREATE VIEW ATHLETE_HEAT_RESULTS_VIEW AS
    SELECT
        -- Heat result identifiers
        hr.id AS heat_result_id,
        hr.source AS result_source,

        -- Athlete information
        a.id AS athlete_id,
        a.primary_name AS athlete_name,
        a.nationality,
        a.year_of_birth,
        COALESCE(a.pwa_profile_url, a.liveheats_image_url) AS profile_picture_url,

        -- Event information
        e.id AS event_db_id,
        e.event_id,
        e.event_name,
        e.year AS event_year,
        e.country_code,
        e.stars,

        -- Heat details
        hr.heat_id,
        hr.round,
        hr.round_position,

        -- Heat result
        hr.place AS heat_place,
        hr.result_total AS heat_score,
        hr.win_by,
        hr.needs,

        -- Division
        hr.pwa_division_code AS division_code,
        hr.sex,

        -- Source-specific IDs
        hr.athlete_id AS source_athlete_id,
        hr.sail_number,

        -- Metadata
        hr.scraped_at,
        hr.created_at

    FROM PWA_IWT_HEAT_RESULTS hr

    -- Join to get source-specific athlete ID mapping
    LEFT JOIN ATHLETE_SOURCE_IDS asi
        ON hr.source = asi.source
        AND hr.athlete_id = asi.source_id

    -- Join to unified athlete profile
    LEFT JOIN ATHLETES a
        ON asi.athlete_id = a.id

    -- Join to event details
    LEFT JOIN PWA_IWT_EVENTS e
        ON hr.source = e.source
        AND hr.pwa_event_id = e.event_id

    WHERE hr.athlete_id IS NOT NULL
      AND hr.athlete_id != ''

    ORDER BY e.year DESC, e.event_id, hr.round_position, hr.heat_id, hr.place
    """

    cursor.execute(view_sql)
    print("  [OK] ATHLETE_HEAT_RESULTS_VIEW created successfully")

def create_athlete_summary_view(cursor):
    """
    Create a summary view of athlete career statistics.

    Aggregates results across all events to show:
    - Total events competed
    - Best finishes
    - Years active
    - Divisions competed in
    """

    print("\nCreating ATHLETE_SUMMARY_VIEW...")

    # Drop view if exists
    cursor.execute("DROP VIEW IF EXISTS ATHLETE_SUMMARY_VIEW")

    # Create view
    view_sql = """
    CREATE VIEW ATHLETE_SUMMARY_VIEW AS
    SELECT
        -- Athlete information
        a.id AS athlete_id,
        a.primary_name AS athlete_name,
        a.nationality,
        a.year_of_birth,
        COALESCE(a.pwa_profile_url, a.liveheats_image_url) AS profile_picture_url,
        a.pwa_sail_number,

        -- Career statistics
        COUNT(DISTINCT r.event_id) AS total_events,
        MIN(CAST(r.place AS UNSIGNED)) AS best_finish,
        MIN(r.year) AS first_year,
        MAX(r.year) AS last_year,

        -- Podium finishes
        SUM(CASE WHEN CAST(r.place AS UNSIGNED) = 1 THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN CAST(r.place AS UNSIGNED) = 2 THEN 1 ELSE 0 END) AS second_places,
        SUM(CASE WHEN CAST(r.place AS UNSIGNED) = 3 THEN 1 ELSE 0 END) AS third_places,
        SUM(CASE WHEN CAST(r.place AS UNSIGNED) <= 3 THEN 1 ELSE 0 END) AS total_podiums,

        -- Division and competition info
        GROUP_CONCAT(DISTINCT r.division_label ORDER BY r.division_label SEPARATOR ', ') AS divisions_competed,
        GROUP_CONCAT(DISTINCT r.source ORDER BY r.source SEPARATOR ', ') AS data_sources,

        -- Match quality
        a.match_stage,
        a.match_score

    FROM ATHLETES a

    -- Join via source ID mapping
    LEFT JOIN ATHLETE_SOURCE_IDS asi
        ON a.id = asi.athlete_id

    -- Join to results
    LEFT JOIN PWA_IWT_RESULTS r
        ON asi.source = r.source
        AND asi.source_id = r.athlete_id

    WHERE r.athlete_id IS NOT NULL
      AND r.place REGEXP '^[0-9]+$'  -- Only numeric placements

    GROUP BY
        a.id,
        a.primary_name,
        a.nationality,
        a.year_of_birth,
        a.pwa_profile_url,
        a.liveheats_image_url,
        a.pwa_sail_number,
        a.match_stage,
        a.match_score

    ORDER BY total_events DESC, wins DESC, total_podiums DESC
    """

    cursor.execute(view_sql)
    print("  [OK] ATHLETE_SUMMARY_VIEW created successfully")

def create_event_stats_view(cursor):
    """
    Create a view for event statistics with pre-joined score types.

    This view combines:
    - PWA_IWT_EVENTS (event details)
    - PWA_IWT_HEAT_RESULTS (heat totals)
    - PWA_IWT_HEAT_SCORES (individual wave/jump scores)
    - SCORE_TYPES (move type names)

    Features:
    - Human-readable move type names (Forward Loop, Backloop, etc.)
    - Pre-joined event information
    - Simplified querying for statistics endpoint
    """

    print("\nCreating EVENT_STATS_VIEW...")

    # Drop view if exists
    cursor.execute("DROP VIEW IF EXISTS EVENT_STATS_VIEW")

    # Create view
    view_sql = """
    CREATE VIEW EVENT_STATS_VIEW AS
    SELECT
        -- Event information
        e.id AS event_db_id,
        e.event_id AS pwa_event_id,
        e.event_name,
        e.year AS event_year,
        e.source,

        -- Score details
        s.id AS score_id,
        s.heat_id,
        a.id AS athlete_id,
        s.athlete_id AS source_athlete_id,
        a.primary_name AS athlete_name,
        s.sail_number,
        COALESCE(NULLIF(s.sex, ''), hp.sex) AS sex,
        s.pwa_division_code AS division_code,

        -- Score values
        ROUND(s.score, 2) AS score,
        s.type AS score_type_code,
        COALESCE(st.Type_Name, s.type) AS move_type,
        s.counting,

        -- Aggregated totals
        ROUND(s.total_wave, 2) AS total_wave,
        ROUND(s.total_jump, 2) AS total_jump,
        ROUND(s.total_points, 2) AS total_points,

        -- Metadata
        s.scraped_at,
        s.created_at

    FROM PWA_IWT_HEAT_SCORES s

    -- Join to event details
    INNER JOIN PWA_IWT_EVENTS e
        ON s.pwa_event_id = e.event_id
        AND s.source = e.source

    -- Join to athlete source IDs to get unified athlete ID
    -- Simple direct join now that all PWA sources are consolidated to 'PWA'
    LEFT JOIN ATHLETE_SOURCE_IDS asi
        ON s.source = asi.source
        AND s.athlete_id = asi.source_id

    -- Join to unified athlete profile for primary name
    LEFT JOIN ATHLETES a
        ON asi.athlete_id = a.id

    -- Join to heat progression for sex (match on heat_id for precision)
    LEFT JOIN (
        SELECT DISTINCT heat_id, pwa_event_id, pwa_division_code, sex, source
        FROM PWA_IWT_HEAT_PROGRESSION
    ) hp
        ON s.source = hp.source
        AND s.pwa_event_id = hp.pwa_event_id
        AND s.heat_id = hp.heat_id

    -- Join to score types for move names
    LEFT JOIN SCORE_TYPES st
        ON s.type = st.Type

    WHERE s.athlete_id IS NOT NULL
      AND s.athlete_id != ''
      AND s.score IS NOT NULL

    ORDER BY e.year DESC, e.event_id, s.heat_id, s.score DESC
    """

    cursor.execute(view_sql)
    print("  [OK] EVENT_STATS_VIEW created successfully")

def verify_views(cursor):
    """Verify views were created and show sample data"""

    print("\n" + "="*50)
    print("VERIFYING VIEWS")
    print("="*50)

    # Check ATHLETE_RESULTS_VIEW
    cursor.execute("SELECT COUNT(*) FROM ATHLETE_RESULTS_VIEW")
    count = cursor.fetchone()[0]
    print(f"\nATHLETE_RESULTS_VIEW: {count} records")

    cursor.execute("""
        SELECT athlete_name, nationality, event_name, event_year, placement, division_label
        FROM ATHLETE_RESULTS_VIEW
        LIMIT 5
    """)
    print("\nSample results:")
    for row in cursor.fetchall():
        print(f"  {row[0]} ({row[1]}) - {row[2]} {row[3]} - Place {row[4]} ({row[5]})")

    # Check ATHLETE_HEAT_RESULTS_VIEW
    cursor.execute("SELECT COUNT(*) FROM ATHLETE_HEAT_RESULTS_VIEW")
    count = cursor.fetchone()[0]
    print(f"\nATHLETE_HEAT_RESULTS_VIEW: {count} records")

    # Check ATHLETE_SUMMARY_VIEW
    cursor.execute("SELECT COUNT(*) FROM ATHLETE_SUMMARY_VIEW")
    count = cursor.fetchone()[0]
    print(f"\nATHLETE_SUMMARY_VIEW: {count} athletes")

    cursor.execute("""
        SELECT athlete_name, nationality, total_events, wins, total_podiums, best_finish
        FROM ATHLETE_SUMMARY_VIEW
        ORDER BY total_events DESC, wins DESC
        LIMIT 10
    """)
    print("\nTop 10 athletes by events competed:")
    for row in cursor.fetchall():
        print(f"  {row[0]} ({row[1]}) - {row[2]} events, {row[3]} wins, {row[4]} podiums, best: {row[5]}")

    # Check EVENT_STATS_VIEW
    cursor.execute("SELECT COUNT(*) FROM EVENT_STATS_VIEW")
    count = cursor.fetchone()[0]
    print(f"\nEVENT_STATS_VIEW: {count} score records")

    cursor.execute("""
        SELECT event_name, move_type, MAX(score) as best_score, COUNT(*) as score_count
        FROM EVENT_STATS_VIEW
        GROUP BY event_name, move_type
        ORDER BY event_name DESC, best_score DESC
        LIMIT 10
    """)
    print("\nSample event statistics (top 10 move type stats):")
    for row in cursor.fetchall():
        print(f"  {row[0][:30]} - {row[1]}: best {row[2]}, {row[3]} scores")

def main():
    """Main execution function"""
    print("Creating Database Views")
    print("="*50)

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print("  [OK] Connected successfully")

        # Create views
        create_athlete_results_view(cursor)
        create_athlete_heat_results_view(cursor)
        create_athlete_summary_view(cursor)
        create_event_stats_view(cursor)

        # Commit changes
        conn.commit()
        print("\n[OK] All views created and committed")

        # Verify views
        verify_views(cursor)

        print("\n" + "="*50)
        print("SUCCESS: Database views created successfully!")
        print("="*50)

        print("\nAvailable views:")
        print("1. ATHLETE_RESULTS_VIEW - Competition results with athlete profiles")
        print("2. ATHLETE_HEAT_RESULTS_VIEW - Heat-by-heat results with athlete profiles")
        print("3. ATHLETE_SUMMARY_VIEW - Career statistics for each athlete")
        print("4. EVENT_STATS_VIEW - Event statistics with score types and move names")

    except mysql.connector.Error as err:
        print(f"\n[ERROR] DATABASE ERROR: {err}")
        return

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        return

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    main()
