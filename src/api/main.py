"""
Windsurf World Tour Stats API

FastAPI application for serving PWA and IWT windsurf wave competition data.

Run locally:
    uvicorn src.api.main:app --reload

Run in production:
    gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import check_database_health
from .models import HealthResponse
from .routes import events, athletes, stats, head_to_head

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {
            "url": "https://windsurf-world-tour-stats-api.duckdns.org",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)


# ============================================================================
# Middleware
# ============================================================================

if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.CORS_ORIGINS}")


# ============================================================================
# Event Handlers
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run on application startup

    Logs configuration. Database initialized lazily on first request.
    """
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"Environment: {'PRODUCTION' if settings.is_production else 'DEVELOPMENT'}")
    logger.info(f"Database: {settings.database_url}")
    logger.info("Database will be initialized on first request (lazy loading)")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown

    Cleanup and logging.
    """
    logger.info(f"Shutting down {settings.API_TITLE}")


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get(
    "/",
    summary="API Information",
    description="Get basic API information and available endpoints"
)
async def root():
    """
    Root endpoint - API information

    Returns basic API metadata and links to documentation.
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "environment": "production" if settings.is_production else "development",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "events": "/api/v1/events",
            "athletes": "/api/v1/athletes",
            "stats": "/api/v1/stats",
            "head_to_head": "/api/v1/events/{event_id}/head-to-head",
            "health": "/health"
        }
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check API and database health status"
)
async def health_check():
    """
    Health check endpoint

    Returns API status and database connectivity.
    Used by monitoring systems and load balancers.
    """
    db_health = check_database_health()

    overall_status = "healthy" if db_health["status"] == "healthy" else "unhealthy"

    return HealthResponse(
        status=overall_status,
        api_version=settings.API_VERSION,
        database=db_health
    )


# ============================================================================
# API Routes
# ============================================================================

# Include routers with /api/v1 prefix
app.include_router(events.router, prefix="/api/v1")
app.include_router(athletes.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(head_to_head.router, prefix="/api/v1")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """
    Handle 404 Not Found errors

    Returns JSON response for any 404 error.
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "NotFound",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """
    Handle 500 Internal Server errors

    Returns JSON response for server errors.
    """
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An internal server error occurred",
            "detail": str(exc) if not settings.is_production else None
        }
    )


# ============================================================================
# Run with uvicorn (for development only)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
