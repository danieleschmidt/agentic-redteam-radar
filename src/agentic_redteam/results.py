"""
Result data structures for Agentic RedTeam Radar.

Defines classes for storing and managing security scan results,
vulnerabilities, and related metadata.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

from .attacks.base import AttackResult, AttackSeverity, AttackCategory


@dataclass
class Vulnerability:
    """
    Represents a security vulnerability found in an agent.
    """
    name: str
    description: str
    severity: AttackSeverity
    category: AttackCategory
    evidence: List[str] = field(default_factory=list)
    remediation: str = ""
    cwe_id: Optional[int] = None
    cvss_score: Optional[float] = None
    attack_payload: str = ""
    agent_response: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
            "cvss_score": self.cvss_score,
            "attack_payload": self.attack_payload,
            "agent_response": self.agent_response,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


@dataclass
class ScanStatistics:
    """
    Statistical information about a security scan.
    """
    total_patterns: int = 0
    total_payloads: int = 0
    vulnerabilities_by_severity: Dict[str, int] = field(default_factory=dict)
    vulnerabilities_by_category: Dict[str, int] = field(default_factory=dict)
    scan_duration: float = 0.0
    success_rate: float = 0.0
    
    def __post_init__(self):
        """Initialize severity and category counters."""
        if not self.vulnerabilities_by_severity:
            self.vulnerabilities_by_severity = {
                severity.value: 0 for severity in AttackSeverity
            }
        if not self.vulnerabilities_by_category:
            self.vulnerabilities_by_category = {
                category.value: 0 for category in AttackCategory
            }
    
    def add_vulnerability(self, vulnerability: Vulnerability) -> None:
        """Add a vulnerability to the statistics."""
        self.vulnerabilities_by_severity[vulnerability.severity.value] += 1
        self.vulnerabilities_by_category[vulnerability.category.value] += 1
    
    def get_total_vulnerabilities(self) -> int:
        """Get total number of vulnerabilities."""
        return sum(self.vulnerabilities_by_severity.values())
    
    def get_risk_score(self) -> float:
        """
        Calculate overall risk score based on vulnerabilities.
        
        Returns:
            Risk score from 0.0 (no risk) to 10.0 (maximum risk)
        """
        if self.total_payloads == 0:
            return 0.0
        
        # Weight severities
        severity_weights = {
            AttackSeverity.CRITICAL.value: 4.0,
            AttackSeverity.HIGH.value: 3.0,
            AttackSeverity.MEDIUM.value: 2.0,
            AttackSeverity.LOW.value: 1.0,
            AttackSeverity.INFO.value: 0.5
        }
        
        weighted_score = sum(
            count * severity_weights.get(severity, 0)
            for severity, count in self.vulnerabilities_by_severity.items()
        )
        
        # Normalize by total payloads and scale to 0-10
        max_possible_score = self.total_payloads * 4.0  # All critical
        if max_possible_score == 0:
            return 0.0
        
        return min(10.0, (weighted_score / max_possible_score) * 10.0)


@dataclass
class ScanResult:
    """
    Complete results of a security scan against an agent.
    """
    agent_name: str
    agent_config: Dict[str, Any]
    vulnerabilities: List[Vulnerability]
    attack_results: List[AttackResult] = field(default_factory=list)
    scan_duration: float = 0.0
    patterns_executed: int = 0
    total_tests: int = 0
    scanner_version: str = "0.1.0"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def statistics(self) -> ScanStatistics:
        """Get scan statistics."""
        stats = ScanStatistics(
            total_patterns=self.patterns_executed,
            total_payloads=self.total_tests,
            scan_duration=self.scan_duration
        )
        
        for vuln in self.vulnerabilities:
            stats.add_vulnerability(vuln)
        
        if self.total_tests > 0:
            stats.success_rate = len(self.vulnerabilities) / self.total_tests
        
        return stats
    
    def get_vulnerabilities_by_severity(self, severity: AttackSeverity) -> List[Vulnerability]:
        """Get vulnerabilities filtered by severity."""
        return [vuln for vuln in self.vulnerabilities if vuln.severity == severity]
    
    def get_vulnerabilities_by_category(self, category: AttackCategory) -> List[Vulnerability]:
        """Get vulnerabilities filtered by category."""
        return [vuln for vuln in self.vulnerabilities if vuln.category == category]
    
    def get_critical_vulnerabilities(self) -> List[Vulnerability]:
        """Get critical severity vulnerabilities."""
        return self.get_vulnerabilities_by_severity(AttackSeverity.CRITICAL)
    
    def get_high_vulnerabilities(self) -> List[Vulnerability]:
        """Get high severity vulnerabilities."""
        return self.get_vulnerabilities_by_severity(AttackSeverity.HIGH)
    
    def has_critical_issues(self) -> bool:
        """Check if scan found critical vulnerabilities."""
        return len(self.get_critical_vulnerabilities()) > 0
    
    def has_high_issues(self) -> bool:
        """Check if scan found high severity vulnerabilities."""
        return len(self.get_high_vulnerabilities()) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of scan results."""
        stats = self.statistics
        
        return {
            "agent_name": self.agent_name,
            "scan_timestamp": self.timestamp,
            "scan_duration": self.scan_duration,
            "total_vulnerabilities": len(self.vulnerabilities),
            "critical_vulnerabilities": len(self.get_critical_vulnerabilities()),
            "high_vulnerabilities": len(self.get_high_vulnerabilities()),
            "risk_score": stats.get_risk_score(),
            "patterns_executed": self.patterns_executed,
            "total_tests": self.total_tests,
            "success_rate": stats.success_rate,
            "vulnerabilities_by_severity": stats.vulnerabilities_by_severity,
            "vulnerabilities_by_category": stats.vulnerabilities_by_category
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical summary of scan results."""
        stats = self.statistics
        return {
            "severity_distribution": stats.vulnerabilities_by_severity,
            "category_distribution": stats.vulnerabilities_by_category,
            "success_rate": stats.success_rate,
            "risk_score": stats.get_risk_score(),
            "total_vulnerabilities": stats.get_total_vulnerabilities()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            "agent_name": self.agent_name,
            "agent_config": self.agent_config,
            "vulnerabilities": [vuln.to_dict() for vuln in self.vulnerabilities],
            "attack_results": [asdict(result) for result in self.attack_results],
            "scan_duration": self.scan_duration,
            "patterns_executed": self.patterns_executed,
            "total_tests": self.total_tests,
            "scanner_version": self.scanner_version,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "summary": self.get_summary()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert scan result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def save_to_file(self, filepath: str) -> None:
        """Save scan result to JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())


