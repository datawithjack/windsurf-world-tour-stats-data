"""
Test script for Head-to-Head API endpoint

Prerequisites:
1. SSH tunnel to database must be running
2. Local dev server must be running: uvicorn src.api.main:app --reload --port 8001

Usage:
    python test_head_to_head_api.py
"""

import requests
import json

# API Configuration
BASE_URL = "http://localhost:8001"

def test_head_to_head():
    """
    Test the head-to-head endpoint
    """

    # First, get a recent event with women's division
    print("=" * 80)
    print("Testing Head-to-Head API Endpoint")
    print("=" * 80)

    # Get events
    print("\n1. Fetching recent events...")
    events_response = requests.get(f"{BASE_URL}/api/v1/events?page_size=5")

    if events_response.status_code != 200:
        print(f"Error fetching events: {events_response.status_code}")
        print(events_response.text)
        return

    events_data = events_response.json()
    if not events_data['events']:
        print("No events found!")
        return

    event = events_data['events'][0]
    event_id = event['id']
    event_name = event['event_name']

    print(f"   Using event: {event_name} (ID: {event_id})")

    # Get athletes from the event
    print(f"\n2. Fetching athletes from event {event_id}...")
    athletes_response = requests.get(
        f"{BASE_URL}/api/v1/events/{event_id}/athletes",
        params={"sex": "Women"}
    )

    if athletes_response.status_code != 200:
        print(f"Error fetching athletes: {athletes_response.status_code}")
        print(athletes_response.text)
        return

    athletes_data = athletes_response.json()
    if len(athletes_data['athletes']) < 2:
        print("Not enough athletes in event!")
        return

    athlete1 = athletes_data['athletes'][0]
    athlete2 = athletes_data['athletes'][1]

    print(f"   Athlete 1: {athlete1['name']} (ID: {athlete1['athlete_id']}, Place: {athlete1['overall_position']})")
    print(f"   Athlete 2: {athlete2['name']} (ID: {athlete2['athlete_id']}, Place: {athlete2['overall_position']})")

    # Test head-to-head comparison
    print(f"\n3. Fetching head-to-head comparison...")
    h2h_response = requests.get(
        f"{BASE_URL}/api/v1/events/{event_id}/head-to-head",
        params={
            "athlete1_id": athlete1['athlete_id'],
            "athlete2_id": athlete2['athlete_id'],
            "division": "Women"
        }
    )

    if h2h_response.status_code != 200:
        print(f"Error fetching head-to-head: {h2h_response.status_code}")
        print(h2h_response.text)
        return

    h2h_data = h2h_response.json()

    print("\n" + "=" * 80)
    print("HEAD-TO-HEAD COMPARISON RESULT")
    print("=" * 80)
    print(f"\nEvent: {h2h_data['event_name']}")
    print(f"Division: {h2h_data['division']}")

    print(f"\n{h2h_data['athlete1']['name']} vs {h2h_data['athlete2']['name']}")
    print("-" * 80)

    print("\nATHLETE 1:")
    a1 = h2h_data['athlete1']
    print(f"  Name: {a1['name']} ({a1['nationality']})")
    print(f"  Place: {a1['place']}")
    print(f"  Heat Scores - Best: {a1['heat_scores_best']}, Avg: {a1['heat_scores_avg']}")
    print(f"  Jumps - Best: {a1['jumps_best']}, Avg Counting: {a1['jumps_avg_counting']}")
    print(f"  Waves - Best: {a1['waves_best']}, Avg Counting: {a1['waves_avg_counting']}")
    print(f"  Heat Wins: {a1['heat_wins']}")

    print("\nATHLETE 2:")
    a2 = h2h_data['athlete2']
    print(f"  Name: {a2['name']} ({a2['nationality']})")
    print(f"  Place: {a2['place']}")
    print(f"  Heat Scores - Best: {a2['heat_scores_best']}, Avg: {a2['heat_scores_avg']}")
    print(f"  Jumps - Best: {a2['jumps_best']}, Avg Counting: {a2['jumps_avg_counting']}")
    print(f"  Waves - Best: {a2['waves_best']}, Avg Counting: {a2['waves_avg_counting']}")
    print(f"  Heat Wins: {a2['heat_wins']}")

    print("\nCOMPARISON:")
    comp = h2h_data['comparison']

    metrics = [
        ("Heat Scores (Best)", comp['heat_scores_best']),
        ("Heat Scores (Avg)", comp['heat_scores_avg']),
        ("Jumps (Best)", comp['jumps_best']),
        ("Jumps (Avg Counting)", comp['jumps_avg_counting']),
        ("Waves (Best)", comp['waves_best']),
        ("Waves (Avg Counting)", comp['waves_avg_counting']),
        ("Heat Wins", comp['heat_wins'])
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

    # Pretty print full JSON for inspection
    print("\n\nFull JSON Response:")
    print(json.dumps(h2h_data, indent=2))


if __name__ == "__main__":
    try:
        test_head_to_head()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the dev server is running:")
        print("  uvicorn src.api.main:app --reload --port 8001")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
