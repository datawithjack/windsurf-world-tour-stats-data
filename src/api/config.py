"""
Configuration Management for Windsurf World Tour Stats API

Automatically detects environment (local vs production) and loads appropriate settings.
- Local: Uses SSH tunnel (localhost:3306)
- Production: Direct connection to MySQL Heatwave (10.0.151.92:3306)
"""

import os
from typing import Literal, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment auto-detection

    Environment Detection:
    - If DB_HOST is 'localhost' or '127.0.0.1': Assumes local development with SSH tunnel
    - Otherwise: Assumes production with direct DB connection
    """

    # Application Environment
    API_ENV: Literal["development", "production"] = "development"

    # API Settings
    API_TITLE: str = "Windsurf World Tour Stats API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for PWA and IWT windsurf wave competition data (2016-2025)"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS Settings
    CORS_ENABLED: bool = True
    CORS_ORIGINS: List[str] = ["*"]  # In production, restrict to specific frontend domains

    # Database Connection
    DB_HOST: str = "localhost"  # Default to localhost (SSH tunnel for local dev)
    DB_PORT: int = 3306
    DB_NAME: str = "jfa_heatwave_db"
    DB_USER: str
    DB_PASSWORD: str

    # Database Pool Settings
    DB_POOL_NAME: str = "windsurf_pool"
    DB_POOL_SIZE: int = 2  # Reduced for local dev (SSH tunnel can be slow)
    DB_POOL_RESET_SESSION: bool = True
    DB_POOL_TIMEOUT: int = 30       # Seconds to wait for pool connection (prevents infinite hangs)
    DB_POOL_RECYCLE: int = 3600     # Recycle connections after 1 hour (prevents stale connections)
    DB_POOL_PRE_PING: bool = True   # Validate connection before use (detects stale connections)

    # Logging
    LOG_LEVEL: str = "info"

    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """
        Check if running in production environment

        Returns True if:
        - API_ENV is explicitly set to 'production', OR
        - DB_HOST is not localhost/127.0.0.1 (assumes direct DB connection)
        """
        if self.API_ENV == "production":
            return True

        # Auto-detect based on DB host
        return self.DB_HOST not in ("localhost", "127.0.0.1")

    @property
    def database_url(self) -> str:
        """
        Generate database connection URL for logging (without password)
        """
        return f"mysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_db_config(self) -> tuple[dict, dict]:
        """
        Get database configuration dictionaries for mysql.connector

        Returns:
            tuple[dict, dict]: (connection parameters, pool parameters)
        """
        # Connection parameters
        conn_config = {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "connect_timeout": 10,  # 10 seconds is enough for SSH tunnel
            "autocommit": True
        }

        # Pool-specific parameters
        pool_config = {
            "pool_name": self.DB_POOL_NAME,
            "pool_size": self.DB_POOL_SIZE,
            "pool_reset_session": self.DB_POOL_RESET_SESSION,
        }

        return conn_config, pool_config


# Global settings instance
# Load from .env (or .env.production in production)
settings = Settings()


# Log configuration on import (without sensitive data)
if __name__ != "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"API Configuration Loaded:")
    logger.info(f"  Environment: {'PRODUCTION' if settings.is_production else 'DEVELOPMENT'}")
    logger.info(f"  Database: {settings.database_url}")
    logger.info(f"  CORS Enabled: {settings.CORS_ENABLED}")
