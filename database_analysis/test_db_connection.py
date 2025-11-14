"""
Test database connection via SSH tunnel
Supports both pyodbc (with MySQL ODBC driver) and mysql-connector-python
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_connection_mysql_connector():
    """Test connection using mysql-connector-python"""
    try:
        import mysql.connector
    except ImportError:
        return None

    # Get connection parameters from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', '3306'))
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')

    if not all([db_name, db_user, db_password]):
        print("[INFO] DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD not all set in .env")
        return None

    print(f"Connection parameters:")
    print(f"  Host: {db_host}")
    print(f"  Port: {db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    print()

    # Try configured host first
    try:
        print(f"Attempting to connect to {db_host}:{db_port}...")
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=30
        )
        print("[OK] Successfully connected to database!")
        print()
        return conn
    except Exception as e:
        print(f"[WARNING] Connection to {db_host} failed: {e}")

        # If not localhost, try localhost (SSH tunnel)
        if db_host != 'localhost':
            print()
            print("Trying localhost (SSH tunnel)...")
            try:
                conn = mysql.connector.connect(
                    host='localhost',
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password,
                    connect_timeout=30
                )
                print("[OK] Successfully connected via localhost (SSH tunnel)!")
                print()
                return conn
            except Exception as e2:
                print(f"[ERROR] Connection to localhost also failed: {e2}")
                return None
        return None


def test_connection_pyodbc():
    """Test connection using pyodbc"""
    try:
        import pyodbc
    except ImportError:
        return None

    connection_string = os.getenv('ORACLE_CONNECTION_STRING')

    if not connection_string or connection_string == 'your_connection_string_here':
        print("[INFO] ORACLE_CONNECTION_STRING not properly set in .env file")
        return None

    try:
        print("Attempting to connect using pyodbc...")
        conn = pyodbc.connect(connection_string)
        print("[OK] Successfully connected to database!")
        print()
        return conn
    except Exception as e:
        print(f"[ERROR] pyodbc connection failed: {e}")
        return None


def test_connection():
    """Test connection to Oracle MySQL Heatwave database via SSH tunnel"""
    print("="*80)
    print("TESTING DATABASE CONNECTION VIA SSH TUNNEL")
    print("="*80)
    print()

    # Try mysql-connector-python first (recommended for MySQL)
    conn = test_connection_mysql_connector()

    # If that fails, try pyodbc
    if conn is None:
        print()
        conn = test_connection_pyodbc()

    if conn is None:
        print()
        print("="*80)
        print("[ERROR] Could not connect using any available method")
        print()
        print("For MySQL databases, please set in .env:")
        print("  DB_HOST=localhost (if using SSH tunnel)")
        print("  DB_PORT=3306 (or your tunneled port)")
        print("  DB_NAME=your_database_name")
        print("  DB_USER=your_username")
        print("  DB_PASSWORD=your_password")
        print()
        print("Or install mysql-connector-python:")
        print("  pip install mysql-connector-python")
        print("="*80)
        return False

    try:

        # Test query
        cursor = conn.cursor()

        # Check if we can query the database
        print("Testing database query...")
        cursor.execute("SELECT DATABASE() as current_db, VERSION() as version")
        result = cursor.fetchone()

        print("[OK] Query successful!")
        print(f"  Current Database: {result[0]}")
        print(f"  MySQL Version: {result[1]}")
        print()

        # Check if PWA_IWT_EVENTS table exists
        print("Checking for PWA_IWT_EVENTS table...")
        try:
            cursor.execute("SHOW TABLES LIKE 'PWA_IWT_EVENTS'")
            table_exists = cursor.fetchone()

            if table_exists:
                print("[OK] PWA_IWT_EVENTS table exists")

                # Get row count
                cursor.execute("SELECT COUNT(*) FROM PWA_IWT_EVENTS")
                count = cursor.fetchone()[0]
                print(f"  Current row count: {count}")

                # Show table structure
                print("\n  Table structure:")
                cursor.execute("DESCRIBE PWA_IWT_EVENTS")
                for row in cursor.fetchall():
                    print(f"    {row[0]:25} {row[1]:20} {row[2]:5} {row[3]:5}")
            else:
                print("[WARNING] PWA_IWT_EVENTS table does not exist")
                print("  You may need to create the table first")
        except Exception as e:
            print(f"[WARNING] Could not check table: {e}")

        print()

        # Close connection
        cursor.close()
        conn.close()
        print("[OK] Connection closed")
        print()
        print("="*80)
        print("CONNECTION TEST SUCCESSFUL!")
        print("="*80)
        return True

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Common issues:")
        print("  1. SSH tunnel is not running")
        print("  2. Connection parameters are incorrect")
        print("  3. Database credentials are invalid")
        print("  4. Firewall blocking connection")
        print()
        return False


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
