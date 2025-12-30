"""
Database Connection Management

Provides connection pooling and database utilities for the FastAPI application.
Works with both local development (SSH tunnel) and production (direct connection).
"""

import logging
import time
from functools import wraps
from typing import Generator, Optional
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

from .config import settings

logger = logging.getLogger(__name__)


def retry_on_db_error(max_attempts=3, base_delay=0.5):
    """
    Retry decorator for database operations with exponential backoff

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        base_delay: Base delay in seconds (default: 0.5s)

    Exponential backoff: 0.5s, 1s, 2s
    Retries only on connection errors, not logic errors
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Error as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Database error on attempt {attempt + 1}/{max_attempts}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"Database error after {max_attempts} attempts: {e}")
                        raise

            raise last_exception

        return wrapper
    return decorator


class DatabaseManager:
    """
    Manages MySQL connection pool and provides database access
    """

    def __init__(self):
        """Initialize database manager (lazy initialization)"""
        self._pool: Optional[MySQLConnectionPool] = None
        self._pool_initialized = False
        self._initialization_error: Optional[str] = None

    def _initialize_pool(self):
        """
        Initialize MySQL connection pool (lazy initialization)

        Creates a connection pool with settings from config.
        Logs connection details (without password) for debugging.

        This is called on first use, not on module import, allowing
        the app to start even if the database is not accessible.
        """
        if self._pool_initialized:
            return

        try:
            conn_config, pool_config = settings.get_db_config()

            # Create connection pool with both connection and pool settings
            pool_args = {
                **pool_config,
                **conn_config
            }

            self._pool = mysql.connector.pooling.MySQLConnectionPool(**pool_args)

            # Mark as initialized BEFORE testing connection to avoid recursion
            self._pool_initialized = True
            self._initialization_error = None

            # Test connection
            conn = self._pool.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logger.info(
                    f"Database connection pool initialized successfully "
                    f"({settings.DB_POOL_SIZE} connections to {settings.database_url})"
                )
            finally:
                if conn.is_connected():
                    conn.close()

        except Error as e:
            error_msg = f"Failed to initialize database connection pool: {e}"
            logger.error(error_msg)
            self._initialization_error = str(e)
            self._pool_initialized = True  # Mark as attempted
            raise

    @contextmanager
    @retry_on_db_error(max_attempts=3, base_delay=0.5)
    def get_connection(self):
        """
        Get a connection from the pool (context manager) with automatic retry

        Retries up to 3 times with exponential backoff on connection errors.

        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
                ...

        Yields:
            mysql.connector.connection: Database connection

        Raises:
            Error: If connection cannot be established after retries
        """
        # Initialize pool on first use
        if not self._pool_initialized:
            self._initialize_pool()

        connection = None
        try:
            connection = self._pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False):
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string (use %s for parameters)
            params: Query parameters tuple
            fetch_one: If True, return single row; if False, return all rows

        Returns:
            dict | list[dict] | None: Query results as dictionary/-ies

        Raises:
            Error: If query execution fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())

                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()

                return result
            finally:
                cursor.close()

    def execute_count(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute a COUNT query and return the count

        Args:
            query: SQL COUNT query string
            params: Query parameters tuple

        Returns:
            int: Count result

        Raises:
            Error: If query execution fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or ())
                result = cursor.fetchone()
                return result[0] if result else 0
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """
        Test database connection

        Pool will be initialized automatically by get_connection if needed.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # get_connection() handles pool initialization automatically
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return True
        except Error as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# FastAPI Dependency
def get_db() -> Generator[DatabaseManager, None, None]:
    """
    FastAPI dependency for database access

    Usage in routes:
        @router.get("/endpoint")
        def endpoint(db: DatabaseManager = Depends(get_db)):
            results = db.execute_query("SELECT * FROM table")
            ...

    Yields:
        DatabaseManager: Database manager instance
    """
    yield db_manager


# Health check function
def check_database_health() -> dict:
    """
    Check database health for health endpoint

    Returns:
        dict: Health status with connection info
    """
    try:
        is_connected = db_manager.test_connection()
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "database": settings.database_url,
            "environment": "production" if settings.is_production else "development"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": settings.database_url
        }
