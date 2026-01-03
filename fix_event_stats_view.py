"""
Recreate EVENT_STATS_VIEW with fixed source mapping

Fixes the join between PWA_IWT_HEAT_SCORES and ATHLETE_SOURCE_IDS
by mapping PWA → PWA_heat for athlete lookups.
"""

import mysql.connector
import os

# Read env from .env.production
env_vars = {}
with open('.env.production') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

def get_connection():
    """Create connection to production database"""
    conn = mysql.connector.connect(
        host='10.0.151.92',
        port=3306,
        database='jfa_heatwave_db',
        user=env_vars['DB_USER'],
        password=env_vars['DB_PASSWORD'],
        connect_timeout=30
    )
    return conn

def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 80)
    print("RECREATING EVENT_STATS_VIEW WITH FIXED SOURCE MAPPING")
    print("=" * 80)

    # Drop existing view
    print("\n1. Dropping existing EVENT_STATS_VIEW...")
    cursor.execute("DROP VIEW IF EXISTS EVENT_STATS_VIEW")
    print("   ✅ Dropped")

    # Create new view with fixed join
    print("\n2. Creating EVENT_STATS_VIEW with corrected source mapping...")

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
        s.athlete_id,
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
    print("   ✅ Created")

    # Verify the fix worked
    print("\n3. Verifying fix by checking for NULL athlete_names...")
    cursor.execute("""
        SELECT COUNT(*) as total_scores,
               SUM(CASE WHEN athlete_name IS NULL THEN 1 ELSE 0 END) as null_names
        FROM EVENT_STATS_VIEW
    """)
    result = cursor.fetchone()
    total = result[0]
    nulls = result[1]

    print(f"   Total scores: {total}")
    print(f"   NULL names: {nulls}")

    if nulls == 0:
        print("   ✅ Perfect! All athlete names are populated.")
    else:
        pct = (nulls / total * 100) if total > 0 else 0
        print(f"   ⚠️  Still {nulls} NULL names ({pct:.1f}%)")

        # Show sample of remaining NULLs
        print("\n   Sample of remaining NULLs:")
        cursor.execute("""
            SELECT DISTINCT athlete_id, sail_number, source
            FROM EVENT_STATS_VIEW
            WHERE athlete_name IS NULL
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"     - {row[2]}: {row[0]} (sail: {row[1]})")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ VIEW RECREATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
