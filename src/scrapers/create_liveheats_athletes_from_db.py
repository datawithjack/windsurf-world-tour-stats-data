"""
Create LiveHeats athlete data from database results (workaround for API auth issues).

Since LiveHeats GraphQL API requires authentication for individual athlete queries,
we'll use the athlete names already stored in our PWA_IWT_RESULTS table.
"""

import mysql.connector
import pandas as pd
import os
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

def extract_liveheats_athletes_from_db():
    """
    Extract LiveHeats athlete data from database results.

    Returns:
        DataFrame with athlete_id, name, first_seen_year, last_seen_year, event_count
    """
    print("Extracting LiveHeats athlete data from database...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            athlete_id,
            athlete_name as name,
            MIN(year) as first_seen_year,
            MAX(year) as last_seen_year,
            COUNT(DISTINCT event_id) as event_count
        FROM PWA_IWT_RESULTS
        WHERE source = 'Live Heats'
          AND athlete_id IS NOT NULL
          AND athlete_id != ''
          AND athlete_name IS NOT NULL
          AND athlete_name != ''
        GROUP BY athlete_id, athlete_name
        ORDER BY athlete_name
        """

        cursor.execute(query)
        results = cursor.fetchall()

        df = pd.DataFrame(results, columns=[
            'athlete_id', 'name', 'first_seen_year', 'last_seen_year', 'event_count'
        ])

        print(f"  Found {len(df)} LiveHeats athletes with names in database")

        return df

    finally:
        cursor.close()
        conn.close()

def main():
    """Main execution function"""
    print("Creating LiveHeats Athlete Data from Database")
    print("=" * 50)

    # Extract athlete data
    lh_df = extract_liveheats_athletes_from_db()

    # Add placeholder columns to match expected schema
    lh_df['image_url'] = None
    lh_df['dob'] = None
    lh_df['year_of_birth'] = None
    lh_df['nationality'] = None
    lh_df['alt_athlete_id'] = None

    # Save outputs
    output_dir = 'data/raw/athletes'
    os.makedirs(output_dir, exist_ok=True)

    raw_output = f'{output_dir}/liveheats_athletes_raw.csv'
    clean_output = f'{output_dir}/liveheats_athletes_clean.csv'

    lh_df.to_csv(raw_output, index=False)
    lh_df.to_csv(clean_output, index=False)

    print(f"\nSaved to: {raw_output}")
    print(f"Saved to: {clean_output}")

    # Display summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total LiveHeats athletes: {len(lh_df)}")
    print(f"  With names: {lh_df['name'].notna().sum()}")
    print(f"  Years covered: {lh_df['first_seen_year'].min()}-{lh_df['last_seen_year'].max()}")

    # Show sample
    print("\nSample athletes:")
    print(lh_df[['athlete_id', 'name', 'first_seen_year', 'event_count']].head(20).to_string(index=False))

if __name__ == "__main__":
    main()
