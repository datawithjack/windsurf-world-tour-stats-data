"""
Load PWA wave event results into Oracle MySQL Heatwave database
"""
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


def get_connection():
    """Create connection to Oracle MySQL Heatwave database"""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', '3306'))
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')

    if not all([db_name, db_user, db_password]):
        raise ValueError("DB_NAME, DB_USER, and DB_PASSWORD must be set in .env file")

    conn = mysql.connector.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        connect_timeout=30
    )
    return conn


def load_pwa_events(cursor, csv_path):
    """
    Load PWA event metadata from CSV into PWA_IWT_EVENTS table

    Args:
        cursor: Database cursor
        csv_path: Path to PWA events CSV file
    """
    print(f"Loading PWA events from: {csv_path}")

    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"Found {len(df)} events to load")

    # Prepare insert statement
    insert_sql = """
    INSERT INTO PWA_IWT_EVENTS
    (source, scraped_at, year, event_id, event_name, event_url, event_date,
     start_date, end_date, day_window, event_section, event_status, competition_state,
     has_wave_discipline, all_disciplines, country_flag, country_code, stars, event_image_url)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        scraped_at = VALUES(scraped_at),
        event_name = VALUES(event_name),
        event_url = VALUES(event_url),
        event_date = VALUES(event_date),
        start_date = VALUES(start_date),
        end_date = VALUES(end_date),
        day_window = VALUES(day_window),
        event_section = VALUES(event_section),
        event_status = VALUES(event_status),
        competition_state = VALUES(competition_state),
        has_wave_discipline = VALUES(has_wave_discipline),
        all_disciplines = VALUES(all_disciplines),
        country_flag = VALUES(country_flag),
        country_code = VALUES(country_code),
        stars = VALUES(stars),
        event_image_url = VALUES(event_image_url)
    """

    # Insert data in batches
    batch_size = 100
    total_inserted = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]

        for _, row in batch.iterrows():
            # Convert scraped_at to datetime
            scraped_at = pd.to_datetime(row['scraped_at'])

            # Handle date fields
            start_date = pd.to_datetime(row['start_date']) if pd.notna(row['start_date']) else None
            end_date = pd.to_datetime(row['end_date']) if pd.notna(row['end_date']) else None

            # Handle NaN values
            event_url = row['event_url'] if pd.notna(row['event_url']) else None
            event_date = row['event_date'] if pd.notna(row['event_date']) else None
            day_window = int(row['day_window']) if pd.notna(row['day_window']) else None
            event_section = row['event_section'] if pd.notna(row['event_section']) else None
            event_status = int(row['event_status']) if pd.notna(row['event_status']) else None
            competition_state = int(row['competition_state']) if pd.notna(row['competition_state']) else None
            all_disciplines = row['all_disciplines'] if pd.notna(row['all_disciplines']) else None
            country_flag = row['country_flag'] if pd.notna(row['country_flag']) else None
            country_code = row['country_code'] if pd.notna(row['country_code']) else None
            stars = int(row['stars']) if pd.notna(row['stars']) else None
            event_image_url = row['event_image_url'] if pd.notna(row['event_image_url']) else None

            cursor.execute(insert_sql, (
                row['source'],
                scraped_at,
                int(row['year']),
                int(row['event_id']),
                row['event_name'],
                event_url,
                event_date,
                start_date,
                end_date,
                day_window,
                event_section,
                event_status,
                competition_state,
                bool(row['has_wave_discipline']),
                all_disciplines,
                country_flag,
                country_code,
                stars,
                event_image_url
            ))

            total_inserted += 1

        # Print progress
        print(f"  Processed {min(i + batch_size, len(df))}/{len(df)} rows...")

    print(f"[OK] Loaded {total_inserted} PWA events")
    return total_inserted


def main():
    """Main execution"""
    print("="*80)
    print("LOAD PWA EVENTS INTO ORACLE DATABASE")
    print("="*80)
    print()

    # Input CSV - construct path relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pwa_events_csv = os.path.join(project_root, "data", "raw", "pwa", "pwa_events_raw.csv")

    try:
        # Connect to database
        print("Connecting to Oracle MySQL Heatwave...")
        conn = get_connection()
        cursor = conn.cursor()
        print("[OK] Connected to database")
        print()

        # Load PWA events
        total = load_pwa_events(cursor, pwa_events_csv)

        # Commit changes
        conn.commit()

        print()
        print("="*80)
        print(f"[OK] Successfully loaded {total} events!")
        print("="*80)

        # Verify data
        print("\nVerifying data in database...")
        cursor.execute("SELECT COUNT(*) FROM PWA_IWT_EVENTS")
        count = cursor.fetchone()[0]
        print(f"Total rows in PWA_IWT_EVENTS: {count}")

        cursor.execute("SELECT year, COUNT(*) as cnt FROM PWA_IWT_EVENTS GROUP BY year ORDER BY year")
        print("\nEvents by year:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} events")

        cursor.execute("SELECT COUNT(*) FROM PWA_IWT_EVENTS WHERE has_wave_discipline = TRUE")
        wave_count = cursor.fetchone()[0]
        print(f"\nWave discipline events: {wave_count}")

    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
