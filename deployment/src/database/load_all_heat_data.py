"""
Load all merged heat data into Oracle MySQL Heatwave database
Loads heat progression, heat results, and heat scores in one script
"""

import os
import sys
import pandas as pd
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

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


def load_csv(csv_path, name):
    """Load CSV file"""
    print(f"\nLoading {name} from: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"[WARNING] File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    print(f"[OK] Loaded {len(df)} records")
    return df


def load_heat_progression(cursor, df):
    """Load heat progression data"""
    if df is None or df.empty:
        print("[WARNING] No heat progression data to load")
        return 0

    print("\n" + "="*80)
    print("LOADING HEAT PROGRESSION DATA")
    print("="*80)

    insert_sql = """
    INSERT INTO PWA_IWT_HEAT_PROGRESSION (
        source, scraped_at, pwa_event_id, pwa_year, pwa_event_name,
        pwa_division_code, sex, round_name, round_order, heat_id, heat_order,
        total_winners_progressing, winners_progressing_to_round_order,
        total_losers_progressing, losers_progressing_to_round_order,
        elimination_name, liveheats_event_id, liveheats_division_id, division_name
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        scraped_at = VALUES(scraped_at),
        pwa_year = VALUES(pwa_year),
        round_order = VALUES(round_order),
        updated_at = CURRENT_TIMESTAMP
    """

    records = []
    for _, row in df.iterrows():
        try:
            scraped_at = pd.to_datetime(row['scraped_at']).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['scraped_at']) else None
        except:
            scraped_at = None

        record = (
            str(row['source']) if pd.notna(row['source']) else '',
            scraped_at,
            int(row['pwa_event_id']) if pd.notna(row['pwa_event_id']) else None,
            int(row['pwa_year']) if pd.notna(row['pwa_year']) else None,
            str(row['pwa_event_name']) if pd.notna(row['pwa_event_name']) else '',
            str(row['pwa_division_code']) if pd.notna(row['pwa_division_code']) else '',
            str(row['sex']) if pd.notna(row['sex']) else '',
            str(row['round_name']) if pd.notna(row['round_name']) else '',
            int(row['round_order']) if pd.notna(row['round_order']) else None,
            str(row['heat_id']) if pd.notna(row['heat_id']) else '',
            int(row['heat_order']) if pd.notna(row['heat_order']) else None,
            int(row['total_winners_progressing']) if pd.notna(row['total_winners_progressing']) else None,
            int(row['winners_progressing_to_round_order']) if pd.notna(row['winners_progressing_to_round_order']) else None,
            int(row['total_losers_progressing']) if pd.notna(row['total_losers_progressing']) else None,
            int(row['losers_progressing_to_round_order']) if pd.notna(row['losers_progressing_to_round_order']) else None,
            str(row['elimination_name']) if pd.notna(row['elimination_name']) else '',
            str(row['liveheats_event_id']) if pd.notna(row['liveheats_event_id']) else '',
            str(row['liveheats_division_id']) if pd.notna(row['liveheats_division_id']) else '',
            str(row['division_name']) if pd.notna(row['division_name']) else ''
        )
        records.append(record)

    print(f"Inserting {len(records)} records...")
    cursor.executemany(insert_sql, records)
    print(f"[OK] {len(records)} records inserted/updated")
    return len(records)


def load_heat_results(cursor, df):
    """Load heat results data"""
    if df is None or df.empty:
        print("[WARNING] No heat results data to load")
        return 0

    print("\n" + "="*80)
    print("LOADING HEAT RESULTS DATA")
    print("="*80)

    insert_sql = """
    INSERT INTO PWA_IWT_HEAT_RESULTS (
        source, scraped_at, pwa_event_id, pwa_year, pwa_event_name,
        pwa_division_code, sex, heat_id, athlete_id, athlete_name,
        sail_number, place, result_total, win_by, needs,
        round, round_position, liveheats_event_id, liveheats_division_id
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        scraped_at = VALUES(scraped_at),
        athlete_name = VALUES(athlete_name),
        place = VALUES(place),
        result_total = VALUES(result_total),
        updated_at = CURRENT_TIMESTAMP
    """

    records = []
    for _, row in df.iterrows():
        try:
            scraped_at = pd.to_datetime(row['scraped_at']).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['scraped_at']) else None
        except:
            scraped_at = None

        record = (
            str(row['source']) if pd.notna(row['source']) else '',
            scraped_at,
            int(row['pwa_event_id']) if pd.notna(row['pwa_event_id']) else None,
            int(row['pwa_year']) if pd.notna(row['pwa_year']) else None,
            str(row['pwa_event_name']) if pd.notna(row['pwa_event_name']) else '',
            str(row['pwa_division_code']) if pd.notna(row['pwa_division_code']) else '',
            str(row['sex']) if pd.notna(row['sex']) else '',
            str(row['heat_id']) if pd.notna(row['heat_id']) else '',
            str(row['athlete_id']) if pd.notna(row['athlete_id']) else '',
            str(row['athlete_name']) if pd.notna(row['athlete_name']) else '',
            str(row['sail_number']) if pd.notna(row['sail_number']) else '',
            int(row['place']) if pd.notna(row['place']) else None,
            float(row['result_total']) if pd.notna(row['result_total']) else None,
            float(row['win_by']) if pd.notna(row['win_by']) else None,
            float(row['needs']) if pd.notna(row['needs']) else None,
            str(row['round']) if pd.notna(row['round']) else '',
            int(row['round_position']) if pd.notna(row['round_position']) else None,
            str(row['liveheats_event_id']) if pd.notna(row['liveheats_event_id']) else '',
            str(row['liveheats_division_id']) if pd.notna(row['liveheats_division_id']) else ''
        )
        records.append(record)

    print(f"Inserting {len(records)} records...")
    cursor.executemany(insert_sql, records)
    print(f"[OK] {len(records)} records inserted/updated")
    return len(records)


