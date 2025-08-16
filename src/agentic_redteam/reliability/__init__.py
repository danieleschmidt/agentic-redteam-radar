"""
Reliability and resilience components for Agentic RedTeam Radar.

This module provides advanced reliability features including:
- Automatic failover mechanisms
- Data consistency checks
- System health monitoring
- Graceful degradation
- Recovery procedures
"""

try:
    from .health_monitor import HealthMonitor, HealthCheck, SystemHealth
except ImportError:
    from .simple_health_monitor import SimpleHealthMonitor as HealthMonitor, HealthCheck, SystemHealth
from .failover import FailoverManager, FailoverStrategy
from .data_integrity import DataIntegrityChecker, IntegrityViolation
from .graceful_degradation import DegradationManager, DegradationLevel

__all__ = [
    "HealthMonitor",
    "HealthCheck", 
    "SystemHealth",
    "FailoverManager",
    "FailoverStrategy",
    "DataIntegrityChecker",
    "IntegrityViolation",
    "DegradationManager",
    "DegradationLevel"
]