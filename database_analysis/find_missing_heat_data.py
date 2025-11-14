"""
Find events that have final results but NO heat data
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def find_missing_heat_data():
    """Find events missing heat data"""
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

    cursor = conn.cursor()

    # Find events with results but no heat data
    cursor.execute("""
        SELECT
            e.event_id,
            e.event_name,
            e.year,
            e.stars,
            (SELECT COUNT(*) FROM PWA_IWT_RESULTS WHERE event_id = e.event_id) as result_count,
            (SELECT COUNT(*) FROM PWA_IWT_HEAT_PROGRESSION WHERE pwa_event_id = e.event_id) as heat_prog_count,
            (SELECT COUNT(*) FROM PWA_IWT_HEAT_RESULTS WHERE pwa_event_id = e.event_id) as heat_results_count,
            (SELECT COUNT(*) FROM PWA_IWT_HEAT_SCORES WHERE pwa_event_id = e.event_id) as heat_scores_count
        FROM PWA_IWT_EVENTS e
        WHERE has_wave_discipline = TRUE
        ORDER BY e.year DESC, e.event_id DESC
    """)

    events = cursor.fetchall()

    print("=" * 120)
    print("EVENTS WITH RESULTS BUT MISSING HEAT DATA")
    print("=" * 120)
    print(f"{'Year':<6} {'Event ID':<10} {'Event Name':<50} {'Results':<10} {'Heats':<8} {'Heat Res':<10} {'Scores'}")
    print("-" * 120)

    missing_heat_data = []
    complete_events = []

    for event_id, event_name, year, stars, results, heat_prog, heat_results, heat_scores in events:
        # Event has results but no heat data
        if results > 0 and heat_results == 0:
            missing_heat_data.append((year, event_id, event_name, results, heat_prog, heat_results, heat_scores))
            print(f"{year:<6} {event_id:<10} {event_name:<50} {results:<10} {heat_prog:<8} {heat_results:<10} {heat_scores}")
        elif results > 0 and heat_results > 0:
            complete_events.append((year, event_id, event_name))

    print("\n" + "=" * 120)
    print(f"SUMMARY")
    print("=" * 120)
    print(f"Total events with wave discipline: {len(events)}")
    print(f"Events with complete data (results + heats): {len(complete_events)}")
    print(f"Events missing heat data: {len(missing_heat_data)}")

    if missing_heat_data:
        print("\n" + "=" * 120)
        print("MISSING HEAT DATA BREAKDOWN BY YEAR")
        print("=" * 120)

        by_year = {}
        for year, event_id, event_name, results, heat_prog, heat_results, heat_scores in missing_heat_data:
            if year not in by_year:
                by_year[year] = []
            by_year[year].append((event_id, event_name))

        for year in sorted(by_year.keys(), reverse=True):
            print(f"\n{year}: {len(by_year[year])} events")
            for event_id, event_name in by_year[year]:
                print(f"  - Event {event_id}: {event_name}")

    conn.close()

if __name__ == "__main__":
    find_missing_heat_data()
