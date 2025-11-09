"""
Load athlete data into MySQL database.

Loads data from:
- athletes_final.csv → ATHLETES table
- athlete_ids_link.csv → ATHLETE_SOURCE_IDS table
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

def load_athletes(cursor, conn, athletes_df):
    """
    Load athlete data into ATHLETES table.

    Args:
        cursor: Database cursor
        conn: Database connection
        athletes_df: DataFrame with athlete data
    """
    print("\nLoading ATHLETES table...")
    print(f"  Records to load: {len(athletes_df)}")

    # Prepare INSERT statement with ON DUPLICATE KEY UPDATE
    insert_sql = """
    INSERT INTO ATHLETES (
        id,
        primary_name,
        pwa_name,
        liveheats_name,
        match_score,
        match_stage,
        year_of_birth,
        nationality,
        pwa_athlete_id,
        pwa_sail_number,
        pwa_profile_url,
        pwa_sponsors,
        pwa_nationality,
        pwa_year_of_birth,
        liveheats_athlete_id,
        liveheats_image_url,
        liveheats_dob,
        liveheats_nationality,
        liveheats_year_of_birth
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        primary_name = VALUES(primary_name),
        pwa_name = VALUES(pwa_name),
        liveheats_name = VALUES(liveheats_name),
        match_score = VALUES(match_score),
        match_stage = VALUES(match_stage),
        year_of_birth = VALUES(year_of_birth),
        nationality = VALUES(nationality),
        pwa_athlete_id = VALUES(pwa_athlete_id),
        pwa_sail_number = VALUES(pwa_sail_number),
        pwa_profile_url = VALUES(pwa_profile_url),
        pwa_sponsors = VALUES(pwa_sponsors),
        pwa_nationality = VALUES(pwa_nationality),
        pwa_year_of_birth = VALUES(pwa_year_of_birth),
        liveheats_athlete_id = VALUES(liveheats_athlete_id),
        liveheats_image_url = VALUES(liveheats_image_url),
        liveheats_dob = VALUES(liveheats_dob),
        liveheats_nationality = VALUES(liveheats_nationality),
        liveheats_year_of_birth = VALUES(liveheats_year_of_birth),
        updated_at = CURRENT_TIMESTAMP
    """

    # Prepare data for batch insert
    batch_size = 100
    total_inserted = 0
    total_updated = 0

    for i in range(0, len(athletes_df), batch_size):
        batch = athletes_df.iloc[i:i + batch_size]
        batch_data = []

        for _, row in batch.iterrows():
            # Convert date string to proper format for MySQL
            lh_dob = None
            if pd.notna(row.get('lh_dob')):
                try:
                    lh_dob = pd.to_datetime(row['lh_dob']).strftime('%Y-%m-%d')
                except:
                    lh_dob = None

            # Prepare values, handling NaN/None
            values = (
                int(row['id']) if pd.notna(row.get('id')) else None,
                row['primary_name'] if pd.notna(row.get('primary_name')) else None,
                row['pwa_name'] if pd.notna(row.get('pwa_name')) else None,
                row['lh_name'] if pd.notna(row.get('lh_name')) else None,
                int(row['match_score']) if pd.notna(row.get('match_score')) else None,
                row['match_stage'] if pd.notna(row.get('match_stage')) else None,
                int(row['year_of_birth']) if pd.notna(row.get('year_of_birth')) else None,
                row['nationality'] if pd.notna(row.get('nationality')) else None,
                str(row['pwa_athlete_id']) if pd.notna(row.get('pwa_athlete_id')) else None,
                row['pwa_sail_number'] if pd.notna(row.get('pwa_sail_number')) else None,
                row['pwa_profile_url'] if pd.notna(row.get('pwa_profile_url')) else None,
                row['pwa_sponsors'] if pd.notna(row.get('pwa_sponsors')) else None,
                row['pwa_nationality'] if pd.notna(row.get('pwa_nationality')) else None,
                int(row['pwa_year_of_birth']) if pd.notna(row.get('pwa_year_of_birth')) else None,
                str(row['lh_athlete_id']) if pd.notna(row.get('lh_athlete_id')) else None,
                row['lh_image_url'] if pd.notna(row.get('lh_image_url')) else None,
                lh_dob,
                row['lh_nationality'] if pd.notna(row.get('lh_nationality')) else None,
                int(row['lh_year_of_birth']) if pd.notna(row.get('lh_year_of_birth')) else None,
            )
            batch_data.append(values)

        # Execute batch
        try:
            cursor.executemany(insert_sql, batch_data)
            conn.commit()
            total_inserted += cursor.rowcount
            print(f"  Processed {min(i + batch_size, len(athletes_df))}/{len(athletes_df)} records...")
        except mysql.connector.Error as err:
            print(f"  ERROR in batch starting at row {i}: {err}")
            conn.rollback()
            raise

    print(f"  [OK] Loaded {total_inserted} athlete records")

def load_athlete_source_ids(cursor, conn, link_df):
    """
    Load athlete source ID mappings into ATHLETE_SOURCE_IDS table.

    Args:
        cursor: Database cursor
        conn: Database connection
        link_df: DataFrame with athlete ID links
    """
    print("\nLoading ATHLETE_SOURCE_IDS table...")
    print(f"  Records to load: {len(link_df)}")

    # Prepare INSERT statement with ON DUPLICATE KEY UPDATE
    insert_sql = """
    INSERT INTO ATHLETE_SOURCE_IDS (
        athlete_id,
        source,
        source_id
    ) VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        athlete_id = VALUES(athlete_id),
        updated_at = CURRENT_TIMESTAMP
    """

    # Prepare data for batch insert
    batch_size = 500
    total_inserted = 0

    for i in range(0, len(link_df), batch_size):
        batch = link_df.iloc[i:i + batch_size]
        batch_data = []

        for _, row in batch.iterrows():
            values = (
                int(row['athlete_id']) if pd.notna(row['athlete_id']) else None,
                row['source'] if pd.notna(row['source']) else None,
                str(row['source_id']) if pd.notna(row['source_id']) else None,
            )
            batch_data.append(values)

        # Execute batch
        try:
            cursor.executemany(insert_sql, batch_data)
            conn.commit()
            total_inserted += cursor.rowcount
            print(f"  Processed {min(i + batch_size, len(link_df))}/{len(link_df)} records...")
        except mysql.connector.Error as err:
            print(f"  ERROR in batch starting at row {i}: {err}")
            conn.rollback()
            raise

    print(f"  [OK] Loaded {total_inserted} link records")

def verify_load(cursor):
    """
    Verify that data was loaded successfully.
    """
    print("\nVerifying data load...")

    # Count ATHLETES records
    cursor.execute("SELECT COUNT(*) FROM ATHLETES")
    athletes_count = cursor.fetchone()[0]
    print(f"  ATHLETES table: {athletes_count} records")

    # Count ATHLETE_SOURCE_IDS records
    cursor.execute("SELECT COUNT(*) FROM ATHLETE_SOURCE_IDS")
    links_count = cursor.fetchone()[0]
    print(f"  ATHLETE_SOURCE_IDS table: {links_count} records")

    # Show sample athletes
    cursor.execute("""
        SELECT id, primary_name, nationality, year_of_birth, match_stage
        FROM ATHLETES
        LIMIT 10
    """)
    print("\n  Sample athletes:")
    for row in cursor.fetchall():
        print(f"    ID {row[0]}: {row[1]} ({row[2]}, born {row[3]}) - {row[4]}")

def main():
    """Main execution function"""
    print("Loading Athlete Data into Database")
    print("=" * 50)

    # Load CSV files
    athletes_file = 'data/processed/athletes/athletes_final.csv'
    link_file = 'data/processed/athletes/athlete_ids_link.csv'

    if not os.path.exists(athletes_file):
        print(f"ERROR: Athletes file not found: {athletes_file}")
        print("Please run merge_final_athletes.py first.")
        return

    if not os.path.exists(link_file):
        print(f"ERROR: Link file not found: {link_file}")
        print("Please run merge_final_athletes.py first.")
        return

    print(f"\nLoading CSV files...")
    athletes_df = pd.read_csv(athletes_file)
    link_df = pd.read_csv(link_file)

    print(f"  [OK] Athletes: {len(athletes_df)} records")
    print(f"  [OK] Links: {len(link_df)} records")

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print("  [OK] Connected successfully")

        # Load data
        load_athletes(cursor, conn, athletes_df)
        load_athlete_source_ids(cursor, conn, link_df)

        # Verify
        verify_load(cursor)

        print("\n" + "=" * 50)
        print("SUCCESS: Athlete data loaded successfully!")
        print("=" * 50)

    except mysql.connector.Error as err:
        print(f"\n[ERROR] DATABASE ERROR: {err}")
        return

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    main()
