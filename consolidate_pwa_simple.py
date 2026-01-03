"""
Simplified PWA source consolidation - delete duplicates and update in one go
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

    print("=" * 100)
    print("SIMPLIFIED PWA SOURCE CONSOLIDATION")
    print("=" * 100)

    # Show current state
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM ATHLETE_SOURCE_IDS
        WHERE source LIKE 'PWA%'
        GROUP BY source
    """)
    print("\nBefore:")
    for row in cursor.fetchall():
        print(f"  {row['source']:<20} {row['count']} mappings")

    # Simple approach: Delete all PWA_heat and PWA_sail_number, keep only PWA
    # But first, add any missing mappings from PWA_heat/PWA_sail_number to PWA

    print("\n1. Adding missing mappings to PWA source...")
    cursor.execute("""
        INSERT IGNORE INTO ATHLETE_SOURCE_IDS (athlete_id, source, source_id)
        SELECT DISTINCT athlete_id, 'PWA', source_id
        FROM ATHLETE_SOURCE_IDS
        WHERE source IN ('PWA_heat', 'PWA_sail_number')
    """)
    added = cursor.rowcount
    print(f"   Added {added} new PWA mappings")

    print("\n2. Deleting PWA_heat and PWA_sail_number sources...")
    cursor.execute("""
        DELETE FROM ATHLETE_SOURCE_IDS
        WHERE source IN ('PWA_heat', 'PWA_sail_number')
    """)
    deleted = cursor.rowcount
    print(f"   Deleted {deleted} old source mappings")

    # Show new state
    cursor.execute("""
        SELECT source, COUNT(*) as count, COUNT(DISTINCT athlete_id) as unique_athletes
        FROM ATHLETE_SOURCE_IDS
        WHERE source IN ('PWA', 'Live Heats')
        GROUP BY source
    """)
    print("\nAfter:")
    for row in cursor.fetchall():
        print(f"  {row['source']:<20} {row['count']} mappings, {row['unique_athletes']} unique athletes")

    # Commit
    conn.commit()
    print("\n✅ Changes committed")

    # Verify EVENT_STATS_VIEW
    print("\n3. Checking EVENT_STATS_VIEW...")
    cursor.execute("SELECT COUNT(*) as count FROM PWA_IWT_HEAT_SCORES")
    base = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM EVENT_STATS_VIEW")
    view = cursor.fetchone()['count']

    print(f"   Base table: {base:,}")
    print(f"   View:       {view:,}")

    if view > base:
        print(f"   ⚠️  Still {view - base:,} duplicates - view needs updating")
    else:
        print(f"   ✅ No duplicates!")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
