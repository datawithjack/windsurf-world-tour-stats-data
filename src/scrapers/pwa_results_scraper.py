"""
PWA Wave Event Results Scraper
Extracts final results for wave divisions from PWA events
Input: pwa_events_raw.csv (wave events only)
Output: pwa_wave_results_raw.csv
"""

import time
import re
from datetime import datetime
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings (PWA site has SSL issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PWAResultsScraper:
    """Scraper for PWA wave event final results"""

    def __init__(self, events_csv_path=None, events_df=None):
        """
        Initialize the scraper

        Args:
            events_csv_path: Path to PWA events CSV file (optional if events_df provided)
            events_df: DataFrame with PWA events (optional if events_csv_path provided)
        """
        if events_csv_path is None and events_df is None:
            raise ValueError("Either events_csv_path or events_df must be provided")

        self.events_csv_path = events_csv_path
        self.events_df = events_df
        self.results_data = []
        self.division_data = []
        self.scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create session with retry logic
        self.session = self._create_session()

        # Statistics
        self.stats = {
            'total_events': 0,
            'events_with_results': 0,
            'events_without_results': 0,
            'total_divisions': 0,
            'total_athletes': 0,
            'errors': 0
        }

    def _create_session(self):
        """Create requests session with retry logic and SSL handling"""
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

    def load_wave_events(self, wave_only=True):
        """
        Load wave events from CSV or DataFrame

        Args:
            wave_only: If True, filter for wave events only. If False, return all events.

        Returns:
            DataFrame of events
        """
        if self.events_df is not None:
            self.log("Using provided events DataFrame...")
            df = self.events_df
        else:
            self.log("Loading PWA events from CSV...")
            df = pd.read_csv(self.events_csv_path)

        # Filter for wave events only if requested
        if wave_only:
            events = df[df['has_wave_discipline'] == True].copy()
            self.log(f"Loaded {len(events)} wave events from {len(df)} total events")
        else:
            events = df.copy()
            self.log(f"Loaded {len(events)} events (all disciplines)")

        return events

    def extract_wave_division_links(self, event_id):
        """
        Extract wave division links and codes from event results page

        Args:
            event_id: PWA event ID

        Returns:
            Dict with division labels as keys and division codes as values
            Example: {'Wave Men': '960', 'Wave Women': '961'}
        """
        url = f"https://www.pwaworldtour.com/index.php?id=193&type=21&tx_pwaevent_pi1%5Baction%5D=results&tx_pwaevent_pi1%5BshowUid%5D={event_id}"

        try:
            response = self.session.get(url, timeout=30, verify=False)
            if response.status_code != 200:
                self.log(f"Failed to fetch results page for event {event_id}: HTTP {response.status_code}", "ERROR")
                return {}

            soup = BeautifulSoup(response.content, 'lxml')

            # Find all links in the page
            container = soup.find('ul')
            links = container.find_all('a', href=True) if container else soup.find_all('a', href=True)

            # Regex pattern to extract discipline code
            pattern = r"tx_pwaevent_pi1%5BeventDiscipline%5D=(\d+)"

            wave_divisions = {}
            for link in links:
                label = link.get_text(strip=True)
                href = link.get('href')

                # Check if the label contains "wave" (case-insensitive)
                if "wave" in label.lower():
                    match = re.search(pattern, href)
                    if match:
                        division_code = match.group(1)
                        wave_divisions[label] = division_code
                        self.log(f"  Found wave division: {label} (code: {division_code})")

            return wave_divisions

        except Exception as e:
            self.log(f"Error extracting division links for event {event_id}: {e}", "ERROR")
            self.stats['errors'] += 1
            return {}

    def extract_division_results(self, event_id, division_label, division_code, event_info):
        """
        Extract results table for a specific wave division

        Args:
            event_id: PWA event ID
            division_label: Division name (e.g., "Wave Men")
            division_code: Division code for URL
            event_info: Dict with event metadata (year, event_name, etc.)

        Returns:
            List of result dictionaries
        """
        url = f"https://www.pwaworldtour.com/index.php?id=193&type=21&tx_pwaevent_pi1%5Baction%5D=results&tx_pwaevent_pi1%5BshowUid%5D={event_id}&tx_pwaevent_pi1%5BeventDiscipline%5D={division_code}"

        try:
            response = self.session.get(url, timeout=30, verify=False)
            if response.status_code != 200:
                self.log(f"Failed to fetch division results: HTTP {response.status_code}", "WARNING")
                return []

            soup = BeautifulSoup(response.content, 'lxml')

            # Find the results table
            table = soup.find('table')
            if table is None:
                self.log(f"  No results table found for {division_label}", "WARNING")
                return []

            # Parse table rows (skip header)
            rows = table.find_all('tr')
            results = []

            for row in rows[1:]:  # Skip header row
                cols = row.find_all('td')
                if len(cols) < 6:
                    continue  # Skip rows without enough columns

                # Extract data from columns
                try:
                    place = cols[0].get_text(strip=True)

                    # Name might be in a div with class 'rank-name', which contains an <a> tag
                    name_div = cols[1].find('div', class_='rank-name')
                    name = name_div.get_text(strip=True) if name_div else cols[1].get_text(strip=True)

                    # Extract PWA athlete ID from href (if available)
                    pwa_athlete_id = ''
                    if name_div:
                        athlete_link = name_div.find('a', href=True)
                        if athlete_link:
                            href = athlete_link.get('href', '')
                            # Pattern: tx_pwasailor_pi1%5BshowUid%5D=791 or showUid=791
                            match = re.search(r'(?:tx_pwasailor_pi1%5BshowUid%5D|showUid)=(\d+)', href)
                            if match:
                                pwa_athlete_id = match.group(1)

                    sail_no = cols[2].get_text(strip=True)

                    # Determine sex from division label
                    sex = "Women" if "women" in division_label.lower() else "Men"

                    result = {
                        'source': 'PWA',
                        'scraped_at': self.scraped_at,
                        'event_id': event_id,
                        'year': event_info.get('year', ''),
                        'event_name': event_info.get('event_name', ''),
                        'division_label': division_label,
                        'division_code': division_code,
                        'sex': sex,
                        'place': place,
                        'athlete_name': name,
                        'sail_number': sail_no,
                        'athlete_id': pwa_athlete_id
                    }

                    results.append(result)
                    self.stats['total_athletes'] += 1

                except Exception as e:
                    self.log(f"  Error parsing row: {e}", "WARNING")
                    continue

            self.log(f"  Extracted {len(results)} results for {division_label}")
            return results

        except Exception as e:
            self.log(f"Error extracting results for division {division_label}: {e}", "ERROR")
            self.stats['errors'] += 1
            return []

    def scrape_event_results(self, event_row):
        """
        Scrape all wave division results for a single event

        Args:
            event_row: Pandas Series with event data

        Returns:
            Number of divisions processed
        """
        event_id = str(event_row['event_id'])
        event_name = event_row['event_name']
        year = event_row['year']

        self.log(f"\n{'='*80}")
        self.log(f"Processing Event {event_id}: {event_name} ({year})")
        self.log(f"{'='*80}")

        self.stats['total_events'] += 1

        # Extract wave division links
        wave_divisions = self.extract_wave_division_links(event_id)

        if not wave_divisions:
            self.log(f"No wave divisions found or no results available for event {event_id}", "WARNING")
            self.stats['events_without_results'] += 1

            # Store division info even if no results
            self.division_data.append({
                'source': 'PWA',
                'event_id': event_id,
                'year': year,
                'event_name': event_name,
                'has_results': False,
                'division_count': 0,
                'division_labels': '',
                'division_codes': ''
            })
            return 0

        # Store division info
        self.division_data.append({
            'source': 'PWA',
            'event_id': event_id,
            'year': year,
            'event_name': event_name,
            'has_results': True,
            'division_count': len(wave_divisions),
            'division_labels': ', '.join(wave_divisions.keys()),
            'division_codes': ', '.join(wave_divisions.values())
        })

        self.stats['events_with_results'] += 1
        self.stats['total_divisions'] += len(wave_divisions)

        # Event metadata for results
        event_info = {
            'year': year,
            'event_name': event_name
        }

        # Extract results for each wave division
        divisions_processed = 0
        for division_label, division_code in wave_divisions.items():
            self.log(f"\nScraping division: {division_label}")
            results = self.extract_division_results(
                event_id, division_label, division_code, event_info
            )

            if results:
                self.results_data.extend(results)
                divisions_processed += 1

            time.sleep(1)  # Be nice to the server

        return divisions_processed

    def scrape_all_events(self):
        """Scrape results for all wave events"""
        wave_events = self.load_wave_events()

        if wave_events.empty:
            self.log("No wave events found to scrape!", "ERROR")
            return

        total_events = len(wave_events)
        self.log(f"\n{'='*80}")
        self.log(f"Starting scrape of {total_events} wave events")
        self.log(f"{'='*80}\n")

        for idx, (_, event_row) in enumerate(wave_events.iterrows(), 1):
            self.log(f"\n--- Event {idx}/{total_events} ---")

            try:
                self.scrape_event_results(event_row)
                time.sleep(2)  # Be nice to the server between events

            except Exception as e:
                self.log(f"FATAL ERROR processing event {event_row['event_id']}: {e}", "ERROR")
                self.stats['errors'] += 1
                continue

        self.print_summary()

    def print_summary(self):
        """Print scraping statistics"""
        self.log(f"\n{'='*80}")
        self.log("SCRAPING COMPLETE - SUMMARY STATISTICS")
        self.log(f"{'='*80}")
        self.log(f"Total Events Processed: {self.stats['total_events']}")
        self.log(f"Events WITH Results: {self.stats['events_with_results']}")
        self.log(f"Events WITHOUT Results: {self.stats['events_without_results']}")
        self.log(f"Total Wave Divisions: {self.stats['total_divisions']}")
        self.log(f"Total Athletes Extracted: {self.stats['total_athletes']}")
        self.log(f"Errors Encountered: {self.stats['errors']}")
        self.log(f"{'='*80}\n")

    def save_results(self, results_output_path, divisions_output_path):
        """
        Save results to CSV files

        Args:
            results_output_path: Path for results CSV
            divisions_output_path: Path for divisions CSV
        """
        # Save results
        if self.results_data:
            results_df = pd.DataFrame(self.results_data)
            results_df.to_csv(results_output_path, index=False, encoding='utf-8-sig')
            self.log(f"Results saved to: {results_output_path}")
            self.log(f"Total rows: {len(results_df)}")
        else:
            self.log("WARNING: No results data to save!", "WARNING")

        # Save division info
        if self.division_data:
            divisions_df = pd.DataFrame(self.division_data)
            divisions_df.to_csv(divisions_output_path, index=False, encoding='utf-8-sig')
            self.log(f"Division info saved to: {divisions_output_path}")
            self.log(f"Total rows: {len(divisions_df)}")
        else:
            self.log("WARNING: No division data to save!", "WARNING")


def main():
    """Main execution function"""
    # Input: PWA events CSV
    events_csv = "data/raw/pwa/pwa_events_raw.csv"

    # Outputs
    results_csv = "data/raw/pwa/pwa_wave_results_updated.csv"
    divisions_csv = "data/raw/pwa/pwa_wave_divisions_raw.csv"

    # Initialize scraper
    scraper = PWAResultsScraper(events_csv)

    try:
        # Scrape all wave event results
        scraper.scrape_all_events()

        # Save to CSV
        scraper.save_results(results_csv, divisions_csv)

    except Exception as e:
        scraper.log(f"FATAL ERROR in main: {e}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
