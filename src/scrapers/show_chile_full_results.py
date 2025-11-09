"""
Show Full Chile 2025 Results - Complete Rankings
"""

import requests


class ChileResultsViewer:
    """Display full Chile results"""

    def __init__(self):
        self.graphql_url = "https://liveheats.com/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

    def calculate_final_rankings_from_all_heats(self, heats_data):
        """Calculate final rankings from all heats"""
        athlete_best = {}

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

        sorted_athletes = sorted(athlete_best.items(), key=lambda x: (-x[1][0], x[1][1]))

        rankings = []
        prev_key = None
        final_rank = 1

        for i, (athlete_id, (round_pos, heat_place)) in enumerate(sorted_athletes):
            if i > 0 and (round_pos, heat_place) != prev_key:
                final_rank = i + 1

            rankings.append({
                'place': final_rank,
                'athleteId': athlete_id,
                'round_reached': round_pos,
                'heat_place': heat_place
            })

            prev_key = (round_pos, heat_place)

        return rankings

    def fetch_division_rankings(self, division_id):
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

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                return None

            event_division = data['data']['eventDivision']
            heats = event_division.get('heats', [])
            rankings = self.calculate_final_rankings_from_all_heats(heats)

            return rankings

        except Exception as e:
            print(f"Error: {e}")
            return None


def main():
    """Display full Chile results"""

    print("="*80)
    print("CHILE 2025 WORLD CUP - COMPLETE FINAL RESULTS")
    print("Source: Live Heats (ALL heats processed)")
    print("="*80)

    viewer = ChileResultsViewer()

    # WOMEN
    print("\nWOMEN'S DIVISION (584951)")
    print("="*80)
    women_results = viewer.fetch_division_rankings(584951)

    if women_results:
        print(f"\n{'Place':<8} {'Athlete ID':<15} {'Round Reached':<15} {'Heat Position':<15}")
        print("-"*80)
        for result in women_results:
            print(f"{result['place']:<8} {result['athleteId']:<15} Round {result['round_reached']:<13} {result['heat_place']:<15}")
        print(f"\nTotal Competitors: {len(women_results)}")

    # MEN
    print("\n\n" + "="*80)
    print("MEN'S DIVISION (584952)")
    print("="*80)
    men_results = viewer.fetch_division_rankings(584952)

    if men_results:
        print(f"\n{'Place':<8} {'Athlete ID':<15} {'Round Reached':<15} {'Heat Position':<15}")
        print("-"*80)
        for result in men_results:
            print(f"{result['place']:<8} {result['athleteId']:<15} Round {result['round_reached']:<13} {result['heat_place']:<15}")
        print(f"\nTotal Competitors: {len(men_results)}")

    # SUMMARY
    print("\n\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Women Competitors: {len(women_results) if women_results else 0}")
    print(f"Men Competitors: {len(men_results) if men_results else 0}")
    print(f"Total: {(len(women_results) if women_results else 0) + (len(men_results) if men_results else 0)}")
    print("="*80)


if __name__ == "__main__":
    main()
