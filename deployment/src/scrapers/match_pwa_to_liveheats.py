"""
Match PWA Events to Live Heats
Creates matching report for 2023+ PWA events without results
Checks if events exist in Live Heats database
"""

import json
import re
from datetime import datetime, timedelta
import pandas as pd
import requests


# Location keyword mapping for matching
LOCATION_MAP = {
    'chile': ['chile', 'topocalma', 'pichilemu'],
    'sylt': ['sylt', 'westerland', 'germany'],
    'maui': ['maui', 'aloha', 'hookipa', 'kanaha', 'hawaii'],
    'gran_canaria': ['gran canaria', 'pozo', 'canary'],
    'tenerife': ['tenerife', 'el medano'],
    'denmark': ['denmark', 'klitmoller', 'cold hawaii'],
    'peru': ['peru', 'pacasmayo'],
    'japan': ['japan', 'omaezaki', 'yokosuka'],
    'puerto_rico': ['puerto rico', 'la pared'],
    'fiji': ['fiji', 'cloudbreak']
}


class PWALiveHeatsMatcher:
    """Match PWA events to Live Heats events"""

    def __init__(self):
        self.graphql_url = "https://liveheats.com/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        self.liveheats_events = []
        self.match_results = []

    def log(self, message, level="INFO"):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_pwa_events_to_check(self):
        """
        Load PWA events that need checking in Live Heats

        Returns:
            DataFrame of PWA events without results (excluding youth)
        """
        self.log("Loading PWA division tracking data...")
        tracking_df = pd.read_csv('data/raw/pwa/pwa_division_results_tracking.csv')

        # Filter: 2023+, no results, exclude youth events
        missing = tracking_df[
            (tracking_df['year'] >= 2023) &
            (tracking_df['has_results'] == False) &
            (~tracking_df['notes'].str.contains('youth', case=False, na=False))
        ].copy()

        # Get unique events (dedupe by event_id)
        pwa_events = missing.drop_duplicates(subset=['event_id']).copy()

        # Load original events data for full details
        events_df = pd.read_csv('data/raw/pwa/pwa_events_raw.csv')
        pwa_events = pwa_events.merge(
            events_df[['event_id', 'start_date', 'end_date', 'stars', 'event_section']],
            on='event_id',
            how='left',
            suffixes=('', '_full')
        )

        self.log(f"Found {len(tracking_df[tracking_df['year'] >= 2023])} total 2023+ divisions without PWA results")
        self.log(f"Excluding {tracking_df[(tracking_df['year'] >= 2023) & (tracking_df['notes'].str.contains('youth', case=False, na=False))].shape[0]} youth event divisions")
        self.log(f"Checking {len(pwa_events)} events ({len(missing)} divisions)")

        return pwa_events, missing

    def fetch_liveheats_events(self):
        """
        Fetch all events from Live Heats "WaveTour" organization

        Returns:
            List of Live Heats events
        """
        self.log("Fetching events from Live Heats...")

        query = """
        query getOrganisationByShortName($shortName: String) {
          organisationByShortName(shortName: $shortName) {
            events {
              id
              name
              status
              date
              daysWindow
            }
          }
        }
        """

        variables = {"shortName": "WaveTour"}
        payload = {"query": query, "variables": variables}

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload)
            response.raise_for_status()

            data = response.json()

            # Save raw response
            with open('data/raw/liveheats/liveheats_all_events.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            events = data["data"]["organisationByShortName"]["events"]

            # Parse and filter events
            lh_events = []
            for event in events:
                # Parse date (handle ISO format with timezone)
                try:
                    date_str = event['date'].split('T')[0]  # Extract just the date part
                    start_date = datetime.strptime(date_str, "%Y-%m-%d")
                    end_date = start_date + timedelta(days=event.get('daysWindow', 0))

                    # Only include 2023+
                    if start_date.year >= 2023:
                        # Extract location and stars from name
                        location = self.extract_location(event['name'])
                        stars = self.extract_stars(event['name'])

                        lh_events.append({
                            'event_id': event['id'],
                            'event_name': event['name'],
                            'status': event['status'],
                            'start_date': start_date,
                            'end_date': end_date,
                            'start_date_str': start_date.strftime('%Y-%m-%d'),
                            'end_date_str': end_date.strftime('%Y-%m-%d'),
                            'location': location,
                            'stars': stars,
                            'year': start_date.year
                        })
                except Exception as e:
                    self.log(f"Error parsing event {event.get('id')}: {e}", "WARNING")
                    continue

            self.liveheats_events = lh_events

            # Save to CSV
            if lh_events:
                lh_df = pd.DataFrame(lh_events)
                lh_df[['event_id', 'event_name', 'status', 'start_date_str', 'end_date_str', 'location', 'stars', 'year']].to_csv(
                    'data/raw/liveheats/liveheats_events_2023plus.csv',
                    index=False,
                    encoding='utf-8-sig'
                )

            self.log(f"Found {len(lh_events)} Live Heats events (2023+)")
            return lh_events

        except Exception as e:
            self.log(f"ERROR fetching Live Heats events: {e}", "ERROR")
            return []

    def extract_location(self, event_name):
        """Extract location from event name"""
        name_lower = event_name.lower()

        for location, keywords in LOCATION_MAP.items():
            if any(keyword in name_lower for keyword in keywords):
                return location

        return None

    def extract_stars(self, event_name):
        """Extract star rating from event name"""
        match = re.search(r'(\d+)\s*star', event_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def dates_overlap(self, pwa_start, pwa_end, lh_start, lh_end, tolerance_days=1):
        """
        Check if two date ranges overlap within tolerance

        Args:
            pwa_start, pwa_end: PWA event dates (strings 'YYYY-MM-DD')
            lh_start, lh_end: Live Heats event dates (datetime objects)
            tolerance_days: Days of tolerance (default 1)

        Returns:
            Boolean indicating overlap
        """
        try:
            # Convert PWA dates to datetime
            if isinstance(pwa_start, str):
                pwa_start = datetime.strptime(pwa_start, '%Y-%m-%d')
            if isinstance(pwa_end, str):
                pwa_end = datetime.strptime(pwa_end, '%Y-%m-%d')

            # Expand ranges by tolerance
            pwa_start_adj = pwa_start - timedelta(days=tolerance_days)
            pwa_end_adj = pwa_end + timedelta(days=tolerance_days)

            # Check for any overlap
            overlap = not (lh_end < pwa_start_adj or lh_start > pwa_end_adj)

            return overlap

        except Exception as e:
            self.log(f"Error checking date overlap: {e}", "WARNING")
            return False

    def calculate_match_score(self, pwa_event, lh_event):
        """
        Calculate match score between PWA and Live Heats event

        Scoring:
        - Date overlap (±1 day): 60 points
        - Location match: 30 points
        - Star rating match: 10 points

        Returns:
            (score, details dict)
        """
        score = 0
        details = {}

        # Date overlap (60 points)
        dates_match = self.dates_overlap(
            pwa_event.get('start_date'),
            pwa_event.get('end_date'),
            lh_event['start_date'],
            lh_event['end_date'],
            tolerance_days=1
        )

        if dates_match:
            score += 60
            details['date_overlap'] = 'Yes'
        else:
            details['date_overlap'] = 'No'

        # Location match (30 points)
        pwa_location = self.extract_location(pwa_event['event_name'])
        lh_location = lh_event.get('location')

        if pwa_location and lh_location and pwa_location == lh_location:
            score += 30
            details['location_match'] = f"{pwa_location}={lh_location}"
        else:
            details['location_match'] = f"{pwa_location}≠{lh_location}"

        # Star rating match (10 points)
        pwa_stars = pwa_event.get('stars')
        lh_stars = lh_event.get('stars')

        if pwa_stars and lh_stars and int(pwa_stars) == int(lh_stars):
            score += 10
            details['stars_match'] = f"{pwa_stars}={lh_stars}"
        elif not pwa_stars or not lh_stars:
            details['stars_match'] = 'N/A'
        else:
            details['stars_match'] = f"{pwa_stars}≠{lh_stars}"

        return score, details

    def check_liveheats_divisions(self, lh_event_id):
        """
        Check divisions and results for a Live Heats event

        Returns:
            List of division dicts with results info
        """
        query = """
        query getEvent($id: ID!) {
          event(id: $id) {
            id
            name
            eventDivisions {
              id
              division { id, name }
              heats {
                id
                result { athleteId }
              }
            }
          }
        }
        """

        variables = {"id": str(lh_event_id)}
        payload = {"query": query, "variables": variables}

        try:
            response = requests.post(self.graphql_url, headers=self.headers, json=payload)
            response.raise_for_status()

            data = response.json()
            event_divs = data['data']['event']['eventDivisions']

            divisions = []
            for ed in event_divs:
                division_name = ed['division']['name']

                # Count results
                result_count = 0
                for heat in ed.get('heats', []):
                    result_count += len(heat.get('result', []))

                divisions.append({
                    'division_id': ed['id'],
                    'division_name': division_name,
                    'has_results': result_count > 0,
                    'result_count': result_count
                })

            return divisions

        except Exception as e:
            self.log(f"Error fetching divisions for event {lh_event_id}: {e}", "WARNING")
            return []

    def match_events(self, pwa_events, pwa_divisions):
        """
        Match PWA events to Live Heats events

        Args:
            pwa_events: DataFrame of PWA events to check
            pwa_divisions: DataFrame of PWA divisions (for reporting)
        """
        self.log("\n" + "="*80)
        self.log("MATCHING PWA EVENTS TO LIVE HEATS")
        self.log("="*80 + "\n")

        match_results = []

        for idx, pwa_event in pwa_events.iterrows():
            pwa_id = pwa_event['event_id']
            pwa_name = pwa_event['event_name']
            pwa_year = pwa_event['year']

            self.log(f"\nChecking Event {pwa_id}: {pwa_name} ({pwa_year})")

            # Find best matching Live Heats event
            best_match = None
            best_score = 0
            best_details = {}

            for lh_event in self.liveheats_events:
                score, details = self.calculate_match_score(pwa_event, lh_event)

                if score > best_score:
                    best_score = score
                    best_match = lh_event
                    best_details = details

            # Check if match meets threshold (80%)
            if best_score >= 80:
                self.log(f"  [OK] MATCHED: Live Heats Event {best_match['event_id']} (Score: {best_score}/100)")
                self.log(f"    - {best_match['event_name']}")
                self.log(f"    - {best_match['start_date_str']} to {best_match['end_date_str']}")

                # Check divisions
                divisions = self.check_liveheats_divisions(best_match['event_id'])

                for div in divisions:
                    self.log(f"    - Division: {div['division_name']} ({div['result_count']} results)")

                # Get PWA divisions for this event
                pwa_event_divs = pwa_divisions[pwa_divisions['event_id'] == pwa_id]

                for _, pwa_div in pwa_event_divs.iterrows():
                    # Find matching Live Heats division by sex
                    # Match: PWA "Men" -> Live Heats division name contains "men" (case insensitive)
                    # Match: PWA "Women" -> Live Heats division name contains "women" (case insensitive)
                    pwa_sex = pwa_div['sex'].lower()

                    lh_div = None
                    for d in divisions:
                        div_name_lower = d['division_name'].lower()
                        # For "Men", ensure it's not "Women" (which also contains "men")
                        if pwa_sex == 'men' and 'men' in div_name_lower and 'women' not in div_name_lower:
                            lh_div = d
                            break
                        elif pwa_sex == 'women' and 'women' in div_name_lower:
                            lh_div = d
                            break

                    match_results.append({
                        'pwa_event_id': pwa_id,
                        'pwa_event_name': pwa_name,
                        'pwa_year': pwa_year,
                        'pwa_start_date': pwa_event.get('start_date'),
                        'pwa_end_date': pwa_event.get('end_date'),
                        'pwa_division_label': pwa_div['division_label'],
                        'pwa_stars': pwa_event.get('stars'),
                        'pwa_status': pwa_event.get('event_section', ''),
                        'matched': True,
                        'liveheats_event_id': best_match['event_id'],
                        'liveheats_event_name': best_match['event_name'],
                        'liveheats_start_date': best_match['start_date_str'],
                        'liveheats_end_date': best_match['end_date_str'],
                        'liveheats_division_id': lh_div['division_id'] if lh_div else '',
                        'liveheats_division_name': lh_div['division_name'] if lh_div else '',
                        'liveheats_has_results': lh_div['has_results'] if lh_div else False,
                        'liveheats_result_count': lh_div['result_count'] if lh_div else 0,
                        'match_score': best_score,
                        'match_details': f"Date: {best_details['date_overlap']}, Location: {best_details['location_match']}, Stars: {best_details['stars_match']}",
                        'notes': 'Strong match' if best_score >= 90 else 'Good match'
                    })

            else:
                self.log(f"  [X] NO MATCH: Best score {best_score}/100 (threshold: 80)")

                # Get PWA divisions for this event
                pwa_event_divs = pwa_divisions[pwa_divisions['event_id'] == pwa_id]

                for _, pwa_div in pwa_event_divs.iterrows():
                    # No matching event, so no division to match
                    match_results.append({
                        'pwa_event_id': pwa_id,
                        'pwa_event_name': pwa_name,
                        'pwa_year': pwa_year,
                        'pwa_start_date': pwa_event.get('start_date'),
                        'pwa_end_date': pwa_event.get('end_date'),
                        'pwa_division_label': pwa_div['division_label'],
                        'pwa_stars': pwa_event.get('stars'),
                        'pwa_status': pwa_event.get('event_section', ''),
                        'matched': False,
                        'liveheats_event_id': '',
                        'liveheats_event_name': '',
                        'liveheats_start_date': '',
                        'liveheats_end_date': '',
                        'liveheats_division_id': '',
                        'liveheats_division_name': '',
                        'liveheats_has_results': False,
                        'liveheats_result_count': 0,
                        'match_score': best_score,
                        'match_details': f"Best: {best_details.get('date_overlap', 'N/A')}",
                        'notes': 'No match found'
                    })

        self.match_results = match_results
        return match_results

    def save_report(self):
        """Save matching report to CSV"""
        if not self.match_results:
            self.log("No results to save", "WARNING")
            return

        df = pd.DataFrame(self.match_results)

        output_path = 'data/reports/pwa_liveheats_matching_report_v2.csv'
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        self.log(f"\nReport saved to: {output_path}")

        return df

    def print_summary(self, report_df):
        """Print summary statistics"""
        self.log("\n" + "="*80)
        self.log("SUMMARY")
        self.log("="*80)

        total_events = report_df['pwa_event_id'].nunique()
        matched_events = report_df[report_df['matched']]['pwa_event_id'].nunique()
        total_divs = len(report_df)
        divs_with_results = report_df['liveheats_has_results'].sum()
        total_athletes = report_df['liveheats_result_count'].sum()

        self.log(f"Total PWA events checked: {total_events}")
        self.log(f"Events matched to Live Heats: {matched_events} ({matched_events/total_events*100:.0f}%)")
        self.log(f"Events NOT matched: {total_events - matched_events}")
        self.log(f"")
        self.log(f"Total divisions: {total_divs}")
        self.log(f"Divisions with Live Heats results: {divs_with_results}")
        self.log(f"Divisions without results (future/no data): {total_divs - divs_with_results}")
        self.log(f"Total athletes found: {int(total_athletes)}")
        self.log(f"")

        if matched_events > 0:
            avg_score = report_df[report_df['matched']]['match_score'].mean()
            self.log(f"Match confidence: Average {avg_score:.0f}%")

        self.log("="*80)

        self.log("\nNext steps:")
        self.log("  1. Review data/reports/pwa_liveheats_matching_report.csv")
        self.log("  2. Verify matches manually if needed")
        self.log("  3. Proceed to scrape matched events from Live Heats")


def main():
    """Main execution"""
    print("="*80)
    print("PWA TO LIVE HEATS EVENT MATCHING REPORT")
    print("="*80)
    print()

    matcher = PWALiveHeatsMatcher()

    # Step 1: Load PWA events to check
    pwa_events, pwa_divisions = matcher.load_pwa_events_to_check()

    if pwa_events.empty:
        matcher.log("No PWA events to check!", "WARNING")
        return

    # Step 2: Fetch Live Heats events
    lh_events = matcher.fetch_liveheats_events()

    if not lh_events:
        matcher.log("No Live Heats events fetched!", "ERROR")
        return

    # Step 3: Match events
    match_results = matcher.match_events(pwa_events, pwa_divisions)

    # Step 4: Save report
    report_df = matcher.save_report()

    # Step 5: Print summary
    if report_df is not None:
        matcher.print_summary(report_df)


if __name__ == "__main__":
    main()
