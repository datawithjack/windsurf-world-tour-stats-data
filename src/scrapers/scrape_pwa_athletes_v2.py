"""
Scrape PWA athlete profiles - FIXED VERSION

This script properly scrapes PWA athlete profiles using the athlete IDs from the database.
Uses requests + BeautifulSoup with proper error handling and retries.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import re
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    """Create requests session with retry logic"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def scrape_pwa_athlete(session, athlete_id):
    """
    Scrape a single PWA athlete profile.

    Args:
        session: requests session
        athlete_id: PWA athlete ID (numeric)

    Returns:
        Dictionary with athlete data
    """
    # Add cHash parameter (generic one works for all athlete pages)
    url = f"https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1[showUid]={athlete_id}&cHash=3079be6910811c9a204a0edff446b23b"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = session.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract name from first H2 (after the page title)
        name = None
        h2_tags = soup.find_all('h2')
        if len(h2_tags) >= 1:
            # First H2 is the athlete name
            name = h2_tags[0].text.strip()
            # Clean up extra whitespace
            name = ' '.join(name.split())

        # Try multiple patterns for sail number
        sail_no = None
        for selector in ['.sail-no', '.sailor-number', '.athlete-number']:
            elem = soup.select_one(selector)
            if elem:
                sail_no = elem.text.strip()
                break

        # If no sail number found, look for pattern like "E-95" in text
        if not sail_no:
            text_content = soup.get_text()
            match = re.search(r'\b([A-Z]{1,3}-\d+)\b', text_content)
            if match:
                sail_no = match.group(1)

        # Extract age and nationality from base info
        age = None
        nationality = None
        year_of_birth = None

        for selector in ['.sailor-details-info-base', '.athlete-info', '.bio-info']:
            base_info = soup.select_one(selector)
            if base_info:
                raw_text = base_info.get_text(separator="\n")

                age_match = re.search(r'Age:\s*(\d+)', raw_text, re.IGNORECASE)
                if age_match:
                    age = int(age_match.group(1))
                    year_of_birth = datetime.now().year - age

                nat_match = re.search(r'Nationality:\s*([^\n]+)', raw_text, re.IGNORECASE)
                if nat_match:
                    nationality = nat_match.group(1).strip()
                break

        # Extract sponsors
        sponsors = None
        for selector in ['.sponsors', '.athlete-sponsors', '.sponsor-list']:
            sponsor_div = soup.find("div", class_=selector.replace('.', ''))
            if sponsor_div:
                sponsor_text = sponsor_div.get_text(separator=" ", strip=True)
                if sponsor_text.startswith("Sponsors"):
                    sponsors = sponsor_text[len("Sponsors"):].strip()
                else:
                    sponsors = sponsor_text
                break

        return {
            'athlete_id': athlete_id,
            'name': name,
            'age': age,
            'year_of_birth': year_of_birth,
            'nationality': nationality,
            'sail_number': sail_no,
            'sponsors': sponsors,
            'profile_url': url,
            'scraped_at': datetime.now().isoformat(),
            'scrape_success': name is not None
        }

    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return {
            'athlete_id': athlete_id,
            'name': None,
            'age': None,
            'year_of_birth': None,
            'nationality': None,
            'sail_number': None,
            'sponsors': None,
            'profile_url': url,
            'scraped_at': datetime.now().isoformat(),
            'scrape_success': False,
            'error': str(e)
        }

def main():
    """Main execution"""
    print("PWA Athlete Profile Scraper - V2")
    print("=" * 50)

    # Load athletes to scrape
    input_file = 'data/raw/athletes/pwa_athletes_to_scrape.csv'
    if not os.path.exists(input_file):
        print(f"ERROR: {input_file} not found")
        return

    athletes_to_scrape = pd.read_csv(input_file)
    print(f"\nLoaded {len(athletes_to_scrape)} PWA athletes to scrape")

    # Create session
    session = create_session()

    # Scrape all athletes
    results = []
    total = len(athletes_to_scrape)
    success_count = 0

    for idx, row in athletes_to_scrape.iterrows():
        athlete_id = row['athlete_id']
        athlete_name = row['athlete_name']

        print(f"\n[{idx + 1}/{total}] Scraping: {athlete_name} (ID: {athlete_id})")

        profile_data = scrape_pwa_athlete(session, athlete_id)

        # Add database metadata
        profile_data['db_name'] = athlete_name
        profile_data['db_sail_number'] = row['sail_number']
        profile_data['first_seen_year'] = row['first_seen_year']
        profile_data['last_seen_year'] = row['last_seen_year']
        profile_data['event_count'] = row['event_count']

        results.append(profile_data)

        if profile_data['scrape_success']:
            success_count += 1
            print(f"  OK: {profile_data['name']}, {profile_data['sail_number']}")
        else:
            print(f"  FAILED: No data extracted")

        # Be polite to server
        time.sleep(0.5)

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Save raw data
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    raw_output = f'{output_dir}/pwa_athletes_raw.csv'
    df.to_csv(raw_output, index=False)
    print(f"\n[OK] Raw data saved: {raw_output}")

    # Clean data (only keep successful scrapes)
    df_clean = df[df['scrape_success'] == True].copy()
    df_clean = df_clean.drop(columns=['scrape_success', 'error'], errors='ignore')

    clean_output = f'{output_dir}/pwa_athletes_clean.csv'
    df_clean.to_csv(clean_output, index=False)
    print(f"[OK] Clean data saved: {clean_output}")

    # Summary
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total attempted: {total}")
    print(f"Successful: {success_count} ({success_count/total*100:.1f}%)")
    print(f"Failed: {total - success_count}")

    # Sample
    if len(df_clean) > 0:
        print("\nSample athletes:")
        print(df_clean[['athlete_id', 'name', 'sail_number', 'nationality', 'year_of_birth']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
