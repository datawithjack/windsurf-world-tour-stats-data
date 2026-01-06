"""
Direct test for Head-to-Head API logic (no server required)

Tests the database queries and comparison logic directly.

Prerequisites:
- SSH tunnel to database must be running

Usage:
    python test_head_to_head_direct.py
"""

import sys
from datetime import datetime
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )


def calculate_comparison_metric(athlete1_value: float, athlete2_value: float) -> dict:
    """
    Calculate comparison metric between two athlete values
    """
    difference = abs(athlete1_value - athlete2_value)

    if athlete1_value > athlete2_value:
        winner = "athlete1"
    elif athlete2_value > athlete1_value:
        winner = "athlete2"
    else:
        winner = "tie"

    return {
        "winner": winner,
        "difference": round(difference, 2),
        "athlete1_value": round(athlete1_value, 2),
        "athlete2_value": round(athlete2_value, 2)
    }


def test_head_to_head_direct():
    """
    Direct test of head-to-head logic
    """
    print("=" * 80)
    print("Direct Head-to-Head Test (No Server Required)")
    print("=" * 80)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Get a recent event
        print("\n1. Finding recent event...")
        cursor.execute("""
            SELECT e.id, e.event_name, e.year
            FROM PWA_IWT_EVENTS e
            WHERE e.has_wave_discipline = TRUE
            ORDER BY e.year DESC, e.start_date DESC
            LIMIT 1
        """)
        event = cursor.fetchone()

        if not event:
            print("ERROR: No events found!")
            return

        event_id = event['id']
        event_name = event['event_name']
        print(f"   Using: {event_name} (ID: {event_id}, Year: {event['year']})")

        # 2. Get athletes from the event (Women's division)
        print(f"\n2. Finding athletes in Women's division...")
        cursor.execute("""
            SELECT DISTINCT a.id, a.primary_name, CAST(r.place AS UNSIGNED) as place
            FROM PWA_IWT_RESULTS r
            JOIN PWA_IWT_EVENTS e ON r.source = e.source AND r.event_id = e.event_id
            JOIN ATHLETE_SOURCE_IDS asi ON r.source = asi.source AND r.athlete_id = asi.source_id
            JOIN ATHLETES a ON asi.athlete_id = a.id
            WHERE e.id = %s AND r.sex = 'Women'
            ORDER BY place
            LIMIT 2
        """, (event_id,))
        athletes = cursor.fetchall()

        if len(athletes) < 2:
            print(f"ERROR: Not enough athletes found (found {len(athletes)}, need 2)")
            return

        athlete1_id = athletes[0]['id']
        athlete1_name = athletes[0]['primary_name']
        athlete1_place = athletes[0]['place']

        athlete2_id = athletes[1]['id']
        athlete2_name = athletes[1]['primary_name']
        athlete2_place = athletes[1]['place']

        print(f"   Athlete 1: {athlete1_name} (ID: {athlete1_id}, Place: {athlete1_place})")
        print(f"   Athlete 2: {athlete2_name} (ID: {athlete2_id}, Place: {athlete2_place})")

        # 3. Get statistics for both athletes
        print(f"\n3. Calculating statistics...")

        division = "Women"
        athletes_stats = {}

        for athlete_key, athlete_id, athlete_name in [
            ("athlete1", athlete1_id, athlete1_name),
            ("athlete2", athlete2_id, athlete2_name)
        ]:
            print(f"   Processing {athlete_name}...")

            # Get athlete profile and placement
            cursor.execute("""
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
            """, (athlete_id, event_id, division))
            profile = cursor.fetchone()

            # Get heat score statistics
            cursor.execute("""
                SELECT
                    ROUND(MAX(hr.result_total), 2) as heat_scores_best,
                    ROUND(AVG(hr.result_total), 2) as heat_scores_avg,
                    COUNT(CASE WHEN hr.place = 1 THEN 1 END) as heat_wins
                FROM PWA_IWT_HEAT_RESULTS hr
                JOIN PWA_IWT_EVENTS e ON hr.source = e.source AND hr.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON hr.source = asi.source AND hr.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s
            """, (athlete_id, event_id))
            heat_stats = cursor.fetchone()

            # Get jump score statistics
            cursor.execute("""
                SELECT
                    ROUND(MAX(s.score), 2) as jumps_best,
                    ROUND(AVG(CASE WHEN COALESCE(s.counting, FALSE) = TRUE THEN s.score END), 2) as jumps_avg_counting
                FROM PWA_IWT_HEAT_SCORES s
                JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s AND s.type != 'Wave'
            """, (athlete_id, event_id))
            jump_stats = cursor.fetchone()

            # Get wave score statistics
            cursor.execute("""
                SELECT
                    ROUND(MAX(s.score), 2) as waves_best,
                    ROUND(AVG(CASE WHEN COALESCE(s.counting, FALSE) = TRUE THEN s.score END), 2) as waves_avg_counting
                FROM PWA_IWT_HEAT_SCORES s
                JOIN PWA_IWT_EVENTS e ON s.source = e.source AND s.pwa_event_id = e.event_id
                JOIN ATHLETE_SOURCE_IDS asi ON s.source = asi.source AND s.athlete_id = asi.source_id
                WHERE asi.athlete_id = %s AND e.id = %s AND s.type = 'Wave'
            """, (athlete_id, event_id))
            wave_stats = cursor.fetchone()

            # Store athlete stats
            athletes_stats[athlete_key] = {
                "athlete_id": profile['athlete_id'],
                "name": profile['name'],
                "nationality": profile['nationality'],
                "place": profile['place'],
                "profile_image": profile['profile_image'],
                "heat_scores_best": heat_stats['heat_scores_best'] or 0.0,
                "heat_scores_avg": heat_stats['heat_scores_avg'] or 0.0,
                "jumps_best": jump_stats['jumps_best'] or 0.0,
                "jumps_avg_counting": jump_stats['jumps_avg_counting'] or 0.0,
                "waves_best": wave_stats['waves_best'] or 0.0,
                "waves_avg_counting": wave_stats['waves_avg_counting'] or 0.0,
                "heat_wins": heat_stats['heat_wins'] or 0
            }

        # 4. Calculate comparisons
        print(f"\n4. Calculating comparisons...")
        a1 = athletes_stats["athlete1"]
        a2 = athletes_stats["athlete2"]

        comparison = {
            "heat_scores_best": calculate_comparison_metric(
                a1["heat_scores_best"], a2["heat_scores_best"]
            ),
            "heat_scores_avg": calculate_comparison_metric(
                a1["heat_scores_avg"], a2["heat_scores_avg"]
            ),
            "jumps_best": calculate_comparison_metric(
                a1["jumps_best"], a2["jumps_best"]
            ),
            "jumps_avg_counting": calculate_comparison_metric(
                a1["jumps_avg_counting"], a2["jumps_avg_counting"]
            ),
            "waves_best": calculate_comparison_metric(
                a1["waves_best"], a2["waves_best"]
            ),
            "waves_avg_counting": calculate_comparison_metric(
                a1["waves_avg_counting"], a2["waves_avg_counting"]
            ),
            "heat_wins": calculate_comparison_metric(
                float(a1["heat_wins"]), float(a2["heat_wins"])
            )
        }

        # 5. Display results
        print("\n" + "=" * 80)
        print("HEAD-TO-HEAD COMPARISON RESULT")
        print("=" * 80)
        print(f"\nEvent: {event_name}")
        print(f"Division: {division}")
        print(f"\n{a1['name']} vs {a2['name']}")
        print("-" * 80)

        print("\nATHLETE 1:")
        print(f"  Name: {a1['name']} ({a1['nationality']})")
        print(f"  Place: {a1['place']}")
        print(f"  Heat Scores - Best: {a1['heat_scores_best']}, Avg: {a1['heat_scores_avg']}")
        print(f"  Jumps - Best: {a1['jumps_best']}, Avg Counting: {a1['jumps_avg_counting']}")
        print(f"  Waves - Best: {a1['waves_best']}, Avg Counting: {a1['waves_avg_counting']}")
        print(f"  Heat Wins: {a1['heat_wins']}")

        print("\nATHLETE 2:")
        print(f"  Name: {a2['name']} ({a2['nationality']})")
        print(f"  Place: {a2['place']}")
        print(f"  Heat Scores - Best: {a2['heat_scores_best']}, Avg: {a2['heat_scores_avg']}")
        print(f"  Jumps - Best: {a2['jumps_best']}, Avg Counting: {a2['jumps_avg_counting']}")
        print(f"  Waves - Best: {a2['waves_best']}, Avg Counting: {a2['waves_avg_counting']}")
        print(f"  Heat Wins: {a2['heat_wins']}")

        print("\nCOMPARISON:")
        metrics = [
            ("Heat Scores (Best)", comparison['heat_scores_best']),
            ("Heat Scores (Avg)", comparison['heat_scores_avg']),
            ("Jumps (Best)", comparison['jumps_best']),
            ("Jumps (Avg Counting)", comparison['jumps_avg_counting']),
            ("Waves (Best)", comparison['waves_best']),
            ("Waves (Avg Counting)", comparison['waves_avg_counting']),
            ("Heat Wins", comparison['heat_wins'])
        ]

        for metric_name, metric_data in metrics:
            winner_text = "ATHLETE 1" if metric_data['winner'] == "athlete1" else \
                         "ATHLETE 2" if metric_data['winner'] == "athlete2" else "TIE"
            print(f"\n  {metric_name}:")
            print(f"    Athlete 1: {metric_data['athlete1_value']}")
            print(f"    Athlete 2: {metric_data['athlete2_value']}")
            print(f"    Difference: {metric_data['difference']}")
            print(f"    Winner: {winner_text}")

        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)

        # Close connection
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        print(f"\nDATABASE ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Head-to-Head Logic Directly (No Server Required)\n")
    test_head_to_head_direct()
