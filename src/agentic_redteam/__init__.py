"""
Agentic RedTeam Radar: Automated Security Testing for AI Agents

Open-source implementation of an agent-centric red-teaming scanner 
inspired by Cloud Security Alliance guidance.
"""

__version__ = "0.1.0"
__author__ = "Daniel Schmidt"
__email__ = "daniel@terragonlabs.com"

from .scanner import RadarScanner
from .agent import Agent, create_agent, AgentType
from .config import RadarConfig
from .results import ScanResult, Vulnerability

__all__ = [
    "RadarScanner", 
    "Agent", 
    "create_agent",
    "AgentType",
    "RadarConfig",
    "ScanResult",
    "Vulnerability",
    "__version__"
]