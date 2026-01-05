"""
Check for Updates Script

Identifies which PWA events need updating by comparing database records
with current PWA website data.

Usage:
    python src/updates/check_for_updates.py --lookback-days 60 --output data/staging/events_to_update.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

# Add parent directory to path to import scrapers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.pwa_event_scraper import PWAEventScraper


class UpdateChecker:
    """Check for events that need updating"""

    def __init__(self, lookback_days=60):
        """
        Initialize update checker

        Args:
            lookback_days: How many days back to check for updates (default: 60)
        """
        self.lookback_days = lookback_days
        self.cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        self.db_conn = None

    def log(self, message):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def connect_to_database(self):
        """Connect to MySQL database using environment variables"""
        load_dotenv()

        self.log("Connecting to database...")

        try:
            self.db_conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '3306')),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                connect_timeout=30
            )
            self.log(f"Connected to database: {os.getenv('DB_NAME')}")
            return True

        except mysql.connector.Error as e:
            self.log(f"ERROR: Database connection failed: {e}")
            return False

    def get_recent_events_from_db(self) -> pd.DataFrame:
        """
        Query database for events from last N days
        NOTE: Gets ALL events (not just wave) because 2026 events may not have discipline icons yet

        Returns:
            DataFrame with database events
        """
        self.log(f"Querying database for events since {self.cutoff_date}...")

        query = """
            SELECT
                event_id,
                event_name,
                year,
                event_status,
                competition_state,
                start_date,
                end_date,
                has_wave_discipline,
                scraped_at
            FROM PWA_IWT_EVENTS
            WHERE source = 'PWA'
                AND (
                    end_date >= %s
                    OR event_status IN (0, 1, 2)
                )
            ORDER BY year DESC, start_date DESC
        """

        cursor = self.db_conn.cursor(dictionary=True)
        cursor.execute(query, (self.cutoff_date,))
        results = cursor.fetchall()
        cursor.close()

        df = pd.DataFrame(results)
        self.log(f"Found {len(df)} events in database (all disciplines)")

        return df

    def scrape_recent_events_from_pwa(self) -> pd.DataFrame:
        """
        Scrape PWA website for current events data

        Returns:
            DataFrame with current PWA event data
        """
        self.log("Scraping PWA website for current events...")

        # Only scrape current year and previous year for efficiency
        current_year = datetime.now().year
        start_year = current_year - 1

        # Use PWAEventScraper to get recent events only
        scraper = PWAEventScraper(start_year=start_year, headless=True)

        try:
            scraper.scrape_all_years()
            pwa_events = pd.DataFrame(scraper.events_data)

            # Check if scraper got any events
            if pwa_events.empty:
                self.log("WARNING: PWA scraper returned no events", "WARNING")
                return pd.DataFrame()

            # Convert event_id to int
            pwa_events['event_id'] = pd.to_numeric(pwa_events['event_id'], errors='coerce')

            # Filter for recent events (last N days or in-progress/upcoming)
            # Note: event_status is stored as STRING ('0', '1', '2', '3') not int
            # Status codes: 0=TBC/Draft, 1=Upcoming, 2=In Progress, 3=Completed
            # NOTE: Not filtering by has_wave_discipline because 2026 events
            # don't have discipline icons added yet
            recent_pwa = pwa_events[
                (pwa_events['end_date'] >= self.cutoff_date) |
                (pwa_events['event_status'].isin(['0', '1', '2']))  # Include TBC (0), Upcoming (1), In Progress (2)
            ].copy()

            self.log(f"Found {len(recent_pwa)} recent events on PWA website (all disciplines)")

            return recent_pwa

        finally:
            scraper.close()

    def compare_events(self, db_events: pd.DataFrame, pwa_events: pd.DataFrame) -> List[Dict]:
        """
        Compare database events with PWA events and identify changes

        Args:
            db_events: Events from database
            pwa_events: Events from PWA website

        Returns:
            List of events that need updating with reasons
        """
        self.log("Comparing database events with PWA events...")

        events_to_update = []

        # Check for new events (in PWA but not in database)
        pwa_event_ids = set(pwa_events['event_id'].dropna().astype(int))
        db_event_ids = set(db_events['event_id'].dropna().astype(int)) if not db_events.empty else set()

        new_event_ids = pwa_event_ids - db_event_ids

        for event_id in new_event_ids:
            event_row = pwa_events[pwa_events['event_id'] == event_id].iloc[0]
            events_to_update.append({
                'event_id': int(event_id),
                'event_name': event_row['event_name'],
                'year': int(event_row['year']),
                'reason': 'new_event',
                'old_status': None,
                'new_status': int(event_row['event_status']),
                'has_wave_discipline': True
            })

        self.log(f"Found {len(new_event_ids)} new events")

        # Check for updated events (status or competition_state changes)
        for event_id in db_event_ids & pwa_event_ids:
            db_row = db_events[db_events['event_id'] == event_id].iloc[0]
            pwa_row = pwa_events[pwa_events['event_id'] == event_id].iloc[0]

            # Check for status change
            db_status = int(db_row['event_status']) if pd.notna(db_row['event_status']) else None
            pwa_status = int(pwa_row['event_status']) if pd.notna(pwa_row['event_status']) else None

            # Check for competition state change
            db_comp_state = int(db_row['competition_state']) if pd.notna(db_row['competition_state']) else None
            pwa_comp_state = int(pwa_row['competition_state']) if pd.notna(pwa_row['competition_state']) else None

            if db_status != pwa_status or db_comp_state != pwa_comp_state:
                reason = []
                if db_status != pwa_status:
                    reason.append('status_change')
                if db_comp_state != pwa_comp_state:
                    reason.append('competition_state_change')

                events_to_update.append({
                    'event_id': int(event_id),
                    'event_name': pwa_row['event_name'],
                    'year': int(pwa_row['year']),
                    'reason': '+'.join(reason),
                    'old_status': db_status,
                    'new_status': pwa_status,
                    'old_competition_state': db_comp_state,
                    'new_competition_state': pwa_comp_state,
                    'has_wave_discipline': True
                })

        self.log(f"Found {len(events_to_update) - len(new_event_ids)} events with status/state changes")
        self.log(f"Total events to update: {len(events_to_update)}")

        return events_to_update

    def save_update_list(self, events_to_update: List[Dict], output_path: str):
        """
        Save list of events to update as JSON

        Args:
            events_to_update: List of events needing updates
            output_path: Path to output JSON file
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        output_data = {
            'timestamp': datetime.now().isoformat(),
            'lookback_days': self.lookback_days,
            'cutoff_date': self.cutoff_date,
            'total_events': len(events_to_update),
            'events': events_to_update
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.log(f"Saved update list to: {output_path}")

        # Print summary
        print("\n" + "="*60)
        print("UPDATE SUMMARY")
        print("="*60)
        print(f"Total events to update: {len(events_to_update)}")

        if events_to_update:
            # Count by reason
            reason_counts = {}
            for event in events_to_update:
                reason = event['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            print("\nBreakdown by reason:")
            for reason, count in sorted(reason_counts.items()):
                print(f"  {reason}: {count}")

            print("\nEvents to update:")
            for event in events_to_update[:10]:  # Show first 10
                print(f"  [{event['year']}] {event['event_name']} (ID: {event['event_id']}) - {event['reason']}")

            if len(events_to_update) > 10:
                print(f"  ... and {len(events_to_update) - 10} more")
        else:
            print("\nNo events need updating - database is up to date!")

        print("="*60)

    def run(self, output_path: str):
        """
        Run the update checker

        Args:
            output_path: Path to save output JSON
        """
        try:
            # Connect to database
            if not self.connect_to_database():
                return False

            # Get events from database
            db_events = self.get_recent_events_from_db()

            # Scrape current PWA events
            pwa_events = self.scrape_recent_events_from_pwa()

            # Compare and identify changes
            events_to_update = self.compare_events(db_events, pwa_events)

            # Save results
            self.save_update_list(events_to_update, output_path)

            return True

        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.db_conn:
                self.db_conn.close()
                self.log("Database connection closed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check for PWA events that need updating'
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=60,
        help='How many days back to check for updates (default: 60)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/staging/events_to_update.json',
        help='Output JSON file path (default: data/staging/events_to_update.json)'
    )

    args = parser.parse_args()

    checker = UpdateChecker(lookback_days=args.lookback_days)
    success = checker.run(args.output)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
