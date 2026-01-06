"""
Test script to verify fleet average is calculated correctly for move type scores
"""
import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath('.'))

from src.api.database import DatabaseManager

# Load environment variables
load_dotenv()

def test_fleet_average_query():
    """Test the fleet average calculation query"""
    db = DatabaseManager()

    try:
        # Test with an athlete who has multiple move types (Women's division)
        test_query = """
            SELECT
                e.id as event_id,
                a.id as athlete_id,
                r.sex,
                COUNT(DISTINCT s.type) as num_move_types
            FROM PWA_IWT_EVENTS e
            JOIN PWA_IWT_RESULTS r ON r.source = e.source AND r.event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON r.source = asi.source AND r.athlete_id = asi.source_id
            JOIN ATHLETES a ON asi.athlete_id = a.id
            JOIN PWA_IWT_HEAT_SCORES s ON s.source = asi.source AND s.athlete_id = asi.source_id
                AND s.pwa_event_id = r.event_id
            WHERE e.has_wave_discipline = TRUE AND r.sex = 'Women'
            GROUP BY e.id, a.id, r.sex
            HAVING num_move_types > 1
            ORDER BY num_move_types DESC
            LIMIT 1
        """

        result = db.execute_query(test_query, fetch_one=True)

        if not result:
            print("No test data found")
            return

        event_id = result['event_id']
        athlete_id = result['athlete_id']
        detected_sex = result['sex']

        print(f"Testing with event_id={event_id}, athlete_id={athlete_id}, sex={detected_sex}")

        # Now test the move type query with fleet average
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
                    JOIN PWA_IWT_RESULTS r2 ON r2.source = e2.source AND r2.event_id = e2.event_id
                        AND r2.source = asi2.source AND r2.athlete_id = asi2.source_id
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

        if move_type_results:
            print(f"\nMove Type Scores (found {len(move_type_results)} move types):")
            print("-" * 80)
            for row in move_type_results:
                print(f"Move Type: {row['move_type']}")
                print(f"  Best Score: {row['best_score']}")
                print(f"  Athlete Average: {row['average_score']}")
                print(f"  Fleet Average: {row['fleet_average']}")
                print()
            print("[SUCCESS] Query executed successfully!")
        else:
            print("[WARNING] No move type scores found for this athlete/event combination")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing fleet average calculation...\n")
    test_fleet_average_query()
