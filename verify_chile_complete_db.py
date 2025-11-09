"""
Verify complete Chile 2025 data in database
Check events, results, heat progression, heat results, and heat scores
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
    print("VERIFY CHILE 2025 COMPLETE DATA IN DATABASE")
    print("="*80)

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Events
    print("\n" + "="*80)
    print("1. EVENTS")
    print("="*80)
    cursor.execute("""
        SELECT event_id, event_name, year, stars
        FROM PWA_IWT_EVENTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
    """)
    for event_id, name, year, stars in cursor.fetchall():
        print(f"  Event {event_id}: {name} ({stars} stars)")

    # 2. Final Results
    print("\n" + "="*80)
    print("2. FINAL RESULTS")
    print("="*80)
    cursor.execute("""
        SELECT sex, COUNT(*) as count
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        GROUP BY sex
    """)
    for sex, count in cursor.fetchall():
        print(f"  {sex}: {count} competitors")

    # 3. Heat Progression
    print("\n" + "="*80)
    print("3. HEAT PROGRESSION/STRUCTURE")
    print("="*80)
    cursor.execute("""
        SELECT sex, COUNT(DISTINCT heat_id) as heats
        FROM PWA_IWT_HEAT_PROGRESSION
        WHERE pwa_year = 2025
        AND pwa_event_name LIKE '%Chile%'
        GROUP BY sex
    """)
    for sex, heats in cursor.fetchall():
        print(f"  {sex}: {heats} heats")

    # 4. Heat Results
    print("\n" + "="*80)
    print("4. HEAT RESULTS (Athlete placements per heat)")
    print("="*80)
    cursor.execute("""
        SELECT sex, COUNT(*) as results, COUNT(DISTINCT heat_id) as heats, COUNT(DISTINCT athlete_id) as athletes
        FROM PWA_IWT_HEAT_RESULTS
        WHERE pwa_year = 2025
        AND pwa_event_name LIKE '%Chile%'
        GROUP BY sex
    """)
    for sex, results, heats, athletes in cursor.fetchall():
        print(f"  {sex}: {results} heat results across {heats} heats, {athletes} unique athletes")

    # 5. Heat Scores
    print("\n" + "="*80)
    print("5. HEAT SCORES (Individual wave scores)")
    print("="*80)
    cursor.execute("""
        SELECT sex, COUNT(*) as total_scores,
               SUM(CASE WHEN counting = TRUE THEN 1 ELSE 0 END) as counting_scores
        FROM PWA_IWT_HEAT_SCORES
        WHERE pwa_year = 2025
        AND pwa_event_name LIKE '%Chile%'
        GROUP BY sex
    """)
    for sex, total, counting in cursor.fetchall():
        print(f"  {sex}: {total} total wave scores ({counting} counting)")

    # 6. Sample Data - Top 5 Men
    print("\n" + "="*80)
    print("6. SAMPLE: TOP 5 MEN RESULTS")
    print("="*80)
    cursor.execute("""
        SELECT place, athlete_id, source
        FROM PWA_IWT_RESULTS
        WHERE year = 2025
        AND event_name LIKE '%Chile%'
        AND sex = 'Men'
        ORDER BY CAST(place AS UNSIGNED)
        LIMIT 5
    """)
    for place, athlete_id, source in cursor.fetchall():
        print(f"  {place}. Athlete ID: {athlete_id} [{source}]")

    # 7. Expected vs Actual
    print("\n" + "="*80)
    print("7. VERIFICATION SUMMARY")
    print("="*80)

    expected = {
        'Men Final Results': 59,
        'Women Final Results': 18,
        'Men Heats': 49,
        'Women Heats': 14,
        'Men Heat Results': 194,
        'Women Heat Results': 52,
        'Men Wave Scores': 830,
        'Women Wave Scores': 185
    }

    # Check results
    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_RESULTS WHERE year = 2025 AND event_name LIKE '%Chile%' AND sex = 'Men'")
    men_results = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_RESULTS WHERE year = 2025 AND event_name LIKE '%Chile%' AND sex = 'Women'")
    women_results = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT heat_id) FROM PWA_IWT_HEAT_PROGRESSION WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Men'")
    men_heats = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT heat_id) FROM PWA_IWT_HEAT_PROGRESSION WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Women'")
    women_heats = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_HEAT_RESULTS WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Men'")
    men_heat_results = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_HEAT_RESULTS WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Women'")
    women_heat_results = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_HEAT_SCORES WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Men'")
    men_scores = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_HEAT_SCORES WHERE pwa_year = 2025 AND pwa_event_name LIKE '%Chile%' AND sex = 'Women'")
    women_scores = cursor.fetchone()[0]

    actual = {
        'Men Final Results': men_results,
        'Women Final Results': women_results,
        'Men Heats': men_heats,
        'Women Heats': women_heats,
        'Men Heat Results': men_heat_results,
        'Women Heat Results': women_heat_results,
        'Men Wave Scores': men_scores,
        'Women Wave Scores': women_scores
    }

    print(f"\n{'Metric':<25} {'Expected':<12} {'Actual':<12} {'Status':<10}")
    print("-"*80)
    for metric in expected.keys():
        exp = expected[metric]
        act = actual[metric]
        status = "✓ PASS" if exp == act else "✗ FAIL"
        print(f"{metric:<25} {exp:<12} {act:<12} {status:<10}")

    print("\n" + "="*80)
    all_pass = all(expected[k] == actual[k] for k in expected.keys())
    if all_pass:
        print("✓ ALL CHECKS PASSED - Chile 2025 data is COMPLETE!")
    else:
        print("✗ SOME CHECKS FAILED - Review data above")
    print("="*80)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
