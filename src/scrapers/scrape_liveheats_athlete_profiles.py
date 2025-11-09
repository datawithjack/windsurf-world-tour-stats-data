"""
Scrape LiveHeats athlete profiles using GraphQL API via event divisions.

This script queries event divisions from the database and extracts athlete data
from the heats/competitors structure (the public API endpoint that doesn't require auth).
"""

import requests
import json
import pandas as pd
from datetime import datetime
import os
import time
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """Create connection to Oracle MySQL Heatwave database"""
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        connect_timeout=30
    )
    return conn

def get_division_ids_from_db():
    """Get unique LiveHeats division IDs from database"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT DISTINCT
            CAST(liveheats_division_id AS UNSIGNED) as division_id
        FROM PWA_IWT_HEAT_RESULTS
        WHERE source = 'Live Heats'
          AND liveheats_division_id IS NOT NULL
        ORDER BY division_id
        """

        cursor.execute(query)
        results = cursor.fetchall()
        division_ids = [str(int(r[0])) for r in results]

        return division_ids

    finally:
        cursor.close()
        conn.close()

def fetch_athletes_by_division(division_id):
    """
    Fetch athlete data from a LiveHeats event division.

    This uses the eventDivision query which is publicly accessible
    and returns athlete data through heats/competitors structure.

    Args:
        division_id: LiveHeats division ID (string)

    Returns:
        Dictionary of unique athletes keyed by athlete_id
    """
    url = "https://liveheats.com/api/graphql"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    # GraphQL query to get athletes via event division
    query = """
    query getAthleteInfo($id: ID!) {
      eventDivision(id: $id) {
        heats {
          competitors {
            athlete {
              id
              name
              image
              dob
              nationality
            }
          }
        }
      }
    }
    """

    variables = {"id": str(division_id)}
    payload = {"query": query, "variables": variables}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Check for GraphQL errors
        if 'errors' in data:
            print(f"  GraphQL error for division {division_id}: {data['errors']}")
            return {}

        if 'data' not in data or 'eventDivision' not in data['data'] or data['data']['eventDivision'] is None:
            print(f"  No division data found for ID {division_id}")
            return {}

        # Extract unique athletes
        unique_athletes = {}
        for heat in data['data']['eventDivision']['heats']:
            for competitor in heat['competitors']:
                athlete = competitor['athlete']

                # Extract year of birth from dob
                dob = athlete.get('dob')
                year_of_birth = None
                if dob:
                    try:
                        year_of_birth = int(dob.split('-')[0])
                    except:
                        pass

                unique_athletes[athlete['id']] = {
                    'athlete_id': athlete['id'],
                    'name': athlete.get('name'),
                    'image_url': athlete.get('image'),
                    'dob': dob,
                    'year_of_birth': year_of_birth,
                    'nationality': athlete.get('nationality')
                }

        return unique_athletes

    except requests.exceptions.RequestException as e:
        print(f"  ERROR fetching division {division_id}: {str(e)}")
        return {}

def clean_liveheats_data(df):
    """
    Clean LiveHeats athlete data following same cleaning rules as old script.

    Args:
        df: DataFrame with raw LiveHeats data

    Returns:
        Cleaned DataFrame
    """
    print("\nCleaning LiveHeats data...")

    original_count = len(df)

    # Convert names to title case
    if 'name' in df.columns:
        df['name'] = df['name'].str.title()

    # Merge duplicate records based on name + nationality
    # Group by name and nationality, keeping most complete record
    def merge_records(group):
        if len(group) == 1:
            group = group.copy()
            group['alt_athlete_id'] = pd.NA
            return group.iloc[0]
        else:
            # Calculate completeness: count of non-null fields
            completeness = group.notnull().sum(axis=1)
            # Get the index of the least complete record for alt_id
            idx_min = completeness.idxmin()
            alt_id = group.loc[idx_min, 'athlete_id']

            # Create merged record by taking first non-null value for each column
            merged = {}
            for col in group.columns:
                non_nulls = group[col].dropna()
                merged[col] = non_nulls.iloc[0] if not non_nulls.empty else None

            # Add alt_athlete_id
            merged['alt_athlete_id'] = alt_id

            return pd.Series(merged)

    # Only group if we have duplicates
    duplicates = df.duplicated(subset=['name', 'nationality'], keep=False)
    if duplicates.any():
        print(f"  Found {duplicates.sum()} duplicate records (by name + nationality)")
        df_grouped = df.groupby(['name', 'nationality'], as_index=False, dropna=False).apply(merge_records)
        df_grouped.reset_index(drop=True, inplace=True)
        df = df_grouped
    else:
        df['alt_athlete_id'] = pd.NA

    cleaned_count = len(df)
    print(f"  Removed {original_count - cleaned_count} duplicate records during cleaning")
    print(f"  Final count: {cleaned_count} LiveHeats athletes")

    return df

def main():
    """Main execution function"""
    print("LiveHeats Athlete Profile Scraper")
    print("=" * 50)

    # Get division IDs from database
    print("\nFetching division IDs from database...")
    division_ids = get_division_ids_from_db()
    print(f"Found {len(division_ids)} unique divisions to query")

    # Scrape athlete data from all divisions
    all_athletes = {}
    total_divisions = len(division_ids)

    for idx, division_id in enumerate(division_ids, 1):
        print(f"\n[{idx}/{total_divisions}] Fetching division {division_id}...")

        division_athletes = fetch_athletes_by_division(division_id)

        if division_athletes:
            print(f"  Found {len(division_athletes)} athletes in this division")
            # Merge into all_athletes (will deduplicate by athlete_id)
            all_athletes.update(division_athletes)

        # Be polite to the API
        time.sleep(0.5)

    print(f"\nTotal unique athletes found: {len(all_athletes)}")

    # Convert to DataFrame
    df = pd.DataFrame(list(all_athletes.values()))

    # Save raw data
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    raw_output = f'{output_dir}/liveheats_athletes_raw.csv'
    df.to_csv(raw_output, index=False)
    print(f"\n[OK] Raw data saved to: {raw_output}")

    # Also save as JSON for compatibility
    raw_json_output = f'{output_dir}/liveheats_athletes_raw.json'
    df.to_json(raw_json_output, orient='records', indent=4)
    print(f"[OK] Raw JSON saved to: {raw_json_output}")

    # Clean the data
    df_clean = clean_liveheats_data(df)

    # Save cleaned data
    clean_output = f'{output_dir}/liveheats_athletes_clean.csv'
    df_clean.to_csv(clean_output, index=False)
    print(f"[OK] Cleaned data saved to: {clean_output}")

    # Display summary
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total scraped: {len(df)}")
    print(f"After cleaning: {len(df_clean)}")
    print(f"Divisions queried: {total_divisions}")

    # Show sample
    print("\nSample cleaned data:")
    print(df_clean[['athlete_id', 'name', 'nationality', 'year_of_birth', 'dob']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
