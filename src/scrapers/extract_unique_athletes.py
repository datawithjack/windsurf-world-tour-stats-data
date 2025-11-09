"""
Extract unique athletes from PWA_IWT_RESULTS table.

This script queries the database to get all unique athlete IDs and names
from the competition results, creating a base list for profile scraping.
"""

import mysql.connector
import pandas as pd
import os
from datetime import datetime
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

def extract_unique_athletes():
    """
    Extract unique athletes from PWA_IWT_RESULTS table.

    Returns:
        DataFrame with columns: source, athlete_id, athlete_name, sail_number,
        first_seen_year, last_seen_year, event_count
    """
    print("Connecting to database...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Query to get unique athletes with metadata
        query = """
        SELECT
            source,
            athlete_id,
            athlete_name,
            sail_number,
            MIN(year) as first_seen_year,
            MAX(year) as last_seen_year,
            COUNT(DISTINCT event_id) as event_count
        FROM PWA_IWT_RESULTS
        WHERE athlete_id IS NOT NULL
          AND athlete_id != ''
        GROUP BY source, athlete_id, athlete_name, sail_number
        ORDER BY source, athlete_name
        """

        print("Executing query to extract unique athletes...")
        cursor.execute(query)
        results = cursor.fetchall()

        # Convert to DataFrame
        df = pd.DataFrame(results, columns=[
            'source', 'athlete_id', 'athlete_name', 'sail_number',
            'first_seen_year', 'last_seen_year', 'event_count'
        ])

        print(f"\nExtracted {len(df)} unique athletes:")
        print(f"  - PWA: {len(df[df['source'] == 'PWA'])} athletes")
        print(f"  - Live Heats: {len(df[df['source'] == 'Live Heats'])} athletes")

        return df

    finally:
        cursor.close()
        conn.close()

def main():
    """Main execution function"""
    # Extract unique athletes
    athletes_df = extract_unique_athletes()

    # Create output directory if it doesn't exist
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    # Save to CSV
    output_file = f'{output_dir}/unique_athletes_from_db.csv'
    athletes_df.to_csv(output_file, index=False)
    print(f"\nSaved to: {output_file}")

    # Split by source for individual scraping
    pwa_athletes = athletes_df[athletes_df['source'] == 'PWA']
    liveheats_athletes = athletes_df[athletes_df['source'] == 'Live Heats']

    pwa_file = f'{output_dir}/pwa_athletes_to_scrape.csv'
    liveheats_file = f'{output_dir}/liveheats_athletes_to_scrape.csv'

    pwa_athletes.to_csv(pwa_file, index=False)
    liveheats_athletes.to_csv(liveheats_file, index=False)

    print(f"\nSplit files created:")
    print(f"  - PWA: {pwa_file} ({len(pwa_athletes)} athletes)")
    print(f"  - LiveHeats: {liveheats_file} ({len(liveheats_athletes)} athletes)")

    # Display sample
    print("\nSample PWA athletes:")
    print(pwa_athletes.head(10).to_string(index=False))

    print("\nSample LiveHeats athletes:")
    print(liveheats_athletes.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
