"""
Quick verification script to check Chile 2025 data in database
"""
import mysql.connector
import os
from dotenv import load_dotenv

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

def main():
    print("="*80)
    print("VERIFY CHILE 2025 DATA IN DATABASE")
    print("="*80)

    conn = get_connection()
    cursor = conn.cursor()

    # Check Chile 2025 Men
    cursor.execute("""
        SELECT COUNT(*)
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        AND sex = 'Men'
    """)
    men_count = cursor.fetchone()[0]
    print(f"\nChile 2025 Men: {men_count} records")

    # Check Chile 2025 Women
    cursor.execute("""
        SELECT COUNT(*)
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        AND sex = 'Women'
    """)
    women_count = cursor.fetchone()[0]
    print(f"Chile 2025 Women: {women_count} records")

    # Get event details
    cursor.execute("""
        SELECT DISTINCT source, event_id, event_name, division_label, sex
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        ORDER BY sex
    """)
    print("\nEvent Details:")
    for source, event_id, event_name, division in cursor.fetchall():
        print(f"  {source} | Event {event_id} | {event_name} | {division}")

    # Sample some results
    cursor.execute("""
        SELECT place, athlete_name, athlete_id, source
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        AND sex = 'Men'
        ORDER BY CAST(place AS UNSIGNED)
        LIMIT 10
    """)
    print("\nTop 10 Men Results:")
    for place, name, athlete_id, source in cursor.fetchall():
        print(f"  {place}. {name or 'N/A'} (ID: {athlete_id}) [{source}]")

    print("\n" + "="*80)
    print(f"VERIFICATION: {'PASS' if men_count == 59 and women_count == 18 else 'FAIL'}")
    print(f"Expected: 59 men, 18 women")
    print(f"Got: {men_count} men, {women_count} women")
    print("="*80)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
