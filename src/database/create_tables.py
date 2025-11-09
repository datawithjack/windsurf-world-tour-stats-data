"""
Create Oracle database tables for PWA/IWT windsurf event data
"""
import mysql.connector
import os
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


def create_pwa_iwt_events_table(cursor):
    """
    Create PWA_IWT_EVENTS table for PWA event metadata

    This table stores event information scraped from PWA World Tour website
    """
    drop_sql = "DROP TABLE IF EXISTS PWA_IWT_EVENTS"

    create_sql = """
    CREATE TABLE PWA_IWT_EVENTS (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        scraped_at DATETIME NOT NULL,
        year INT NOT NULL,
        event_id INT NOT NULL,
        event_name VARCHAR(255) NOT NULL,
        event_url TEXT,
        event_date VARCHAR(100),
        start_date DATE,
        end_date DATE,
        day_window INT,
        event_section VARCHAR(100),
        event_status INT,
        competition_state INT,
        has_wave_discipline BOOLEAN DEFAULT FALSE,
        all_disciplines VARCHAR(255),
        country_flag VARCHAR(100),
        country_code VARCHAR(10),
        stars INT,
        event_image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_source (source),
        INDEX idx_event_id (event_id),
        INDEX idx_year (year),
        INDEX idx_country_code (country_code),
        INDEX idx_has_wave (has_wave_discipline),
        UNIQUE KEY unique_event (source, event_id)
    )
    """

    print("Dropping PWA_IWT_EVENTS table if exists...")
    cursor.execute(drop_sql)

    print("Creating PWA_IWT_EVENTS table...")
    cursor.execute(create_sql)

    print("[OK] PWA_IWT_EVENTS table created successfully")


def create_pwa_iwt_results_table(cursor):
    """
    Create PWA_IWT_RESULTS table for wave event results

    This table stores athlete placements/results from PWA and Live Heats sources
    """
    drop_sql = "DROP TABLE IF EXISTS PWA_IWT_RESULTS"

    create_sql = """
    CREATE TABLE PWA_IWT_RESULTS (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        scraped_at DATETIME NOT NULL,
        event_id INT NOT NULL,
        year INT NOT NULL,
        event_name VARCHAR(255) NOT NULL,
        division_label VARCHAR(100) NOT NULL,
        division_code VARCHAR(50),
        sex VARCHAR(20),
        place VARCHAR(10) NOT NULL,
        athlete_name VARCHAR(255),
        sail_number VARCHAR(50),
        athlete_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_source (source),
        INDEX idx_event_id (event_id),
        INDEX idx_year (year),
        INDEX idx_sex (sex),
        INDEX idx_athlete_id (athlete_id),
        INDEX idx_athlete_name (athlete_name),
        UNIQUE KEY unique_result (source, event_id, division_code, athlete_id, place)
    )
    """

    print("Dropping PWA_IWT_RESULTS table if exists...")
    cursor.execute(drop_sql)

    print("Creating PWA_IWT_RESULTS table...")
    cursor.execute(create_sql)

    print("[OK] PWA_IWT_RESULTS table created successfully")


def create_pwa_iwt_heat_progression_table(cursor):
    """Create PWA_IWT_HEAT_PROGRESSION table"""
    drop_sql = "DROP TABLE IF EXISTS PWA_IWT_HEAT_PROGRESSION"

    create_sql = """
    CREATE TABLE PWA_IWT_HEAT_PROGRESSION (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        scraped_at DATETIME,
        pwa_event_id INT NOT NULL,
        pwa_year INT,
        pwa_event_name VARCHAR(255),
        pwa_division_code VARCHAR(50),
        sex VARCHAR(20),
        round_name VARCHAR(100),
        round_order INT,
        heat_id VARCHAR(100) NOT NULL,
        heat_order INT,
        total_winners_progressing INT,
        winners_progressing_to_round_order INT,
        total_losers_progressing INT,
        losers_progressing_to_round_order INT,
        elimination_name TEXT,
        liveheats_event_id VARCHAR(50),
        liveheats_division_id VARCHAR(50),
        division_name VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_source (source),
        INDEX idx_event (pwa_event_id),
        INDEX idx_heat (heat_id),
        UNIQUE KEY unique_heat (source, heat_id)
    )
    """

    print("Dropping PWA_IWT_HEAT_PROGRESSION table if exists...")
    cursor.execute(drop_sql)
    print("Creating PWA_IWT_HEAT_PROGRESSION table...")
    cursor.execute(create_sql)
    print("[OK] PWA_IWT_HEAT_PROGRESSION table created successfully")


