"""
Scrape Live Heats Heat Data for Matched PWA Events
Extracts heat progression, heat results, and heat scores from Live Heats
Uses proven code structure from functions_iwt_scrape.py

Output Files:
- liveheats_heat_progression.csv (heat structure and progression rules)
- liveheats_heat_results.csv (athlete placements per heat)
- liveheats_heat_scores.csv (individual wave/ride scores)
"""

import json
import os
from datetime import datetime
import pandas as pd
import requests


class LiveHeatsHeatDataScraper:
    """Scraper for Live Heats heat-level data"""

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

        # Data storage
        self.progression_data = []
        self.results_data = []
        self.scores_data = []

        self.stats = {
            'total_divisions': 0,
            'divisions_processed': 0,
            'total_heats': 0,
            'total_results': 0,
            'total_scores': 0,
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

    def fetch_event_division_data(self, division_id):
        """
        Fetch complete event division data from Live Heats
        Uses the full query from functions_iwt_scrape.py

        Args:
            division_id: Live Heats division ID

        Returns:
            JSON response data or None if error
        """
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

        variables = {"id": str(division_id)}
        payload = {"query": query, "variables": variables}

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'errors' in data:
                self.log(f"GraphQL errors: {data['errors']}", "ERROR")
                return None

            return data

        except Exception as e:
            self.log(f"Error fetching division data: {e}", "ERROR")
            return None

    def flatten_heat_progression(self, data, event_id, division_id, pwa_event_info):
        """
        Extract heat progression data (adapted from functions_iwt_scrape.py)

        Args:
            data: GraphQL response data
            event_id: Live Heats event ID
            division_id: Live Heats division ID
            pwa_event_info: Dict with PWA event metadata

        Returns:
            List of progression records
        """
        try:
            ed = data["data"]["eventDivision"]
            prog = ed["formatDefinition"]["progression"]
            heats = ed["heats"]
            division_name = ed["division"]["name"]
        except (KeyError, TypeError):
            self.log(f"  Could not extract progression for division {division_id}", "WARNING")
            return []

        records = []
        for heat in heats:
            rec = {
                'source': 'Live Heats',
                'pwa_event_id': pwa_event_info['pwa_event_id'],
                'pwa_year': pwa_event_info['pwa_year'],
                'pwa_event_name': pwa_event_info['pwa_event_name'],
                'liveheats_event_id': event_id,
                'liveheats_division_id': division_id,
                'division_name': division_name,
                'sex': pwa_event_info['sex'],
                'round_name': heat.get('round'),
                'round_order': heat.get('roundPosition'),
                'heat_id': heat.get('id'),
                'heat_order': heat.get('position')
            }

            # Get progression rules for this round
            entries = prog.get(str(heat.get('roundPosition')), []) or prog.get('default', [])

            for i in range(2):
                if i < len(entries):
                    e = entries[i]
                    maxv = e.get('max')
                    to_round = e.get('to_round') or (maxv + 1 if maxv else None)
                    rec[f'progression_{i}_max'] = maxv
                    rec[f'progression_{i}_to_round'] = to_round
                else:
                    rec[f'progression_{i}_max'] = None
                    rec[f'progression_{i}_to_round'] = None

            records.append(rec)

        return records

    def flatten_heat_results_and_scores(self, data, event_id, division_id, pwa_event_info):
        """
        Extract heat results and scores (adapted from functions_iwt_scrape.py)

        Args:
            data: GraphQL response data
            event_id: Live Heats event ID
            division_id: Live Heats division ID
            pwa_event_info: Dict with PWA event metadata

        Returns:
            Tuple of (results_records, scores_records)
        """
        try:
            heats = data['data']['eventDivision']['heats']
        except (KeyError, TypeError):
            self.log(f"  Could not extract results/scores for division {division_id}", "WARNING")
            return [], []

        results_rows = []
        scores_rows = []

        for heat in heats:
            hid = heat.get('id')
            edid = heat.get('eventDivisionId')
            rlabel = heat.get('round')
            rpos = heat.get('roundPosition', 0)

            for res in heat.get('result', []):
                # Heat result record
                base = {
                    'source': 'Live Heats',
                    'pwa_event_id': pwa_event_info['pwa_event_id'],
                    'pwa_year': pwa_event_info['pwa_year'],
                    'pwa_event_name': pwa_event_info['pwa_event_name'],
                    'liveheats_event_id': event_id,
                    'liveheats_division_id': division_id,
                    'sex': pwa_event_info['sex'],
                    'heat_id': hid,
                    'athlete_id': res.get('athleteId'),
                    'result_total': res.get('total'),
                    'win_by': res.get('winBy'),
                    'needs': res.get('needs'),
                    'place': res.get('place'),
                    'round': rlabel,
                    'round_position': rpos
                }
                results_rows.append(base)

                # Heat scores records
                rides = res.get('rides') or {}
                for ride_list in rides.values():
                    for ride in ride_list:
                        scores_rows.append({
                            'source': 'Live Heats',
                            'pwa_event_id': pwa_event_info['pwa_event_id'],
                            'pwa_year': pwa_event_info['pwa_year'],
                            'pwa_event_name': pwa_event_info['pwa_event_name'],
                            'liveheats_event_id': event_id,
                            'liveheats_division_id': division_id,
                            'sex': pwa_event_info['sex'],
                            'heat_id': hid,
                            'athlete_id': res.get('athleteId'),
                            'score': ride.get('total'),
                            'modified_total': ride.get('modified_total'),
                            'modifier': ride.get('modifier'),
                            'type': ride.get('category', '').rstrip('s') if ride.get('category') else '',
                            'counting': ride.get('scoring_ride')
                        })

        return results_rows, scores_rows

    def process_all_divisions(self):
        """Process all matched divisions"""
        matched_df = self.load_matched_divisions()

        if matched_df.empty:
            self.log("No matched divisions to process!", "WARNING")
            return

        self.stats['total_divisions'] = len(matched_df)

        self.log("\n" + "="*80)
        self.log("SCRAPING LIVE HEATS HEAT DATA")
        self.log("="*80 + "\n")

        for idx, row in matched_df.iterrows():
            pwa_event_id = row['pwa_event_id']
            pwa_event_name = row['pwa_event_name']
            pwa_year = row['pwa_year']
            pwa_division_label = row['pwa_division_label']
            lh_event_id = row['liveheats_event_id']
            lh_division_id = row['liveheats_division_id']
            lh_division_name = row['liveheats_division_name']

            self.log(f"Processing: {pwa_event_name} - {pwa_division_label}")
            self.log(f"  Live Heats Event: {lh_event_id}, Division: {lh_division_id} ({lh_division_name})")

            # Prepare PWA event info
            pwa_event_info = {
                'pwa_event_id': pwa_event_id,
                'pwa_year': pwa_year,
                'pwa_event_name': pwa_event_name,
                'pwa_division_label': pwa_division_label,
                'sex': pwa_division_label.split()[-1] if pwa_division_label else ''  # "Wave Men" -> "Men"
            }

            # Fetch complete division data
            data = self.fetch_event_division_data(lh_division_id)

            if not data:
                self.log(f"  Failed to fetch data", "ERROR")
                self.stats['errors'] += 1
                continue

            # Extract heat progression
            progression_records = self.flatten_heat_progression(data, lh_event_id, lh_division_id, pwa_event_info)
            if progression_records:
                self.progression_data.extend(progression_records)
                self.stats['total_heats'] += len(progression_records)
                self.log(f"  Extracted {len(progression_records)} heat progression records")

            # Extract heat results and scores
            results_records, scores_records = self.flatten_heat_results_and_scores(data, lh_event_id, lh_division_id, pwa_event_info)

            if results_records:
                self.results_data.extend(results_records)
                self.stats['total_results'] += len(results_records)
                self.log(f"  Extracted {len(results_records)} heat result records")

            if scores_records:
                self.scores_data.extend(scores_records)
                self.stats['total_scores'] += len(scores_records)
                self.log(f"  Extracted {len(scores_records)} heat score records")

            self.stats['divisions_processed'] += 1
            self.log(f"  [OK] Division processed successfully\n")

        self.log("="*80)
        self.log("SCRAPING COMPLETE")
        self.log("="*80)

    def save_data(self, output_dir):
        """
        Save all extracted data to CSV files

        Args:
            output_dir: Directory to save CSV files
        """
        os.makedirs(output_dir, exist_ok=True)

        # Save heat progression
        if self.progression_data:
            df_prog = pd.DataFrame(self.progression_data)

            # Rename columns to match PWA format
            df_prog = df_prog.rename(columns={
                'progression_0_max': 'total_winners_progressing',
                'progression_0_to_round': 'winners_progressing_to_round_order',
                'progression_1_max': 'total_losers_progressing',
                'progression_1_to_round': 'losers_progressing_to_round_order'
            })

            prog_path = os.path.join(output_dir, 'liveheats_heat_progression.csv')
            df_prog.to_csv(prog_path, index=False, encoding='utf-8-sig')
            self.log(f"\nHeat progression saved to: {prog_path}")
            self.log(f"  Total records: {len(df_prog)}")

        # Save heat results
        if self.results_data:
            df_results = pd.DataFrame(self.results_data)
            results_path = os.path.join(output_dir, 'liveheats_heat_results.csv')
            df_results.to_csv(results_path, index=False, encoding='utf-8-sig')
            self.log(f"\nHeat results saved to: {results_path}")
            self.log(f"  Total records: {len(df_results)}")

        # Save heat scores
        if self.scores_data:
            df_scores = pd.DataFrame(self.scores_data)

            # Calculate total_points (sum of counting scores per athlete per heat)
            summary = (
                df_scores[df_scores['counting'] == True]
                .groupby(['heat_id', 'athlete_id'])['score']
                .sum()
                .reset_index()
                .rename(columns={'score': 'total_points'})
            )
            df_scores = pd.merge(df_scores, summary, on=['heat_id', 'athlete_id'], how='left')
            df_scores['total_points'] = df_scores['total_points'].fillna(0)

            scores_path = os.path.join(output_dir, 'liveheats_heat_scores.csv')
            df_scores.to_csv(scores_path, index=False, encoding='utf-8-sig')
            self.log(f"\nHeat scores saved to: {scores_path}")
            self.log(f"  Total records: {len(df_scores)}")

    def print_summary(self):
        """Print summary statistics"""
        self.log("\n" + "="*80)
        self.log("SUMMARY STATISTICS")
        self.log("="*80)
        self.log(f"Total divisions to process: {self.stats['total_divisions']}")
        self.log(f"Divisions successfully processed: {self.stats['divisions_processed']}")
        self.log(f"Errors: {self.stats['errors']}")
        self.log(f"")
        self.log(f"Total heats extracted: {self.stats['total_heats']}")
        self.log(f"Total heat results extracted: {self.stats['total_results']}")
        self.log(f"Total heat scores extracted: {self.stats['total_scores']}")
        self.log("="*80 + "\n")


def main():
    """Main execution"""
    print("="*80)
    print("LIVE HEATS HEAT DATA SCRAPER - MATCHED PWA EVENTS")
    print("="*80)
    print()

    # Get project root (assuming script is in src/scrapers/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Input and output paths
    matching_report = os.path.join(project_root, 'data', 'reports', 'pwa_liveheats_matching_report_v2.csv')
    output_dir = os.path.join(project_root, 'data', 'raw', 'liveheats')

    # Initialize scraper
    scraper = LiveHeatsHeatDataScraper(matching_report)

    try:
        # Process all matched divisions
        scraper.process_all_divisions()

        # Save data
        scraper.save_data(output_dir)

        # Print summary
        scraper.print_summary()

        print("="*80)
        print("SCRAPING COMPLETE!")
        print("="*80)

    except Exception as e:
        scraper.log(f"FATAL ERROR: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
