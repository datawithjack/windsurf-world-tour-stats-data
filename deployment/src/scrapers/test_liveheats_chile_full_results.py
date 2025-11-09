"""
Test Script: Get Full Chile Results from Live Heats
Tests using eventDivisionRanks to get ALL competitor results
"""

import requests
import json

GRAPHQL_URL = "https://liveheats.com/api/graphql"

# Chile event from matching report:
# Event 321865, Division Women: 584951, Division Men: 584952

def test_event_division_ranks(division_id):
    """
    Test fetching full rankings using EventDivisionRank

    Args:
        division_id: Live Heats division ID (e.g., 584951 for Chile Women)
    """

    query = """
    query getEventDivision($id: ID!) {
      eventDivision(id: $id) {
        id
        division { id, name }
        eventDivisionRanks {
          id
          athleteId
          place
          total
          excluded
          competitor {
            id
            firstName
            lastName
            sailNumber
            country
          }
        }
      }
    }
    """

    variables = {"id": str(division_id)}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    payload = {"query": query, "variables": variables}

    print(f"\n{'='*80}")
    print(f"Testing Division ID: {division_id}")
    print(f"{'='*80}\n")

    try:
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Check for errors
        if 'errors' in data:
            print(f"[ERROR] GraphQL Errors:")
            print(json.dumps(data['errors'], indent=2))
            return None

        # Extract division info
        event_division = data['data']['eventDivision']

        if not event_division:
            print("[ERROR] No event division found")
            return None

        division_name = event_division['division']['name']
        ranks = event_division.get('eventDivisionRanks', [])

        print(f"[OK] Division: {division_name}")
        print(f"[OK] Total Competitors: {len(ranks)}\n")

        # Display results
        print(f"{'Place':<8} {'Athlete Name':<30} {'Sail#':<10} {'Country':<10} {'Athlete ID':<12} {'Total':<8}")
        print(f"{'-'*100}")

        for rank in ranks:
            place = rank.get('place', '?')
            athlete_id = rank.get('athleteId', '')
            total = rank.get('total', 0)
            excluded = rank.get('excluded', False)

            competitor = rank.get('competitor', {})
            if competitor:
                first_name = competitor.get('firstName', '')
                last_name = competitor.get('lastName', '')
                full_name = f"{first_name} {last_name}".strip()
                sail_number = competitor.get('sailNumber', '')
                country = competitor.get('country', '')
            else:
                full_name = '[No competitor data]'
                sail_number = ''
                country = ''

            status = " (EXCLUDED)" if excluded else ""

            print(f"{place:<8} {full_name:<30} {sail_number:<10} {country:<10} {athlete_id:<12} {total:<8.2f}{status}")

        print(f"\n{'='*80}\n")

        # Save to JSON for inspection
        output_file = f"chile_division_{division_id}_full_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"[SAVED] Full JSON saved to: {output_file}\n")

        return ranks

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Test both Chile divisions"""

    print("\n" + "="*80)
    print("LIVE HEATS - CHILE FULL RESULTS TEST")
    print("Event: 2025 Chile World Cup (Event ID: 321865)")
    print("="*80)

    # Test Women's division
    print("\n[1] Testing WOMEN'S Division (584951)...")
    women_ranks = test_event_division_ranks(584951)

    # Test Men's division
    print("\n[2] Testing MEN'S Division (584952)...")
    men_ranks = test_event_division_ranks(584952)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Women competitors: {len(women_ranks) if women_ranks else 0}")
    print(f"Men competitors: {len(men_ranks) if men_ranks else 0}")
    print(f"Total competitors: {(len(women_ranks) if women_ranks else 0) + (len(men_ranks) if men_ranks else 0)}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
