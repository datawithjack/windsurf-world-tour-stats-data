"""
Incremental PWA Scraper

Scrapes only the events identified by check_for_updates.py, rather than
performing a full re-scrape of all PWA events.

Usage:
    python src/updates/incremental_scraper.py --events-json data/staging/events_to_update.json --output-dir data/staging
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict
import pandas as pd

# Add parent directory to path to import scrapers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.pwa_event_scraper import PWAEventScraper
from scrapers.pwa_results_scraper import PWAResultsScraper
from scrapers.pwa_heat_scraper import PWAHeatScraper


class IncrementalScraper:
    """Scrape only specified events incrementally"""

    def __init__(self, events_to_update: List[Dict], output_dir: str):
        """
        Initialize incremental scraper

        Args:
            events_to_update: List of events needing updates (from check_for_updates.py)
            output_dir: Directory to save scraped data
        """
        self.events_to_update = events_to_update
        self.event_ids = [e['event_id'] for e in events_to_update]
        self.output_dir = output_dir
        self.errors = []

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def scrape_events(self) -> pd.DataFrame:
        """
        Scrape event metadata for specified events

        Returns:
            DataFrame with event data or empty DataFrame on error
        """
        self.log(f"Scraping event metadata for {len(self.event_ids)} events...")

        scraper = None
        try:
            # Only scrape current year and previous year for efficiency
            current_year = datetime.now().year
            start_year = current_year - 1

            # Initialize scraper with event_ids filter
            scraper = PWAEventScraper(
                start_year=start_year,
                headless=True,
                event_ids=self.event_ids
            )

            # Scrape filtered years (but only matching events will be extracted)
            scraper.scrape_all_years()

            # Convert to DataFrame
            events_df = pd.DataFrame(scraper.events_data)

            self.log(f"Successfully scraped {len(events_df)} events")

            # Save to staging
            output_path = os.path.join(self.output_dir, 'events_incremental.csv')
            if not events_df.empty:
                events_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                self.log(f"Saved events to: {output_path}")

            return events_df

        except Exception as e:
            self.log(f"ERROR scraping events: {e}", "ERROR")
            self.errors.append({
                'stage': 'events',
                'error': str(e)
            })
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

        finally:
            if scraper:
                scraper.close()

    def scrape_results(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Scrape results for specified events

        Args:
            events_df: DataFrame of events to scrape results for

        Returns:
            DataFrame with results data or empty DataFrame on error
        """
        if events_df.empty:
            self.log("No events to scrape results for", "WARNING")
            return pd.DataFrame()

        self.log(f"Scraping results for {len(events_df)} events...")

        try:
            # Initialize results scraper with events DataFrame
            scraper = PWAResultsScraper(events_df=events_df)

            # Load events (will use our filtered DataFrame)
            # NOTE: Not filtering by wave discipline - get ALL events
            # because 2026 events may not have discipline icons yet
            events_to_scrape = scraper.load_wave_events(wave_only=False)

            if events_to_scrape.empty:
                self.log("No events found", "WARNING")
                return pd.DataFrame()

            # Scrape results for all events
            scraper.scrape_all_events()

            # Convert to DataFrame
            results_df = pd.DataFrame(scraper.results_data)

            self.log(f"Successfully scraped {len(results_df)} results")

            # Save to staging
            output_path = os.path.join(self.output_dir, 'results_incremental.csv')
            if not results_df.empty:
                results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                self.log(f"Saved results to: {output_path}")

            return results_df

        except Exception as e:
            self.log(f"ERROR scraping results: {e}", "ERROR")
            self.errors.append({
                'stage': 'results',
                'error': str(e)
            })
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def scrape_heat_data(self) -> Dict[str, pd.DataFrame]:
        """
        Scrape heat data (structure, results, scores) for specified events

        Returns:
            Dict with 'structure', 'results', 'scores' DataFrames
        """
        self.log(f"Scraping heat data for {len(self.event_ids)} events...")

        try:
            # Need to use tracking CSV but filter by event IDs
            tracking_csv_path = 'data/raw/pwa/pwa_division_results_tracking.csv'

            if not os.path.exists(tracking_csv_path):
                self.log(f"WARNING: Tracking CSV not found: {tracking_csv_path}", "WARNING")
                self.log("Skipping heat data scraping", "WARNING")
                return {'structure': pd.DataFrame(), 'results': pd.DataFrame(), 'scores': pd.DataFrame()}

            # Initialize heat scraper with event_ids filter
            scraper = PWAHeatScraper(
                tracking_csv_path=tracking_csv_path,
                event_ids=self.event_ids
            )

            # Scrape all events (will only process filtered event IDs)
            scraper.scrape_all_events()

            # Convert to DataFrames
            structure_df = pd.DataFrame(scraper.heat_structure_data)
            results_df = pd.DataFrame(scraper.heat_results_data)
            scores_df = pd.DataFrame(scraper.heat_scores_data)

            self.log(f"Successfully scraped heat data:")
            self.log(f"  - Heat structures: {len(structure_df)}")
            self.log(f"  - Heat results: {len(results_df)}")
            self.log(f"  - Heat scores: {len(scores_df)}")

            # Save to staging
            if not structure_df.empty:
                output_path = os.path.join(self.output_dir, 'heat_progression_incremental.csv')
                structure_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                self.log(f"Saved heat progression to: {output_path}")

            if not results_df.empty:
                output_path = os.path.join(self.output_dir, 'heat_results_incremental.csv')
                results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                self.log(f"Saved heat results to: {output_path}")

            if not scores_df.empty:
                output_path = os.path.join(self.output_dir, 'heat_scores_incremental.csv')
                scores_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                self.log(f"Saved heat scores to: {output_path}")

            return {
                'structure': structure_df,
                'results': results_df,
                'scores': scores_df
            }

        except Exception as e:
            self.log(f"ERROR scraping heat data: {e}", "ERROR")
            self.errors.append({
                'stage': 'heat_data',
                'error': str(e)
            })
            import traceback
            traceback.print_exc()
            return {'structure': pd.DataFrame(), 'results': pd.DataFrame(), 'scores': pd.DataFrame()}

    def save_errors(self):
        """Save scraping errors to JSON file"""
        if self.errors:
            error_file = os.path.join(self.output_dir, 'scraping_errors.json')
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_errors': len(self.errors),
                    'errors': self.errors
                }, f, indent=2)
            self.log(f"Saved {len(self.errors)} errors to: {error_file}", "WARNING")

    def run(self):
        """
        Run the incremental scraping process

        Returns:
            bool: True if scraping completed (even with some errors), False if critical failure
        """
        if not self.events_to_update:
            self.log("No events to scrape - update list is empty")
            return True

        self.log("=" * 60)
        self.log("INCREMENTAL SCRAPING STARTED")
        self.log("=" * 60)
        self.log(f"Events to scrape: {len(self.events_to_update)}")
        self.log(f"Event IDs: {self.event_ids}")
        self.log("")

        try:
            # Step 1: Scrape event metadata
            self.log("STEP 1: Scraping event metadata...")
            events_df = self.scrape_events()
            time.sleep(2)  # Be nice to the server

            # Step 2: Scrape results
            self.log("\nSTEP 2: Scraping results...")
            results_df = self.scrape_results(events_df)
            time.sleep(2)

            # Step 3: Scrape heat data
            self.log("\nSTEP 3: Scraping heat data...")
            heat_data = self.scrape_heat_data()

            # Save any errors
            if self.errors:
                self.save_errors()

            # Print summary
            print("\n" + "=" * 60)
            print("INCREMENTAL SCRAPING SUMMARY")
            print("=" * 60)
            print(f"Events scraped: {len(events_df)}")
            print(f"Results scraped: {len(results_df)}")
            print(f"Heat structures scraped: {len(heat_data['structure'])}")
            print(f"Heat results scraped: {len(heat_data['results'])}")
            print(f"Heat scores scraped: {len(heat_data['scores'])}")
            print(f"Errors encountered: {len(self.errors)}")
            print("=" * 60)

            return True

        except Exception as e:
            self.log(f"CRITICAL ERROR during scraping: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Incrementally scrape only specified PWA events'
    )
    parser.add_argument(
        '--events-json',
        type=str,
        required=True,
        help='JSON file with events to update (from check_for_updates.py)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/staging',
        help='Output directory for scraped data (default: data/staging)'
    )

    args = parser.parse_args()

    # Load events to update
    if not os.path.exists(args.events_json):
        print(f"ERROR: Events JSON file not found: {args.events_json}")
        sys.exit(1)

    with open(args.events_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        events_to_update = data.get('events', [])

    if not events_to_update:
        print("No events to update - scraping skipped")
        sys.exit(0)

    # Run incremental scraper
    scraper = IncrementalScraper(events_to_update, args.output_dir)
    success = scraper.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
