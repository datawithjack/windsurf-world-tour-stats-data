"""
Check for duplicate scores in EVENT_STATS_VIEW caused by multiple athlete source mappings
"""

import mysql.connector

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
    cursor = conn.cursor(dictionary=True)

    print("=" * 120)
    print("INVESTIGATING DUPLICATES IN EVENT_STATS_VIEW")
    print("=" * 120)

    # Check total records in base table vs view
    print("\n1. Comparing record counts:")
    cursor.execute("SELECT COUNT(*) as count FROM PWA_IWT_HEAT_SCORES")
    base_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM EVENT_STATS_VIEW")
    view_count = cursor.fetchone()['count']

    print(f"   PWA_IWT_HEAT_SCORES: {base_count:,} records")
    print(f"   EVENT_STATS_VIEW:    {view_count:,} records")

    if view_count > base_count:
        diff = view_count - base_count
        pct = (diff / base_count * 100)
        print(f"   ⚠️  DUPLICATES: {diff:,} extra records ({pct:.1f}% inflation)")
    elif view_count == base_count:
        print(f"   ✅ No duplicates - counts match")
    else:
        print(f"   ⚠️  MISSING: {base_count - view_count:,} records")

    # Find actual duplicates by score_id
    print("\n2. Finding duplicate score_id entries:")
    cursor.execute("""
        SELECT score_id, COUNT(*) as count
        FROM EVENT_STATS_VIEW
        GROUP BY score_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 10
    """)

    duplicates = cursor.fetchall()

    if duplicates:
        print(f"   Found {len(duplicates)} score_ids with duplicates:\n")
        for dup in duplicates:
            print(f"   score_id {dup['score_id']}: appears {dup['count']} times")

            # Get details
            cursor.execute("""
                SELECT esv.score_id, esv.athlete_id, esv.athlete_name,
                       esv.heat_id, esv.score, esv.event_name
                FROM EVENT_STATS_VIEW esv
                WHERE esv.score_id = %s
            """, (dup['score_id'],))

            details = cursor.fetchall()
            for d in details:
                print(f"      → {d['athlete_name']}, score={d['score']}, event={d['event_name']}")
    else:
        print("   ✅ No duplicate score_ids found")

    # Check for athletes with multiple source mappings
    print("\n3. Athletes with multiple PWA source mappings:")
    cursor.execute("""
        SELECT asi.source_id, asi.athlete_id, a.primary_name,
               GROUP_CONCAT(DISTINCT asi.source ORDER BY asi.source) as sources,
               COUNT(DISTINCT asi.source) as source_count
        FROM ATHLETE_SOURCE_IDS asi
        LEFT JOIN ATHLETES a ON asi.athlete_id = a.id
        WHERE asi.source LIKE 'PWA%'
        GROUP BY asi.source_id, asi.athlete_id, a.primary_name
        HAVING COUNT(DISTINCT asi.source) > 1
        ORDER BY source_count DESC, a.primary_name
        LIMIT 20
    """)

    multi_source = cursor.fetchall()

    if multi_source:
        print(f"   Found {len(multi_source)} athletes with multiple PWA source types:\n")
        print(f"   {'Athlete Name':<35} {'Source ID':<35} {'Sources'}")
        print("   " + "-" * 110)
        for row in multi_source:
            print(f"   {row['primary_name']:<35} {row['source_id']:<35} {row['sources']}")
    else:
        print("   ✅ No athletes with multiple PWA source types")

    # Show current PWA source distribution
    print("\n4. Current PWA source type distribution in ATHLETE_SOURCE_IDS:")
    cursor.execute("""
        SELECT source, COUNT(*) as count, COUNT(DISTINCT athlete_id) as unique_athletes
        FROM ATHLETE_SOURCE_IDS
        WHERE source LIKE 'PWA%'
        GROUP BY source
        ORDER BY count DESC
    """)

    sources = cursor.fetchall()
    for row in sources:
        print(f"   {row['source']:<20} {row['count']:>5} mappings, {row['unique_athletes']:>4} unique athletes")

    cursor.close()
    conn.close()

    print("\n" + "=" * 120)
    print("RECOMMENDATION")
    print("=" * 120)
    if multi_source:
        print("""
   ⚠️  Multiple source types found for same athletes, causing view duplicates.

   SOLUTION: Consolidate all PWA source types to single 'PWA' source:
   - PWA_heat      → PWA
   - PWA_sail_number → PWA
   - PWA (unchanged) → PWA

   This will:
   1. Eliminate duplicate join matches in EVENT_STATS_VIEW
   2. Simplify view join logic (source = source, no IN clause needed)
   3. Maintain data integrity (source_id still distinguishes different data sources)
        """)
    else:
        print("   ✅ No consolidation needed - sources are clean")

if __name__ == "__main__":
    main()
