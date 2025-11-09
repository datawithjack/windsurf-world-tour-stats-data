"""
Test Improved Live Heats Scraper - Chile Only
Tests the new calculate_final_rankings_from_all_heats method
"""

import requests
from datetime import datetime


class LiveHeatsTestScraper:
    """Test scraper for Chile event"""

    def __init__(self):
        self.graphql_url = "https://liveheats.com/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

    def calculate_final_rankings_from_all_heats(self, heats_data):
        """
        Calculate final rankings by finding each athlete's best round progression
        """
        athlete_best = {}

        # Process all heats
        for heat in heats_data:
            round_position = heat.get('roundPosition', 0)

            for result in heat.get('result', []):
                athlete_id = result.get('athleteId')
                place_in_heat = int(result.get('place', 999)) if result.get('place') is not None else 999

                if athlete_id:
                    stored = athlete_best.get(athlete_id)

                    if stored:
                        stored_round, stored_place = stored
                        if round_position > stored_round or (round_position == stored_round and place_in_heat < stored_place):
                            athlete_best[athlete_id] = (round_position, place_in_heat)
                    else:
                        athlete_best[athlete_id] = (round_position, place_in_heat)

        # Sort by furthest round, then best placement
        sorted_athletes = sorted(athlete_best.items(), key=lambda x: (-x[1][0], x[1][1]))

        # Assign rankings
        rankings = []
        prev_key = None
        final_rank = 1

        for i, (athlete_id, (round_pos, heat_place)) in enumerate(sorted_athletes):
            if i > 0 and (round_pos, heat_place) != prev_key:
                final_rank = i + 1

            rankings.append({
                'athleteId': athlete_id,
                'place': final_rank,
                'round_reached': round_pos,
                'heat_place': heat_place
            })

            prev_key = (round_pos, heat_place)

        return rankings

    def fetch_division_rankings(self, division_id, division_name):
        """Fetch rankings for a division"""

        query = """
        query getEventDivision($id: ID!) {
          eventDivision(id: $id) {
            id
            division { id, name }
            heats {
              id
              roundPosition
              round
              result {
                athleteId
                place
              }
            }
          }
        }
        """

        variables = {"id": str(division_id)}
        payload = {"query": query, "variables": variables}

        print(f"\nFetching {division_name} (Division {division_id})...")

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'errors' in data:
                print(f"  [ERROR] {data['errors']}")
                return None

            event_division = data['data']['eventDivision']
            heats = event_division.get('heats', [])

            print(f"  Found {len(heats)} heats")

            # Show heat structure
            for heat in heats[:3]:  # Show first 3 heats
                round_name = heat.get('round', 'Unknown')
                round_pos = heat.get('roundPosition', 0)
                num_athletes = len(heat.get('result', []))
                print(f"    Heat: {round_name} (Round {round_pos}) - {num_athletes} athletes")

            # Calculate rankings
            rankings = self.calculate_final_rankings_from_all_heats(heats)

            print(f"\n  [NEW METHOD] Extracted {len(rankings)} total competitors")
            print(f"\n  Top 10 Rankings:")
            print(f"  {'Place':<8} {'Athlete ID':<15} {'Round Reached':<15} {'Heat Place':<12}")
            print(f"  {'-'*60}")

            for rank in rankings[:10]:
                print(f"  {rank['place']:<8} {rank['athleteId']:<15} {rank['round_reached']:<15} {rank['heat_place']:<12}")

            return rankings

        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Test Chile divisions"""

    print("="*80)
    print("TEST: IMPROVED LIVE HEATS SCRAPER - CHILE 2025")
    print("="*80)
    print("\nEvent: 2025 Chile World Cup (Event ID: 321865)")
    print("\nOLD METHOD: Gets heats[0] only (final heat)")
    print("NEW METHOD: Processes ALL heats to get every competitor")
    print("="*80)

    scraper = LiveHeatsTestScraper()

    # Test Women
    women_results = scraper.fetch_division_rankings(584951, "Women")

    # Test Men
    men_results = scraper.fetch_division_rankings(584952, "Men")

    # Summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print(f"Women:")
    print(f"  OLD METHOD: 4 results")
    print(f"  NEW METHOD: {len(women_results) if women_results else 0} results")
    print(f"\nMen:")
    print(f"  OLD METHOD: 3 results")
    print(f"  NEW METHOD: {len(men_results) if men_results else 0} results")
    print(f"\nTOTAL:")
    print(f"  OLD: 7 results")
    print(f"  NEW: {(len(women_results) if women_results else 0) + (len(men_results) if men_results else 0)} results")
    print("="*80)


if __name__ == "__main__":
    main()
