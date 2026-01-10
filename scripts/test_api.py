"""
API Test Script Template
========================

Reusable script for testing API endpoints locally and in production.

Usage:
    python scripts/test_api.py                      # Test production
    python scripts/test_api.py --local              # Test local (localhost:8001)
    python scripts/test_api.py --endpoint /health   # Test specific endpoint
    python scripts/test_api.py --verbose            # Show full response
"""

import argparse
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Configuration
PROD_BASE_URL = "https://windsurf-world-tour-stats-api.duckdns.org"
LOCAL_BASE_URL = "http://localhost:8001"


def fetch_json(url: str, timeout: int = 30) -> dict:
    """Fetch JSON from URL with error handling."""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}")
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            print(f"        {error_body}")
        except:
            pass
        return None
    except URLError as e:
        print(f"[ERROR] Connection failed: {e.reason}")
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def test_health(base_url: str) -> bool:
    """Test the health endpoint."""
    print("\n--- Testing /health ---")
    data = fetch_json(f"{base_url}/health")
    if data:
        status = data.get("status", "unknown")
        db_status = data.get("database", {}).get("status", "unknown")
        print(f"API Status: {status}")
        print(f"DB Status:  {db_status}")
        return status == "healthy" and db_status == "healthy"
    return False


def test_event_stats(base_url: str, event_id: int = 1, sex: str = "Women") -> bool:
    """Test the event stats endpoint."""
    print(f"\n--- Testing /api/v1/events/{event_id}/stats?sex={sex} ---")
    data = fetch_json(f"{base_url}/api/v1/events/{event_id}/stats?sex={sex}")

    if not data:
        return False

    if "detail" in data:
        print(f"[ERROR] {data['detail']}")
        return False

    event_name = data.get("event_name", "Unknown")
    print(f"Event: {event_name}")

    # Check score counts
    heat_scores = data.get("top_heat_scores", [])
    jump_scores = data.get("top_jump_scores", [])
    wave_scores = data.get("top_wave_scores", [])

    print(f"\nScore counts:")
    print(f"  top_heat_scores: {len(heat_scores)}")
    print(f"  top_jump_scores: {len(jump_scores)}")
    print(f"  top_wave_scores: {len(wave_scores)}")

    # Verify athlete_id is integer
    all_pass = True

    if heat_scores:
        first = heat_scores[0]
        athlete_id = first.get("athlete_id")
        is_int = isinstance(athlete_id, int)
        print(f"\nFirst heat score:")
        print(f"  rank: {first.get('rank')}")
        print(f"  athlete_name: {first.get('athlete_name')}")
        print(f"  athlete_id: {athlete_id} (type: {type(athlete_id).__name__})")
        print(f"  score: {first.get('score')}")
        print(f"  heat_number: {first.get('heat_number')}")

        if is_int:
            print("\n[PASS] athlete_id is INTEGER")
        else:
            print("\n[FAIL] athlete_id is NOT an integer")
            all_pass = False

        if len(heat_scores) > 10:
            print(f"[PASS] More than 10 heat scores returned ({len(heat_scores)})")
        else:
            print(f"[INFO] {len(heat_scores)} heat scores returned")

    # Check move_type_stats
    move_stats = data.get("move_type_stats", [])
    if move_stats:
        print(f"\nMove type stats: {len(move_stats)} types")
        best = move_stats[0] if move_stats else None
        if best:
            scored_by = best.get("best_scored_by", {})
            scored_by_id = scored_by.get("athlete_id") if scored_by else None
            if scored_by_id is not None:
                if isinstance(scored_by_id, int):
                    print(f"[PASS] best_scored_by.athlete_id is INTEGER ({scored_by_id})")
                else:
                    print(f"[FAIL] best_scored_by.athlete_id is NOT integer ({type(scored_by_id).__name__})")
                    all_pass = False

    return all_pass


def test_events_list(base_url: str) -> bool:
    """Test the events list endpoint."""
    print("\n--- Testing /api/v1/events ---")
    data = fetch_json(f"{base_url}/api/v1/events?page_size=5")

    if not data:
        return False

    events = data.get("events", [])
    pagination = data.get("pagination", {})

    print(f"Total events: {pagination.get('total', 'unknown')}")
    print(f"Returned: {len(events)} events")

    if events:
        first = events[0]
        print(f"\nFirst event:")
        print(f"  id: {first.get('id')}")
        print(f"  name: {first.get('event_name')}")
        print(f"  year: {first.get('year')}")
        print(f"  country: {first.get('country_code')}")

    return len(events) > 0


def test_athletes_summary(base_url: str) -> bool:
    """Test the athletes summary endpoint."""
    print("\n--- Testing /api/v1/athletes/summary ---")
    data = fetch_json(f"{base_url}/api/v1/athletes/summary?page_size=5")

    if not data:
        return False

    athletes = data.get("athletes", [])
    pagination = data.get("pagination", {})

    print(f"Total athletes: {pagination.get('total', 'unknown')}")
    print(f"Returned: {len(athletes)} athletes")

    if athletes:
        first = athletes[0]
        print(f"\nFirst athlete:")
        print(f"  id: {first.get('athlete_id')}")
        print(f"  name: {first.get('name')}")
        print(f"  events: {first.get('total_events')}")
        print(f"  wins: {first.get('wins')}")

    return len(athletes) > 0


def main():
    parser = argparse.ArgumentParser(description="Test Windsurf API endpoints")
    parser.add_argument("--local", action="store_true", help="Test local server (localhost:8001)")
    parser.add_argument("--endpoint", type=str, help="Test specific endpoint path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full response")
    parser.add_argument("--event-id", type=int, default=1, help="Event ID for stats test")
    parser.add_argument("--sex", type=str, default="Women", help="Sex filter for stats test")

    args = parser.parse_args()

    base_url = LOCAL_BASE_URL if args.local else PROD_BASE_URL
    env = "LOCAL" if args.local else "PRODUCTION"

    print("=" * 60)
    print(f"WINDSURF API TEST - {env}")
    print("=" * 60)
    print(f"Base URL: {base_url}")

    if args.endpoint:
        # Test specific endpoint
        url = f"{base_url}{args.endpoint}"
        print(f"\nFetching: {url}")
        data = fetch_json(url)
        if data:
            if args.verbose:
                print(json.dumps(data, indent=2))
            else:
                print(f"Response keys: {list(data.keys())}")
                print("[OK] Endpoint returned data")
        return

    # Run standard tests
    results = {}

    results["health"] = test_health(base_url)
    results["events_list"] = test_events_list(base_url)
    results["athletes_summary"] = test_athletes_summary(base_url)
    results["event_stats"] = test_event_stats(base_url, args.event_id, args.sex)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_pass = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
