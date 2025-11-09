"""
Load merged wave results into Oracle MySQL Heatwave database
Loads data from wave_results_merged.csv into PWA_IWT_RESULTS table
"""

import os
import sys
import pandas as pd
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

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


def load_merged_results(csv_filename=None):
    """
    Load merged wave results CSV file

    Args:
        csv_filename: Optional specific filename to load (otherwise uses latest)

    Returns:
        DataFrame with merged results
    """
    # Get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    processed_dir = os.path.join(project_root, 'data', 'processed')

    # If specific filename provided, use it
    if csv_filename:
        csv_path = os.path.join(processed_dir, csv_filename)
    else:
        # Find the most recent wave_results_merged file
        import glob
        pattern = os.path.join(processed_dir, 'wave_results_merged*.csv')
        files = glob.glob(pattern)

        if not files:
            raise FileNotFoundError(f"No merged results files found in {processed_dir}")

        # Get most recent file
        csv_path = max(files, key=os.path.getmtime)

    print(f"Loading CSV from: {csv_path}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Merged results file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    print(f"[OK] Loaded {len(df)} records from CSV")
    print(f"Columns: {', '.join(df.columns)}")

    return df


def prepare_data(df):
    """
    Prepare data for database insertion

    Args:
        df: DataFrame with merged results

    Returns:
        List of tuples ready for insertion
    """
    print("\nPreparing data for database insertion...")

    records = []

    for idx, row in df.iterrows():
        # Handle scraped_at datetime
        try:
            scraped_at = pd.to_datetime(row['scraped_at']).strftime('%Y-%m-%d %H:%M:%S')
        except:
            scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Handle NaN/None values
        record = (
            str(row['source']) if pd.notna(row['source']) else 'Unknown',
            scraped_at,
            int(row['event_id']) if pd.notna(row['event_id']) else 0,
            int(row['year']) if pd.notna(row['year']) else 0,
            str(row['event_name']) if pd.notna(row['event_name']) else '',
            str(row['division_label']) if pd.notna(row['division_label']) else '',
            str(row['division_code']) if pd.notna(row['division_code']) else '',
            str(row['sex']) if pd.notna(row['sex']) else '',
            str(row['place']) if pd.notna(row['place']) else '',
            str(row['athlete_name']) if pd.notna(row['athlete_name']) else '',
            str(row['sail_number']) if pd.notna(row['sail_number']) else '',
            str(row['athlete_id']) if pd.notna(row['athlete_id']) else ''
        )

        records.append(record)

    print(f"[OK] Prepared {len(records)} records for insertion")
    return records


def insert_results(cursor, records, batch_size=100):
    """
    Insert results into database using batch processing

    Args:
        cursor: Database cursor
        records: List of tuples to insert
        batch_size: Number of records per batch (default 100)
    """
    insert_sql = """
    INSERT INTO PWA_IWT_RESULTS (
        source, scraped_at, event_id, year, event_name,
        division_label, division_code, sex, place,
        athlete_name, sail_number, athlete_id
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        scraped_at = VALUES(scraped_at),
        year = VALUES(year),
        event_name = VALUES(event_name),
        division_label = VALUES(division_label),
        sex = VALUES(sex),
        athlete_name = VALUES(athlete_name),
        sail_number = VALUES(sail_number),
        updated_at = CURRENT_TIMESTAMP
    """

    total_records = len(records)
    batches = (total_records + batch_size - 1) // batch_size

    print(f"\nInserting {total_records} records in {batches} batches...")

    inserted = 0
    updated = 0

    for i in range(0, total_records, batch_size):
        batch = records[i:i+batch_size]
        batch_num = (i // batch_size) + 1

        try:
            cursor.executemany(insert_sql, batch)
            inserted += cursor.rowcount

            print(f"  Batch {batch_num}/{batches}: Processed {len(batch)} records")

        except Exception as e:
            print(f"  [ERROR] Batch {batch_num} failed: {e}")
            raise

    print(f"\n[OK] Database operations complete")
    print(f"  Total records processed: {total_records}")

    return inserted


def verify_data(cursor):
    """
    Verify data was loaded correctly

    Args:
        cursor: Database cursor
    """
    print("\nVerifying data in database...")

    # Count total records
    cursor.execute("SELECT COUNT(*) FROM PWA_IWT_RESULTS")
    total_count = cursor.fetchone()[0]
    print(f"  Total records in table: {total_count}")

    # Count by source
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM PWA_IWT_RESULTS
        GROUP BY source
        ORDER BY count DESC
    """)
    print("\n  Records by source:")
    for source, count in cursor.fetchall():
        print(f"    {source}: {count}")

    # Count by year
    cursor.execute("""
        SELECT year, COUNT(*) as count
        FROM PWA_IWT_RESULTS
        WHERE year > 0
        GROUP BY year
        ORDER BY year DESC
    """)
    print("\n  Records by year:")
    for year, count in cursor.fetchall():
        print(f"    {year}: {count}")

    # Count by division/sex
    cursor.execute("""
        SELECT division_label, sex, COUNT(*) as count
        FROM PWA_IWT_RESULTS
        GROUP BY division_label, sex
        ORDER BY count DESC
    """)
    print("\n  Records by division:")
    for div, sex, count in cursor.fetchall():
        print(f"    {div} ({sex}): {count}")


def main():
    """Main execution"""
    print("="*80)
    print("LOAD WAVE RESULTS INTO ORACLE DATABASE")
    print("="*80)
    print()

    try:
        # Step 1: Load CSV
        df = load_merged_results()

        # Step 2: Prepare data
        records = prepare_data(df)

        # Step 3: Connect to database
        print("\nConnecting to Oracle MySQL Heatwave...")
        conn = get_connection()
        cursor = conn.cursor()
        print("[OK] Connected to database")

        # Step 4: Insert data
        insert_results(cursor, records, batch_size=100)

        # Step 5: Commit transaction
        print("\nCommitting transaction...")
        conn.commit()
        print("[OK] Transaction committed")

        # Step 6: Verify data
        verify_data(cursor)

        print("\n" + "="*80)
        print("[SUCCESS] Wave results loaded successfully!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] Failed to load wave results: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