def load_heat_scores(cursor, df):
    """Load heat scores data"""
    if df is None or df.empty:
        print("[WARNING] No heat scores data to load")
        return 0

    print("\n" + "="*80)
    print("LOADING HEAT SCORES DATA")
    print("="*80)

    insert_sql = """
    INSERT INTO PWA_IWT_HEAT_SCORES (
        source, scraped_at, pwa_event_id, pwa_year, pwa_event_name,
        pwa_division_code, sex, heat_id, athlete_id, athlete_name,
        sail_number, score, type, counting, modified_total, modifier,
        total_wave, total_jump, total_points, liveheats_event_id, liveheats_division_id
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    records = []
    for _, row in df.iterrows():
        try:
            scraped_at = pd.to_datetime(row['scraped_at']).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['scraped_at']) else None
        except:
            scraped_at = None

        # Handle counting boolean
        counting_val = None
        if pd.notna(row['counting']):
            if isinstance(row['counting'], bool):
                counting_val = row['counting']
            elif str(row['counting']).lower() in ['true', '1', 'yes']:
                counting_val = True
            elif str(row['counting']).lower() in ['false', '0', 'no', '']:
                counting_val = False

        record = (
            str(row['source']) if pd.notna(row['source']) else '',
            scraped_at,
            int(row['pwa_event_id']) if pd.notna(row['pwa_event_id']) else None,
            int(row['pwa_year']) if pd.notna(row['pwa_year']) else None,
            str(row['pwa_event_name']) if pd.notna(row['pwa_event_name']) else '',
            str(row['pwa_division_code']) if pd.notna(row['pwa_division_code']) else '',
            str(row['sex']) if pd.notna(row['sex']) else '',
            str(row['heat_id']) if pd.notna(row['heat_id']) else '',
            str(row['athlete_id']) if pd.notna(row['athlete_id']) else '',
            str(row['athlete_name']) if pd.notna(row['athlete_name']) else '',
            str(row['sail_number']) if pd.notna(row['sail_number']) else '',
            float(row['score']) if pd.notna(row['score']) else None,
            str(row['type']) if pd.notna(row['type']) else '',
            counting_val,
            float(row['modified_total']) if pd.notna(row['modified_total']) else None,
            str(row['modifier']) if pd.notna(row['modifier']) else '',
            float(row['total_wave']) if pd.notna(row['total_wave']) else None,
            float(row['total_jump']) if pd.notna(row['total_jump']) else None,
            float(row['total_points']) if pd.notna(row['total_points']) else None,
            str(row['liveheats_event_id']) if pd.notna(row['liveheats_event_id']) else '',
            str(row['liveheats_division_id']) if pd.notna(row['liveheats_division_id']) else ''
        )
        records.append(record)

    # Insert in batches for scores (lots of data)
    batch_size = 500
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        cursor.executemany(insert_sql, batch)
        print(f"  Batch {i//batch_size + 1}: Inserted {len(batch)} records")

    print(f"[OK] {len(records)} total records inserted")
    return len(records)


def verify_data(cursor):
    """Verify loaded data"""
    print("\n" + "="*80)
    print("VERIFYING DATA")
    print("="*80)

    tables = [
        ('PWA_IWT_HEAT_PROGRESSION', 'Heat Progression'),
        ('PWA_IWT_HEAT_RESULTS', 'Heat Results'),
        ('PWA_IWT_HEAT_SCORES', 'Heat Scores')
    ]

    for table, name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{name}: {count} records")

        cursor.execute(f"SELECT source, COUNT(*) FROM {table} GROUP BY source")
        print(f"  By source:")
        for source, cnt in cursor.fetchall():
            print(f"    {source}: {cnt}")


def main():
    """Main execution"""
    print("="*80)
    print("LOAD ALL HEAT DATA INTO ORACLE DATABASE")
    print("="*80)

    try:
        # Get project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        processed_dir = os.path.join(project_root, 'data', 'processed')

        # Load CSVs
        prog_df = load_csv(os.path.join(processed_dir, 'heat_progression_merged.csv'), 'Heat Progression')
        results_df = load_csv(os.path.join(processed_dir, 'heat_results_merged.csv'), 'Heat Results')
        scores_df = load_csv(os.path.join(processed_dir, 'heat_scores_merged.csv'), 'Heat Scores')

        # Connect to database
        print("\nConnecting to Oracle MySQL Heatwave...")
        conn = get_connection()
        cursor = conn.cursor()
        print("[OK] Connected to database")

        # Load data
        total = 0
        total += load_heat_progression(cursor, prog_df)
        total += load_heat_results(cursor, results_df)
        total += load_heat_scores(cursor, scores_df)

        # Commit
        print("\nCommitting transaction...")
        conn.commit()
        print("[OK] Transaction committed")

        # Verify
        verify_data(cursor)

        print("\n" + "="*80)
        print(f"[SUCCESS] {total} total heat records loaded successfully!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] Failed to load heat data: {e}")
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
