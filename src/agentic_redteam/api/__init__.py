"""
API layer for Agentic RedTeam Radar.

Provides REST API endpoints for remote scanning, result management,
and integration with external systems.
"""

from .app import create_app, app
from .routes import register_routes
from .models import ScanRequest, ScanResponse, AgentConfigRequest

__all__ = [
    "create_app",
    "app", 
    "register_routes",
    "ScanRequest",
    "ScanResponse",
    "AgentConfigRequest"
]