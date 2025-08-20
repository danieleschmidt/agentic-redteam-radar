"""
Reporting module for Agentic RedTeam Radar.

Provides various report formats including HTML, PDF, and interactive dashboards.
"""

from .html_generator import generate_html_report, HTMLReportConfig
from .report_base import ReportGenerator, ReportConfig

__all__ = [
    "generate_html_report",
    "HTMLReportConfig", 
    "ReportGenerator",
    "ReportConfig"
]