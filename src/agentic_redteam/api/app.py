"""
FastAPI application for Agentic RedTeam Radar.

Provides REST API for remote scanning capabilities with authentication,
rate limiting, and comprehensive API documentation.
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ..utils.logger import setup_logger
from ..config import RadarConfig
from ..database import init_database
from ..cache import init_cache
from .routes import register_routes
from .middleware import RateLimitMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger = setup_logger("agentic_redteam.api")
    logger.info("Starting Agentic RedTeam Radar API server")
    
    # Initialize database
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/radar_api.db")
    init_database(database_url)
    logger.info(f"Database initialized: {database_url}")
    
    # Initialize cache
    redis_url = os.getenv("REDIS_URL", "memory://")
    init_cache(redis_url)
    logger.info(f"Cache initialized: {redis_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agentic RedTeam Radar API server")


def create_app(config: Optional[RadarConfig] = None) -> FastAPI:
    """
    Create FastAPI application with full configuration.
    
    Args:
        config: Optional radar configuration
        
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="Agentic RedTeam Radar API",
        description="REST API for AI agent security testing and vulnerability scanning",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Store config in app state
    app.state.radar_config = config or RadarConfig()
    
    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add rate limiting middleware
    rate_limit = int(os.getenv("API_RATE_LIMIT", "60"))
    app.add_middleware(RateLimitMiddleware, calls=rate_limit, period=60)
    
    # Add CORS middleware
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for production
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        trusted_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    
    # Register API routes
    register_routes(app)
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger = logging.getLogger("agentic_redteam.api")
        logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "service": "agentic-redteam-radar-api"
        }
    
    # Metrics endpoint (if enabled)
    if os.getenv("ENABLE_METRICS", "false").lower() == "true":
        @app.get("/metrics", tags=["Monitoring"])
        async def metrics():
            """Prometheus metrics endpoint."""
            from ..monitoring.telemetry import get_prometheus_metrics
            return get_prometheus_metrics()
    
    return app


# Create default app instance
app = create_app()


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    workers: int = 1
):
    """
    Run the API server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
        workers: Number of worker processes
    """
    logger = setup_logger("agentic_redteam.api.server")
    logger.info(f"Starting API server on {host}:{port}")
    
    if reload:
        # Development mode - single worker with reload
        uvicorn.run(
            "agentic_redteam.api.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    else:
        # Production mode - multiple workers
        uvicorn.run(
            "agentic_redteam.api.app:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info"
        )


if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("DEV_MODE", "false").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))
    
    run_server(host, port, reload, workers)