def create_pwa_iwt_heat_results_table(cursor):
    """Create PWA_IWT_HEAT_RESULTS table"""
    drop_sql = "DROP TABLE IF EXISTS PWA_IWT_HEAT_RESULTS"

    create_sql = """
    CREATE TABLE PWA_IWT_HEAT_RESULTS (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        scraped_at DATETIME,
        pwa_event_id INT NOT NULL,
        pwa_year INT,
        pwa_event_name VARCHAR(255),
        pwa_division_code VARCHAR(50),
        sex VARCHAR(20),
        heat_id VARCHAR(100) NOT NULL,
        athlete_id VARCHAR(100),
        athlete_name VARCHAR(255),
        sail_number VARCHAR(50),
        place INT,
        result_total DECIMAL(10,2),
        win_by DECIMAL(10,2),
        needs DECIMAL(10,2),
        round VARCHAR(100),
        round_position INT,
        liveheats_event_id VARCHAR(50),
        liveheats_division_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_source (source),
        INDEX idx_event (pwa_event_id),
        INDEX idx_heat (heat_id),
        INDEX idx_athlete (athlete_id),
        UNIQUE KEY unique_heat_athlete (source, heat_id, athlete_id)
    )
    """

    print("Dropping PWA_IWT_HEAT_RESULTS table if exists...")
    cursor.execute(drop_sql)
    print("Creating PWA_IWT_HEAT_RESULTS table...")
    cursor.execute(create_sql)
    print("[OK] PWA_IWT_HEAT_RESULTS table created successfully")


def create_pwa_iwt_heat_scores_table(cursor):
    """Create PWA_IWT_HEAT_SCORES table"""
    drop_sql = "DROP TABLE IF EXISTS PWA_IWT_HEAT_SCORES"

    create_sql = """
    CREATE TABLE PWA_IWT_HEAT_SCORES (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source VARCHAR(50) NOT NULL,
        scraped_at DATETIME,
        pwa_event_id INT NOT NULL,
        pwa_year INT,
        pwa_event_name VARCHAR(255),
        pwa_division_code VARCHAR(50),
        sex VARCHAR(20),
        heat_id VARCHAR(100) NOT NULL,
        athlete_id VARCHAR(100),
        athlete_name VARCHAR(255),
        sail_number VARCHAR(50),
        score DECIMAL(10,2),
        type VARCHAR(20),
        counting BOOLEAN,
        modified_total DECIMAL(10,2),
        modifier TEXT,
        total_wave DECIMAL(10,2),
        total_jump DECIMAL(10,2),
        total_points DECIMAL(10,2),
        liveheats_event_id VARCHAR(50),
        liveheats_division_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_source (source),
        INDEX idx_event (pwa_event_id),
        INDEX idx_heat (heat_id),
        INDEX idx_athlete (athlete_id),
        INDEX idx_counting (counting)
    )
    """

    print("Dropping PWA_IWT_HEAT_SCORES table if exists...")
    cursor.execute(drop_sql)
    print("Creating PWA_IWT_HEAT_SCORES table...")
    cursor.execute(create_sql)
    print("[OK] PWA_IWT_HEAT_SCORES table created successfully")


def main():
    """Main execution"""
    print("="*80)
    print("ORACLE DATABASE TABLE CREATION")
    print("="*80)
    print()

    try:
        # Connect to database
        print("Connecting to Oracle MySQL Heatwave...")
        conn = get_connection()
        cursor = conn.cursor()
        print("[OK] Connected to database")
        print()

        # Create tables
        create_pwa_iwt_events_table(cursor)
        print()
        create_pwa_iwt_results_table(cursor)
        print()
        create_pwa_iwt_heat_progression_table(cursor)
        print()
        create_pwa_iwt_heat_results_table(cursor)
        print()
        create_pwa_iwt_heat_scores_table(cursor)

        # Commit changes
        conn.commit()
        print()
        print("="*80)
        print("[OK] All tables created successfully!")
        print("="*80)

    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")


if __name__ == "__main__":
    main()
