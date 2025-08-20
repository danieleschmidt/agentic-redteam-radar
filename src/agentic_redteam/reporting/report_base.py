"""
Base classes for report generation.

Provides common functionality for all report generators.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from ..results import ScanResult


@dataclass 
class ReportConfig:
    """Base configuration for report generation."""
    title: str = "Security Scan Report"
    author: str = "Agentic RedTeam Radar"
    include_executive_summary: bool = True
    include_technical_details: bool = True
    include_remediation: bool = True
    company_name: Optional[str] = None
    company_logo: Optional[str] = None


class ReportGenerator(ABC):
    """Abstract base class for report generators."""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize report generator with configuration."""
        self.config = config or ReportConfig()
    
    @abstractmethod
    def generate(self, scan_result: ScanResult) -> str:
        """
        Generate report from scan results.
        
        Args:
            scan_result: Results from security scan
            
        Returns:
            Generated report content
        """
        pass
    
    def save_to_file(self, content: str, filepath: str) -> None:
        """Save report content to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _get_executive_summary(self, scan_result: ScanResult) -> Dict[str, Any]:
        """Generate executive summary data from scan results."""
        total_vulns = len(scan_result.vulnerabilities)
        severity_counts = self._count_by_severity(scan_result)
        
        # Calculate risk level
        if severity_counts.get('critical', 0) > 0:
            risk_level = "Critical"
        elif severity_counts.get('high', 0) > 2:
            risk_level = "High" 
        elif severity_counts.get('medium', 0) > 5:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return {
            'total_vulnerabilities': total_vulns,
            'risk_level': risk_level,
            'scan_duration': scan_result.scan_duration,
            'patterns_executed': scan_result.patterns_executed,
            'severity_breakdown': severity_counts
        }
    
    def _count_by_severity(self, scan_result: ScanResult) -> Dict[str, int]:
        """Count vulnerabilities by severity level."""
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        
        for vuln in scan_result.vulnerabilities:
            severity = vuln.severity.lower() if hasattr(vuln, 'severity') else 'info'
            if severity in counts:
                counts[severity] += 1
                
        return counts
    
    def _count_by_category(self, scan_result: ScanResult) -> Dict[str, int]:
        """Count vulnerabilities by category."""
        counts = {}
        
        for vuln in scan_result.vulnerabilities:
            category = vuln.category if hasattr(vuln, 'category') else 'other'
            counts[category] = counts.get(category, 0) + 1
            
        return counts