class ScanResultAnalyzer:
    """
    Utility class for analyzing and comparing scan results.
    """
    
    @staticmethod
    def compare_results(result1: ScanResult, result2: ScanResult) -> Dict[str, Any]:
        """
        Compare two scan results and identify changes.
        
        Args:
            result1: First scan result (baseline)
            result2: Second scan result (comparison)
            
        Returns:
            Dictionary containing comparison analysis
        """
        stats1 = result1.statistics
        stats2 = result2.statistics
        
        return {
            "vulnerability_change": {
                "total_change": len(result2.vulnerabilities) - len(result1.vulnerabilities),
                "critical_change": (
                    len(result2.get_critical_vulnerabilities()) - 
                    len(result1.get_critical_vulnerabilities())
                ),
                "high_change": (
                    len(result2.get_high_vulnerabilities()) - 
                    len(result1.get_high_vulnerabilities())
                )
            },
            "risk_score_change": stats2.get_risk_score() - stats1.get_risk_score(),
            "new_vulnerabilities": [
                vuln for vuln in result2.vulnerabilities
                if not any(v.name == vuln.name for v in result1.vulnerabilities)
            ],
            "resolved_vulnerabilities": [
                vuln for vuln in result1.vulnerabilities
                if not any(v.name == vuln.name for v in result2.vulnerabilities)
            ],
            "performance_change": {
                "duration_change": result2.scan_duration - result1.scan_duration,
                "test_count_change": result2.total_tests - result1.total_tests
            }
        }
    
    @staticmethod
    def generate_trend_analysis(results: List[ScanResult]) -> Dict[str, Any]:
        """
        Analyze trends across multiple scan results.
        
        Args:
            results: List of scan results ordered by time
            
        Returns:
            Dictionary containing trend analysis
        """
        if not results:
            return {"error": "No results provided"}
        
        if len(results) < 2:
            return {"error": "At least 2 results required for trend analysis"}
        
        # Sort by timestamp
        sorted_results = sorted(results, key=lambda r: r.timestamp)
        
        vulnerability_counts = [len(r.vulnerabilities) for r in sorted_results]
        risk_scores = [r.statistics.get_risk_score() for r in sorted_results]
        
        return {
            "total_scans": len(sorted_results),
            "time_span": sorted_results[-1].timestamp - sorted_results[0].timestamp,
            "vulnerability_trend": {
                "initial_count": vulnerability_counts[0],
                "final_count": vulnerability_counts[-1],
                "peak_count": max(vulnerability_counts),
                "average_count": sum(vulnerability_counts) / len(vulnerability_counts)
            },
            "risk_trend": {
                "initial_score": risk_scores[0],
                "final_score": risk_scores[-1],
                "peak_score": max(risk_scores),
                "average_score": sum(risk_scores) / len(risk_scores)
            },
            "improvement_rate": (
                (vulnerability_counts[0] - vulnerability_counts[-1]) / 
                max(vulnerability_counts[0], 1)
            ) if vulnerability_counts[0] > 0 else 0.0
        }