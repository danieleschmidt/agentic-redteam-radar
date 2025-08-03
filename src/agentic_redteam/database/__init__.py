"""
Database layer for Agentic RedTeam Radar.

Provides database connectivity, models, and data access patterns
for persistent storage of scan results and configurations.
"""

from .connection import DatabaseManager, get_db_connection
from .models import ScanSession, Vulnerability, AttackPattern, AgentConfig
from .repositories import (
    ScanSessionRepository,
    VulnerabilityRepository, 
    AttackPatternRepository,
    AgentConfigRepository
)

__all__ = [
    "DatabaseManager",
    "get_db_connection",
    "ScanSession",
    "Vulnerability",
    "AttackPattern", 
    "AgentConfig",
    "ScanSessionRepository",
    "VulnerabilityRepository",
    "AttackPatternRepository",
    "AgentConfigRepository"
]