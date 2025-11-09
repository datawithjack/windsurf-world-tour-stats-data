"""
Create athlete database tables in MySQL.

Creates two tables:
1. ATHLETES - Master athlete table with unified IDs
2. ATHLETE_SOURCE_IDS - Link table mapping unified IDs to source-specific IDs
"""

import mysql.connector
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

def create_athletes_table(cursor):
    """
    Create ATHLETES table.

    This table stores the master athlete list with profiles from both PWA and LiveHeats.
    """
    print("\nCreating ATHLETES table...")

    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS ATHLETES")

    # Create table
    create_table_sql = """
    CREATE TABLE ATHLETES (
        id INT PRIMARY KEY AUTO_INCREMENT,
        primary_name VARCHAR(255) NOT NULL,
        pwa_name VARCHAR(255),
        liveheats_name VARCHAR(255),
        match_score INT,
        match_stage VARCHAR(50),
        year_of_birth INT,
        nationality VARCHAR(100),
        pwa_athlete_id VARCHAR(50),
        pwa_sail_number VARCHAR(50),
        pwa_profile_url TEXT,
        pwa_sponsors TEXT,
        pwa_nationality VARCHAR(100),
        pwa_year_of_birth INT,
        liveheats_athlete_id VARCHAR(50),
        liveheats_image_url TEXT,
        liveheats_dob DATE,
        liveheats_nationality VARCHAR(100),
        liveheats_year_of_birth INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_primary_name (primary_name),
        INDEX idx_pwa_name (pwa_name),
        INDEX idx_liveheats_name (liveheats_name),
        INDEX idx_nationality (nationality),
        INDEX idx_year_of_birth (year_of_birth),
        INDEX idx_pwa_athlete_id (pwa_athlete_id),
        INDEX idx_liveheats_athlete_id (liveheats_athlete_id),
        INDEX idx_pwa_sail_number (pwa_sail_number)
    )
    """

    cursor.execute(create_table_sql)
    print("  [OK] ATHLETES table created successfully")

def create_athlete_source_ids_table(cursor):
    """
    Create ATHLETE_SOURCE_IDS table.

    This is a link table that maps unified athlete IDs to source-specific IDs
    (PWA athlete IDs, LiveHeats athlete IDs, sail numbers, etc).
    """
    print("\nCreating ATHLETE_SOURCE_IDS table...")

    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS ATHLETE_SOURCE_IDS")

    # Create table
    create_table_sql = """
    CREATE TABLE ATHLETE_SOURCE_IDS (
        id INT PRIMARY KEY AUTO_INCREMENT,
        athlete_id INT NOT NULL,
        source VARCHAR(50) NOT NULL,
        source_id VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (athlete_id) REFERENCES ATHLETES(id) ON DELETE CASCADE,
        INDEX idx_athlete_id (athlete_id),
        INDEX idx_source (source),
        INDEX idx_source_id (source_id),
        UNIQUE KEY unique_source_id (source, source_id)
    )
    """

    cursor.execute(create_table_sql)
    print("  [OK] ATHLETE_SOURCE_IDS table created successfully")

def verify_tables(cursor):
    """
    Verify that tables were created successfully.
    """
    print("\nVerifying tables...")

    # Check ATHLETES table
    cursor.execute("SHOW TABLES LIKE 'ATHLETES'")
    if cursor.fetchone():
        cursor.execute("DESCRIBE ATHLETES")
        columns = cursor.fetchall()
        print(f"  [OK] ATHLETES table: {len(columns)} columns")
    else:
        print("  [ERROR] ATHLETES table not found!")

    # Check ATHLETE_SOURCE_IDS table
    cursor.execute("SHOW TABLES LIKE 'ATHLETE_SOURCE_IDS'")
    if cursor.fetchone():
        cursor.execute("DESCRIBE ATHLETE_SOURCE_IDS")
        columns = cursor.fetchall()
        print(f"  [OK] ATHLETE_SOURCE_IDS table: {len(columns)} columns")
    else:
        print("  [ERROR] ATHLETE_SOURCE_IDS table not found!")

def main():
    """Main execution function"""
    print("Creating Athlete Database Tables")
    print("=" * 50)

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print("  [OK] Connected successfully")

        # Create tables
        create_athletes_table(cursor)
        create_athlete_source_ids_table(cursor)

        # Commit changes
        conn.commit()
        print("\n[OK] Changes committed to database")

        # Verify tables
        verify_tables(cursor)

        print("\n" + "=" * 50)
        print("SUCCESS: Athlete tables created successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Run scraping scripts to collect athlete data")
        print("2. Run matching script to link athletes across sources")
        print("3. Run merge script to create final athlete lists")
        print("4. Run load_athletes.py to load data into these tables")

    except mysql.connector.Error as err:
        print(f"\n[ERROR] DATABASE ERROR: {err}")
        return

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        return

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    main()
