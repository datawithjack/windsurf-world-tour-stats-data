"""
Scrape Live Heats Final Results for Matched PWA Events
Extracts final rankings from Live Heats for events missing from PWA
Output format matches PWA results CSV structure
"""

import json
from datetime import datetime
import pandas as pd
import requests


class LiveHeatsResultsScraper:
    """Scraper for Live Heats final rankings"""

    def __init__(self, matching_report_path):
        """
        Initialize scraper

        Args:
            matching_report_path: Path to PWA-LiveHeats matching report CSV
        """
        self.matching_report_path = matching_report_path
        self.graphql_url = "https://liveheats.com/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        self.results_data = []
        self.scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.stats = {
            'total_divisions': 0,
            'divisions_scraped': 0,
            'total_athletes': 0,
            'errors': 0
        }

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_matched_divisions(self):
        """
        Load matched divisions from matching report

        Returns:
            DataFrame of divisions to scrape
        """
        self.log("Loading matching report...")
        df = pd.read_csv(self.matching_report_path)

        # Filter for matched divisions with results
        matched = df[
            (df['matched'] == True) &
            (df['liveheats_has_results'] == True)
        ].copy()

        self.log(f"Found {len(matched)} matched divisions with Live Heats results")
        return matched

    def fetch_athlete_details(self, athlete_id):
        """
        Fetch athlete details from Live Heats

        Args:
            athlete_id: Live Heats athlete ID

        Returns:
            Dict with athlete info or None
        """
        query = """
        query getUser($id: ID!) {
          user(id: $id) {
            id
            firstName
            lastName
            sailNumber
            country
          }
        }
        """

        variables = {"id": str(athlete_id)}
        payload = {"query": query, "variables": variables}

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'errors' in data:
                # Try alternate query structure
                return None

            user = data.get('data', {}).get('user')
            return user

        except Exception as e:
            return None

    def calculate_final_rankings_from_all_heats(self, heats_data):
        """
        Calculate final rankings by finding each athlete's best round progression
        This ensures we capture ALL athletes who competed, not just finalists

        Args:
            heats_data: List of heats with results

        Returns:
            List of ranking dicts sorted by final placement
        """
        athlete_best = {}

        # Process all heats to find each athlete's furthest progression
        for heat in heats_data:
            round_position = heat.get('roundPosition', 0)

            for result in heat.get('result', []):
                athlete_id = result.get('athleteId')
                place_in_heat = int(result.get('place', 999)) if result.get('place') is not None else 999

                if athlete_id:
                    stored = athlete_best.get(athlete_id)

                    # Keep the best (furthest round, or best placement if same round)
                    if stored:
                        stored_round, stored_place = stored
                        if round_position > stored_round or (round_position == stored_round and place_in_heat < stored_place):
                            athlete_best[athlete_id] = (round_position, place_in_heat)
                    else:
                        athlete_best[athlete_id] = (round_position, place_in_heat)

        # Sort athletes by: highest round first, then best placement in that round
        sorted_athletes = sorted(athlete_best.items(), key=lambda x: (-x[1][0], x[1][1]))

        # Assign final rankings
        rankings = []
        prev_key = None
        final_rank = 1

        for i, (athlete_id, (round_pos, heat_place)) in enumerate(sorted_athletes):
            # Same rank for ties (same round + same heat placement)
            if i > 0 and (round_pos, heat_place) != prev_key:
                final_rank = i + 1

            rankings.append({
                'athleteId': athlete_id,
                'place': final_rank
            })

            prev_key = (round_pos, heat_place)

        return rankings

    def fetch_division_rankings(self, event_id, division_id):
        """
        Fetch final rankings for a specific event division from Live Heats
        Gets ALL athlete results by processing all heats, not just finalists
        Uses the same proven query structure as the working historical scraper

        Args:
            event_id: Live Heats event ID
            division_id: Live Heats division ID

        Returns:
            List of ranking dicts with athlete details or None if error
        """
        # Full query matching the working historical scraper - gets ALL heat data
        query = """query getEventDivision($id: ID!) {
          eventDivision(id: $id) {
            id
            heatDurationMinutes
            defaultEventDurationMinutes
            formatDefinition { progression runProgression heatSizes seeds defaultHeatDurationMinutes numberOfRounds }
            heatConfig { hasPriority totalCountingRides athleteRidesLimit }
            division { id name }
            heats {
              id eventDivisionId round roundPosition position startTime endTime heatDurationMinutes
              config { maxRideScore heatSize }
              result { athleteId total winBy needs rides place }
            }
          }
        }"""

        variables = {
            "id": str(division_id)
        }

        payload = {"query": query, "variables": variables}

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'errors' in data:
                self.log(f"GraphQL errors: {data['errors']}", "ERROR")
                return None

            event_division = data.get('data', {}).get('eventDivision')

            if not event_division:
                self.log("No event division found in response", "WARNING")
                return None

            heats = event_division.get('heats', [])

            if not heats or len(heats) == 0:
                self.log("No heats found in division", "WARNING")
                return None

            # Calculate final rankings from ALL heats (gets all competitors)
            rankings = self.calculate_final_rankings_from_all_heats(heats)

            self.log(f"  Extracted {len(rankings)} complete rankings from all heats")

            return rankings

        except Exception as e:
            self.log(f"Error fetching rankings: {e}", "ERROR")
            return None

    def transform_to_pwa_format(self, rankings, pwa_event_info):
        """
        Transform Live Heats rankings to PWA results format

        Args:
            rankings: List of Live Heats ranking dicts
            pwa_event_info: Dict with PWA event metadata

        Returns:
            List of result dicts in PWA format
        """
        results = []

        for rank in rankings:
            # Get athlete details from result
            athlete_id = rank.get('athleteId', '')
            place = rank.get('place', '')

            # Note: Athlete names not available from Live Heats public API
            # These fields remain empty and can be populated later via athlete ID matching
            athlete_name = ''
            sail_number = ''

            result = {
                'source': 'Live Heats',
                'scraped_at': self.scraped_at,
                'event_id': pwa_event_info['pwa_event_id'],
                'year': pwa_event_info['pwa_year'],
                'event_name': pwa_event_info['pwa_event_name'],
                'division_label': pwa_event_info['pwa_division_label'],
                'division_code': pwa_event_info['liveheats_division_id'],
                'sex': pwa_event_info['sex'],
                'place': place,
                'athlete_name': athlete_name,
                'sail_number': sail_number,
                'athlete_id': athlete_id
            }

            results.append(result)
            self.stats['total_athletes'] += 1

        return results

    def scrape_all_matched_divisions(self):
        """Scrape results for all matched divisions"""
        matched_df = self.load_matched_divisions()

        if matched_df.empty:
            self.log("No matched divisions to scrape!", "WARNING")
            return

        self.stats['total_divisions'] = len(matched_df)

        self.log("\n" + "="*80)
        self.log("SCRAPING LIVE HEATS RESULTS")
        self.log("="*80 + "\n")

        for idx, row in matched_df.iterrows():
            pwa_event_id = row['pwa_event_id']
            pwa_event_name = row['pwa_event_name']
            pwa_division_label = row['pwa_division_label']
            lh_event_id = row['liveheats_event_id']
            lh_division_id = row['liveheats_division_id']
            lh_division_name = row['liveheats_division_name']

            self.log(f"Processing: {pwa_event_name} - {pwa_division_label}")
            self.log(f"  Live Heats Event: {lh_event_id}, Division: {lh_division_id} ({lh_division_name})")

            # Fetch rankings
            rankings = self.fetch_division_rankings(lh_event_id, lh_division_id)

            if not rankings:
                self.log(f"  No rankings found or error occurred", "WARNING")
                self.stats['errors'] += 1
                continue

            self.log(f"  Found {len(rankings)} athletes")

            # Prepare PWA event info
            pwa_event_info = {
                'pwa_event_id': pwa_event_id,
                'pwa_year': row['pwa_year'],
                'pwa_event_name': pwa_event_name,
                'pwa_division_label': pwa_division_label,
                'liveheats_division_id': lh_division_id,
                'sex': row['pwa_division_label'].split()[-1]  # "Wave Men" -> "Men"
            }

            # Transform to PWA format
            results = self.transform_to_pwa_format(rankings, pwa_event_info)

            if results:
                self.results_data.extend(results)
                self.stats['divisions_scraped'] += 1
                self.log(f"  [OK] Scraped {len(results)} results")

        self.log("\n" + "="*80)
        self.log("SCRAPING COMPLETE")
        self.log("="*80)

    def save_results(self, output_path):
        """
        Save results to CSV

        Args:
            output_path: Path to output CSV file
        """
        if not self.results_data:
            self.log("No results to save!", "WARNING")
            return

        df = pd.DataFrame(self.results_data)

        # Ensure column order matches PWA results
        column_order = [
            'source', 'scraped_at', 'event_id', 'year', 'event_name',
            'division_label', 'division_code', 'sex', 'place',
            'athlete_name', 'sail_number', 'athlete_id'
        ]

        df = df[column_order]

        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        self.log(f"\nResults saved to: {output_path}")
        self.log(f"Total rows: {len(df)}")

    def print_summary(self):
        """Print summary statistics"""
        self.log("\n" + "="*80)
        self.log("SUMMARY STATISTICS")
        self.log("="*80)
        self.log(f"Total divisions to scrape: {self.stats['total_divisions']}")
        self.log(f"Divisions successfully scraped: {self.stats['divisions_scraped']}")
        self.log(f"Errors: {self.stats['errors']}")
        self.log(f"Total athletes extracted: {self.stats['total_athletes']}")
        self.log("="*80 + "\n")


def main():
    """Main execution"""
    print("="*80)
    print("LIVE HEATS RESULTS SCRAPER - MATCHED PWA EVENTS")
    print("="*80)
    print()

    # Get project root (assuming script is in src/scrapers/)
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Input and output paths
    matching_report = os.path.join(project_root, 'data', 'reports', 'pwa_liveheats_matching_report_v2.csv')
    output_path = os.path.join(project_root, 'data', 'raw', 'liveheats', 'liveheats_matched_results.csv')

    # Initialize scraper
    scraper = LiveHeatsResultsScraper(matching_report)

    try:
        # Scrape all matched divisions
        scraper.scrape_all_matched_divisions()

        # Save results
        scraper.save_results(output_path)

        # Print summary
        scraper.print_summary()

    except Exception as e:
        scraper.log(f"FATAL ERROR: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
