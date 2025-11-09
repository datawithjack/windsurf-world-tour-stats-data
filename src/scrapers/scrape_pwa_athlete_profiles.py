"""
Scrape PWA athlete profiles using BeautifulSoup.

This script takes the list of PWA athlete IDs from the database and scrapes
their profile pages to get additional metadata (age, nationality, sponsors, etc).
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from datetime import datetime
import os

def scrape_pwa_athlete_by_id(athlete_id, base_url="https://www.pwaworldtour.com/"):
    """
    Scrape a single PWA athlete profile by their athlete_id.

    Args:
        athlete_id: PWA athlete ID (numeric)
        base_url: Base URL for PWA website

    Returns:
        Dictionary with athlete data or None if scraping fails
    """
    # Construct profile URL using athlete ID
    # Pattern: index.php?id=7&tx_pwasailor_pi1[showUid]={athlete_id}
    url = f"{base_url}index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D={athlete_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract name
        try:
            name = soup.select_one('.sailor-details-info-top h2').text.strip()
        except:
            name = None

        # Extract sail number
        try:
            sail_no = soup.select_one('.sail-no').text.strip()
        except:
            sail_no = None

        # Extract age and nationality from the base info section
        try:
            base_info = soup.select_one('.sailor-details-info-base')
            raw_text = base_info.get_text(separator="\n")

            age_match = re.search(r'Age:\s*(\d+)', raw_text)
            nationality_match = re.search(r'Nationality:\s*([^\n]+)', raw_text)
            age = int(age_match.group(1)) if age_match else None
            nationality = nationality_match.group(1).strip() if nationality_match else None
        except:
            age = None
            nationality = None

        # Extract current sponsors from the sponsors div
        try:
            sponsor_div = soup.find("div", class_="sponsors")
            if sponsor_div:
                sponsor_text = sponsor_div.get_text(separator=" ", strip=True)
                # Remove the header "Sponsors" if present
                if sponsor_text.startswith("Sponsors"):
                    current_sponsors = sponsor_text[len("Sponsors"):].strip()
                else:
                    current_sponsors = sponsor_text
            else:
                current_sponsors = None
        except:
            current_sponsors = None

        # Calculate year of birth from age
        current_year = datetime.now().year
        year_of_birth = current_year - age if age else None

        return {
            'athlete_id': athlete_id,
            'name': name,
            'age': age,
            'year_of_birth': year_of_birth,
            'nationality': nationality,
            'sail_number': sail_no,
            'sponsors': current_sponsors,
            'profile_url': url,
            'scraped_at': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"  ERROR scraping athlete {athlete_id}: {str(e)}")
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
            'error': str(e)
        }

def clean_pwa_data(df):
    """
    Clean PWA athlete data following the same cleaning rules as old script.

    Args:
        df: DataFrame with raw PWA data

    Returns:
        Cleaned DataFrame
    """
    print("\nCleaning PWA data...")

    original_count = len(df)

    # Remove extra spaces from name
    if 'name' in df.columns:
        df['name'] = df['name'].astype(str).apply(lambda x: re.sub(r'\s+', ' ', x).strip())

        # Remove rows where name is null or "nan"
        df = df[df['name'].notna()]
        df = df[df['name'].str.lower() != 'nan']

    # Remove rows with sail_number that doesn't contain any digit
    if 'sail_number' in df.columns:
        df = df[df['sail_number'].str.contains(r'\d', na=False)]

        # Remove specific unwanted sail numbers
        unwanted_sailnos = ["CRO-751", "E-4", "SGP-21"]
        df = df[~df['sail_number'].isin(unwanted_sailnos)]

    # Remove specific unwanted URLs
    unwanted_urls = [
        "https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D=1835",
        "https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D=2013",
        "https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D=1962",
        "https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D=1977",
        "https://www.pwaworldtour.com/index.php?id=7&tx_pwasailor_pi1%5BshowUid%5D=2053"
    ]
    # Check if URL starts with any unwanted URL (handles different parameter formats)
    for unwanted_url in unwanted_urls:
        df = df[~df['profile_url'].str.startswith(unwanted_url)]

    # Remove specific names
    df = df[(df['name'] != 'Marc') & (df['name'] != 'Farrah Hall')]

    # Fix Julian Salmonn's sail number
    df.loc[df['name'] == 'Julian Salmonn', 'sail_number'] = 'G-901'

    cleaned_count = len(df)
    print(f"  Removed {original_count - cleaned_count} records during cleaning")
    print(f"  Final count: {cleaned_count} PWA athletes")

    return df

def main():
    """Main execution function"""
    print("PWA Athlete Profile Scraper")
    print("=" * 50)

    # Load the list of PWA athletes to scrape
    input_file = 'data/raw/athletes/pwa_athletes_to_scrape.csv'

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        print("Please run extract_unique_athletes.py first.")
        return

    athletes_to_scrape = pd.read_csv(input_file)
    print(f"\nLoaded {len(athletes_to_scrape)} PWA athletes to scrape")

    # Scrape profiles
    results = []
    total = len(athletes_to_scrape)

    for idx, row in athletes_to_scrape.iterrows():
        athlete_id = row['athlete_id']
        athlete_name = row['athlete_name']

        print(f"\n[{idx + 1}/{total}] Scraping: {athlete_name} (ID: {athlete_id})")

        profile_data = scrape_pwa_athlete_by_id(athlete_id)

        if profile_data:
            # Add database metadata
            profile_data['db_name'] = athlete_name
            profile_data['db_sail_number'] = row['sail_number']
            profile_data['first_seen_year'] = row['first_seen_year']
            profile_data['last_seen_year'] = row['last_seen_year']
            profile_data['event_count'] = row['event_count']
            results.append(profile_data)

        # Be polite to the server
        time.sleep(0.5)

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Save raw data
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    raw_output = f'{output_dir}/pwa_athletes_raw.csv'
    df.to_csv(raw_output, index=False)
    print(f"\n✓ Raw data saved to: {raw_output}")

    # Clean the data
    df_clean = clean_pwa_data(df)

    # Save cleaned data
    clean_output = f'{output_dir}/pwa_athletes_clean.csv'
    df_clean.to_csv(clean_output, index=False)
    print(f"✓ Cleaned data saved to: {clean_output}")

    # Display summary
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total scraped: {len(df)}")
    print(f"After cleaning: {len(df_clean)}")
    print(f"Success rate: {len(df_clean)/total*100:.1f}%")

    # Show sample
    print("\nSample cleaned data:")
    print(df_clean[['athlete_id', 'name', 'sail_number', 'nationality', 'year_of_birth']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
