"""
PWA Wave Heat Data Scraper
Extracts heat structure, heat results, and heat scores from PWA events
Based on old scripts in old_scripts/Script/functions_pwa_scrape.py

Data sources:
- Heat Structure & Results: XML endpoint (live_ladder_{category_code}.xml)
- Heat Scores: JSON endpoint (live_score/{heat_id}.json)

Input: pwa_division_results_tracking.csv
Output:
  - pwa_heat_structure.csv
  - pwa_heat_results.csv
  - pwa_heat_scores.csv
  - pwa_division_results_tracking.csv (updated with heat data flags)
"""

import time
import re
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
import unicodedata
import urllib3

# Disable SSL warnings (PWA site has SSL issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PWAHeatScraper:
    """Scraper for PWA wave event heat data (structure, results, scores)"""

    def __init__(self, tracking_csv_path, event_ids=None):
        """
        Initialize the scraper

        Args:
            tracking_csv_path: Path to PWA division tracking CSV file
            event_ids: Optional list of event IDs to filter (default: None = scrape all)
        """
        self.tracking_csv_path = tracking_csv_path
        self.event_ids_filter = set(map(int, event_ids)) if event_ids else None
        self.heat_structure_data = []
        self.heat_results_data = []
        self.heat_scores_data = []
        self.scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create session with retry logic
        self.session = self._create_session()

        # Statistics
        self.stats = {
            'total_events': 0,
            'events_with_heat_structure': 0,
            'events_with_heat_results': 0,
            'events_with_heat_scores': 0,
            'total_heats': 0,
            'total_heat_results': 0,
            'total_heat_scores': 0,
            'errors': 0
        }

    def _create_session(self):
        """Create requests session with retry logic"""
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_divisions_to_scrape(self):
        """
        Load divisions from tracking CSV that have results

        Returns:
            DataFrame of divisions to scrape for heat data
        """
        self.log("Loading PWA division tracking data...")
        df = pd.read_csv(self.tracking_csv_path)

        # Filter for divisions with results (2016+, has_results=True)
        # Excluding 2020-2021 (COVID years with no published results)
        divisions_with_results = df[
            (df['year'] >= 2016) &
            (df['year'] != 2020) &
            (df['year'] != 2021) &
            (df['has_results'] == True)
        ].copy()

        # If event_ids filter is set, filter by event IDs
        if self.event_ids_filter:
            divisions_with_results = divisions_with_results[
                divisions_with_results['event_id'].isin(self.event_ids_filter)
            ].copy()
            self.log(f"Filtered to {len(divisions_with_results)} divisions from {len(self.event_ids_filter)} specified event IDs")

        self.log(f"Found {len(divisions_with_results)} divisions with results to check for heat data")
        return divisions_with_results

    def fetch_category_codes(self, event_id):
        """
        Fetch all category codes (elimination ladder IDs) for an event

        Args:
            event_id: PWA event ID

        Returns:
            List of dicts with category_code and elimination_name
        """
        url = f'https://www.pwaworldtour.com/index.php?id=1900&type=21&tx_pwaevent_pi1%5Baction%5D=ladders&tx_pwaevent_pi1%5BshowUid%5D={event_id}'

        try:
            from bs4 import BeautifulSoup

            response = self.session.get(url, timeout=30, verify=False)

            if response.status_code != 200:
                self.log(f"Failed to fetch ladders page for event {event_id}: HTTP {response.status_code}", "WARNING")
                return []

            soup = BeautifulSoup(response.content, 'lxml')

            # Check for "no elimination ladders" message
            no_ladders = soup.find_all(class_='no-entries-found-msg')
            if no_ladders:
                self.log(f"No elimination ladders found for event {event_id}", "INFO")
                return []

            # Find all ladder links
            ladder_links = soup.find_all('a', href=True)

            category_codes = []
            for link in ladder_links:
                href = link.get('href', '')
                if '%5Bladder%5D=' in href:
                    try:
                        category_code = href.split('%5Bladder%5D=')[-1].split('&')[0]
                        elimination_name = link.text.strip()

                        # Only include wave eliminations
                        if 'wave' in elimination_name.lower():
                            category_codes.append({
                                'category_code': category_code,
                                'elimination_name': elimination_name
                            })
                            self.log(f"  Found category code {category_code}: {elimination_name}")
                    except:
                        pass

            return category_codes

        except Exception as e:
            self.log(f"Error fetching category codes for event {event_id}: {e}", "ERROR")
            self.stats['errors'] += 1
            return []

    def fetch_heat_structure_and_results(self, event_id, category_code):
        """
        Fetch heat structure and results from PWA XML endpoint
        Based on export_heat_progression_and_results() from old scripts

        Args:
            event_id: PWA event ID
            category_code: Category/ladder code (represents one elimination)

        Returns:
            Tuple of (heat_structure_list, heat_results_list, unique_heat_ids)
        """
        xml_url = f'https://www.pwaworldtour.com/fileadmin/live_ladder/live_ladder_{category_code}.xml'

        try:
            response = self.session.get(xml_url, timeout=30, verify=False)

            if response.status_code != 200:
                self.log(f"Failed to fetch XML for category {category_code}: HTTP {response.status_code}", "WARNING")
                return [], [], []

            # Parse XML
            root = ET.fromstring(response.content)

            heat_structure = []
            heat_results = []

            # Process each elimination block in the XML
            for elimination in root.findall('elimination'):
                discipline = elimination.find('discipline').text if elimination.find('discipline') is not None else None

                if discipline != 'wave':
                    continue  # Only process 'wave' discipline

                event = elimination.find('event').text if elimination.find('event') is not None else None
                elimination_name = elimination.find('name').text if elimination.find('name') is not None else None
                sex = elimination.find('sex').text if elimination.find('sex') is not None else None
                event_division_id = elimination.find('eventDivisionId').text if elimination.find('eventDivisionId') is not None else None
                ladder_id = elimination.find('ladderId').text if elimination.find('ladderId') is not None else None
                e_discipline_id = elimination.find('eDisciplineId').text if elimination.find('eDisciplineId') is not None else None
                elimination_toadvance = elimination.find('toAdvance').text if elimination.find('toAdvance') is not None else None

                # Map sex values: "male" -> "Men" and "female" -> "Women"
                sex_mapping = {'male': 'Men', 'female': 'Women'}
                sex_normalized = sex_mapping.get(sex, sex)

                rounds = elimination.find('rounds')
                if rounds is None:
                    continue

                # Loop through each round
                for round_elem in rounds.findall('round'):
                    round_name_raw = round_elem.find('name').text if round_elem.find('name') is not None else None

                    # Try to extract toAdvance from the round; if missing, fall back to elimination level
                    round_toadvance_elem = round_elem.find('toAdvance')
                    if round_toadvance_elem is not None and round_toadvance_elem.text is not None:
                        toadvance = round_toadvance_elem.text
                    else:
                        toadvance = elimination_toadvance

                    # Compute round_order and add "Round " prefix to round_name
                    if round_name_raw and round_name_raw.isdigit():
                        round_order = int(round_name_raw) - 1
                        round_name = f"Round {round_name_raw}"
                    else:
                        round_order = None
                        round_name = f"Round {round_name_raw}" if round_name_raw else None

                    # --- Extract heat structure data ---
                    for heat_group in round_elem.findall('heats/heatGroup'):
                        for heat in heat_group.findall('heat'):
                            heat_id = heat.find('heatId').text if heat.find('heatId') is not None else None
                            heat_name = heat.find('heatName').text if heat.find('heatName') is not None else None

                            heat_structure.append({
                                'source': 'PWA',
                                'scraped_at': self.scraped_at,
                                'event_id': event_id,
                                'category_code': category_code,
                                'ladder_id': ladder_id,
                                'e_discipline_id': e_discipline_id,
                                'sex': sex_normalized,
                                'elimination_name': elimination_name,
                                'round_name': round_name,
                                'round_order': round_order,
                                'heat_id': heat_id,
                                'heat_order': heat_name,
                                'total_winners_progressing': toadvance,
                                'winners_progressing_to_round_order': '',
                                'total_losers_progressing': '',
                                'losers_progressing_to_round_order': ''
                            })

                    # --- Extract sailor-level heat results ---
                    for heat_group in round_elem.findall('heats/heatGroup'):
                        for heat in heat_group.findall('heat'):
                            heat_id = heat.find('heatId').text if heat.find('heatId') is not None else None
                            heat_name = heat.find('heatName').text if heat.find('heatName') is not None else None
                            sailors_node = heat.find('sailors')

                            if sailors_node is None:
                                continue

                            for sailor in sailors_node.findall('sailor'):
                                sailor_name = sailor.find('sailorName').text if sailor.find('sailorName') is not None else None
                                sail_nr = sailor.find('sailNr').text if sailor.find('sailNr') is not None else None
                                place = sailor.find('place').text if sailor.find('place') is not None else None

                                # Create athlete_id by combining sailor name and number
                                athlete_id = f"{sailor_name}_{sail_nr}" if sailor_name and sail_nr else ''

                                heat_results.append({
                                    'source': 'PWA',
                                    'scraped_at': self.scraped_at,
                                    'event_id': event_id,
                                    'category_code': category_code,
                                    'ladder_id': ladder_id,
                                    'e_discipline_id': e_discipline_id,
                                    'heat_id': heat_id,
                                    'athlete_id': athlete_id,
                                    'sailor_name': sailor_name,
                                    'sail_number': sail_nr,
                                    'place': place,
                                    'result_total': '',  # To be merged from heat scores
                                    'win_by': '',
                                    'needs': ''
                                })

            # Get unique heat IDs for heat scores extraction
            unique_heat_ids = list(set([hr['heat_id'] for hr in heat_results if hr.get('heat_id')]))

            self.log(f"  Found {len(heat_structure)} heat structure entries, {len(heat_results)} heat results, {len(unique_heat_ids)} unique heats")

            return heat_structure, heat_results, unique_heat_ids

        except Exception as e:
            self.log(f"Error fetching heat structure/results for category {category_code}: {e}", "ERROR")
            self.stats['errors'] += 1
            return [], [], []

    def fetch_heat_scores(self, event_id, category_code, heat_ids):
        """
        Fetch heat scores from PWA JSON endpoint
        Based on export_heat_scores() from old scripts

        Args:
            event_id: PWA event ID
            category_code: Category/ladder code
            heat_ids: List of heat IDs to fetch scores for

        Returns:
            List of heat score dicts
        """
        api_base_url = "https://www.pwaworldtour.com/fileadmin/live_score/"
        heat_scores = []

        for heat_id in heat_ids:
            try:
                api_url = f"{api_base_url}{heat_id}.json"
                response = self.session.get(api_url, timeout=30, verify=False)
                response.raise_for_status()
                heatsheet_json = response.json()

                # Basic heat info
                heat_info = {
                    'heat_id': heatsheet_json['heat']['heatId'],
                    'heat_no': heatsheet_json['heat']['heatNo'],
                    'wave_count': heatsheet_json['heat']['waveCount'],
                    'jumps_count': heatsheet_json['heat']['jumpsCount'],
                    'wave_factor': heatsheet_json['heat']['waveFactor'],
                    'jump_factor': heatsheet_json['heat']['jumpFactor'],
                }

                # Process each sailor in the heat
                for sailor_info in heatsheet_json['heat']['sailors']:
                    sailor = sailor_info['sailor']

                    # Normalize sailor name
                    sailor_name = unicodedata.normalize('NFKD', sailor.get('sailorName', ''))
                    sail_no = sailor.get('sailNo', '')
                    athlete_id = f"{sailor.get('sailorName', '')}_{sail_no}" if sailor.get('sailorName') and sail_no else ''

                    base_info = {
                        'source': 'PWA',
                        'scraped_at': self.scraped_at,
                        'event_id': event_id,
                        'category_code': category_code,
                        'heat_id': heat_id,
                        'athlete_id': athlete_id,
                        'sailor_name': sailor.get('sailorName', ''),
                        'sail_number': sail_no,
                        'total_wave': sailor.get('totalWave', ''),
                        'total_jump': sailor.get('totalJump', ''),
                        'total_points': sailor.get('totalPoints', ''),
                        'position': sailor.get('totalPos', ''),
                    }

                    combined_info = {**heat_info, **base_info}

                    # Process each score (wave or jump)
                    for score_type, score_list in sailor.get('scores', {}).items():
                        for score in score_list:
                            if not isinstance(score, dict):
                                continue

                            row = combined_info.copy()
                            row['type'] = 'Wave' if score_type == 'wave' else score.get('type', '')
                            row['score'] = score.get('score', None)
                            row['counting'] = 'Yes' if score.get('counting') else 'No'
                            row['modified_total'] = ''
                            row['modifier'] = ''

                            heat_scores.append(row)

                self.log(f"  Successfully fetched scores for Heat ID {heat_id}")

            except Exception as e:
                self.log(f"  Failed to fetch scores for Heat ID {heat_id}: {e}", "WARNING")
                continue

        return heat_scores

    def scrape_event_heat_data(self, event_id, event_name, year):
        """
        Scrape all heat data for a single event (all eliminations)

        Args:
            event_id: PWA event ID
            event_name: Event name
            year: Event year

        Returns:
            Dict with flags indicating what heat data was found
        """
        self.log(f"\n{'='*80}")
        self.log(f"Processing Event: {event_name} ({year})")
        self.log(f"Event ID: {event_id}")
        self.log(f"{'='*80}")

        # Step 1: Fetch all category codes (eliminations) for this event
        category_codes = self.fetch_category_codes(event_id)

        if not category_codes:
            self.log("No elimination ladders found for this event")
            return {
                'has_heat_structure': False,
                'has_heat_results': False,
                'has_heat_scores': False,
                'heat_count': 0,
                'category_count': 0
            }

        self.log(f"Found {len(category_codes)} elimination ladder(s)")

        total_has_structure = False
        total_has_results = False
        total_has_scores = False
        total_heat_count = 0

        # Step 2: For each category code, fetch heat structure, results, and scores
        for cat_info in category_codes:
            category_code = cat_info['category_code']
            elimination_name = cat_info['elimination_name']

            self.log(f"\nProcessing category {category_code}: {elimination_name}")

            # Fetch heat structure and results
            heat_structure, heat_results, heat_ids = self.fetch_heat_structure_and_results(event_id, category_code)

            has_structure = len(heat_structure) > 0
            has_results = len(heat_results) > 0
            has_scores = False

            if has_structure:
                self.heat_structure_data.extend(heat_structure)
                total_has_structure = True
                total_heat_count += len(heat_structure)
                self.stats['total_heats'] += len(heat_structure)

            if has_results:
                total_has_results = True
                self.stats['total_heat_results'] += len(heat_results)

            # Fetch heat scores if we have heat IDs
            if heat_ids:
                self.log(f"Fetching scores for {len(heat_ids)} heats...")
                heat_scores = self.fetch_heat_scores(event_id, category_code, heat_ids)

                if heat_scores:
                    has_scores = True
                    total_has_scores = True
                    self.heat_scores_data.extend(heat_scores)
                    self.stats['total_heat_scores'] += len(heat_scores)

                    # Merge total_points into heat_results
                    scores_df = pd.DataFrame(heat_scores)
                    if not scores_df.empty and 'total_points' in scores_df.columns:
                        total_points_df = scores_df[['event_id', 'heat_id', 'athlete_id', 'total_points']].drop_duplicates()

                        # Update heat_results with total_points
                        for hr in heat_results:
                            matching = total_points_df[
                                (total_points_df['event_id'] == hr['event_id']) &
                                (total_points_df['heat_id'] == hr['heat_id']) &
                                (total_points_df['athlete_id'] == hr['athlete_id'])
                            ]
                            if not matching.empty:
                                hr['result_total'] = matching.iloc[0]['total_points']

                # Add updated heat_results to main list
                if heat_results:
                    self.heat_results_data.extend(heat_results)

            time.sleep(1)  # Be nice to the server between categories

        # Update stats
        self.stats['total_events'] += 1
        if total_has_structure:
            self.stats['events_with_heat_structure'] += 1
        if total_has_results:
            self.stats['events_with_heat_results'] += 1
        if total_has_scores:
            self.stats['events_with_heat_scores'] += 1

        return {
            'has_heat_structure': total_has_structure,
            'has_heat_results': total_has_results,
            'has_heat_scores': total_has_scores,
            'heat_count': total_heat_count,
            'category_count': len(category_codes)
        }

    def scrape_all_events(self):
        """Scrape heat data for all events"""
        # Load divisions to scrape (with event_ids filtering applied)
        divisions_df = self.load_divisions_to_scrape()

        if divisions_df.empty:
            self.log("No divisions to scrape (all events filtered out or no heat data available)", "INFO")
            return

        # Get unique events from filtered divisions
        events_df = divisions_df[['event_id', 'event_name', 'year']].drop_duplicates()

        if events_df.empty:
            self.log("No events to scrape!", "WARNING")
            return

        total_events = len(events_df)
        self.log(f"\n{'='*80}")
        self.log(f"Starting scrape of {total_events} events")
        self.log(f"{'='*80}\n")

        # Track heat data availability per event
        heat_data_tracking = []

        for idx, (_, event_row) in enumerate(events_df.iterrows(), 1):
            self.log(f"\n--- Event {idx}/{total_events} ---")

            try:
                event_id = str(event_row['event_id'])
                event_name = event_row['event_name']
                year = event_row['year']

                heat_flags = self.scrape_event_heat_data(event_id, event_name, year)

                # Store tracking info
                heat_data_tracking.append({
                    'event_id': event_id,
                    'event_name': event_name,
                    'year': year,
                    'has_heat_structure': heat_flags['has_heat_structure'],
                    'has_heat_results': heat_flags['has_heat_results'],
                    'has_heat_scores': heat_flags['has_heat_scores'],
                    'heat_count': heat_flags['heat_count'],
                    'category_count': heat_flags['category_count']
                })

                time.sleep(2)  # Be nice to the server between events

            except Exception as e:
                self.log(f"FATAL ERROR processing event {event_row['event_id']}: {e}", "ERROR")
                self.stats['errors'] += 1
                continue

        self.print_summary()

        return pd.DataFrame(heat_data_tracking)

    def print_summary(self):
        """Print scraping statistics"""
        self.log(f"\n{'='*80}")
        self.log("SCRAPING COMPLETE - SUMMARY STATISTICS")
        self.log(f"{'='*80}")
        self.log(f"Total Events Processed: {self.stats['total_events']}")
        self.log(f"Events WITH Heat Structure: {self.stats['events_with_heat_structure']}")
        self.log(f"Events WITH Heat Results: {self.stats['events_with_heat_results']}")
        self.log(f"Events WITH Heat Scores: {self.stats['events_with_heat_scores']}")
        self.log(f"Total Heat Structure Entries: {self.stats['total_heats']}")
        self.log(f"Total Heat Results Entries: {self.stats['total_heat_results']}")
        self.log(f"Total Heat Scores Entries: {self.stats['total_heat_scores']}")
        self.log(f"Errors Encountered: {self.stats['errors']}")
        self.log(f"{'='*80}\n")

    def save_results(self, structure_path, results_path, scores_path):
        """
        Save heat data to CSV files

        Args:
            structure_path: Path for heat structure CSV
            results_path: Path for heat results CSV
            scores_path: Path for heat scores CSV
        """
        # Save heat structure
        if self.heat_structure_data:
            structure_df = pd.DataFrame(self.heat_structure_data)
            structure_df.to_csv(structure_path, index=False, encoding='utf-8-sig')
            self.log(f"Heat structure saved to: {structure_path}")
            self.log(f"Total rows: {len(structure_df)}")
        else:
            self.log("WARNING: No heat structure data to save!", "WARNING")

        # Save heat results
        if self.heat_results_data:
            results_df = pd.DataFrame(self.heat_results_data)
            results_df.to_csv(results_path, index=False, encoding='utf-8-sig')
            self.log(f"Heat results saved to: {results_path}")
            self.log(f"Total rows: {len(results_df)}")
        else:
            self.log("WARNING: No heat results data to save!", "WARNING")

        # Save heat scores
        if self.heat_scores_data:
            scores_df = pd.DataFrame(self.heat_scores_data)
            scores_df.to_csv(scores_path, index=False, encoding='utf-8-sig')
            self.log(f"Heat scores saved to: {scores_path}")
            self.log(f"Total rows: {len(scores_df)}")
        else:
            self.log("WARNING: No heat scores data to save!", "WARNING")

    def update_tracking_csv(self, heat_tracking_df):
        """
        Update the division tracking CSV with heat data flags

        Args:
            heat_tracking_df: DataFrame with heat data tracking info
        """
        # Load original tracking CSV
        tracking_df = pd.read_csv(self.tracking_csv_path)

        # Merge heat tracking data
        tracking_df = tracking_df.merge(
            heat_tracking_df[['division_code', 'event_id', 'has_heat_structure', 'has_heat_results', 'has_heat_scores', 'heat_count']],
            on=['division_code', 'event_id'],
            how='left'
        )

        # Fill NaN values for divisions that weren't scraped
        tracking_df['has_heat_structure'] = tracking_df['has_heat_structure'].fillna(False).astype(bool)
        tracking_df['has_heat_results'] = tracking_df['has_heat_results'].fillna(False).astype(bool)
        tracking_df['has_heat_scores'] = tracking_df['has_heat_scores'].fillna(False).astype(bool)
        tracking_df['heat_count'] = tracking_df['heat_count'].fillna(0).astype(int)

        # Save updated tracking CSV
        tracking_df.to_csv(self.tracking_csv_path, index=False, encoding='utf-8-sig')
        self.log(f"\nUpdated tracking CSV: {self.tracking_csv_path}")


def main():
    """Main execution function"""
    # Input: PWA division tracking CSV
    tracking_csv = "data/raw/pwa/pwa_division_results_tracking.csv"

    # Outputs
    structure_csv = "data/raw/pwa/pwa_heat_structure.csv"
    results_csv = "data/raw/pwa/pwa_heat_results.csv"
    scores_csv = "data/raw/pwa/pwa_heat_scores.csv"

    # Initialize scraper
    scraper = PWAHeatScraper(tracking_csv)

    try:
        # Scrape all events
        heat_tracking_df = scraper.scrape_all_events()

        # Save heat data to CSV
        scraper.save_results(structure_csv, results_csv, scores_csv)

        # Save event tracking data
        if heat_tracking_df is not None and not heat_tracking_df.empty:
            event_tracking_path = "data/raw/pwa/pwa_event_heat_tracking.csv"
            heat_tracking_df.to_csv(event_tracking_path, index=False, encoding='utf-8-sig')
            scraper.log(f"\nEvent heat tracking saved to: {event_tracking_path}")

    except Exception as e:
        scraper.log(f"FATAL ERROR in main: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
