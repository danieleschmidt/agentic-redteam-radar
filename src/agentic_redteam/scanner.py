"""
Core scanner engine for Agentic RedTeam Radar.

This module provides the main RadarScanner class that orchestrates 
security testing workflows for AI agents.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from pathlib import Path

from .agent import Agent
from .attacks.base import AttackPattern
from .attacks.prompt_injection import PromptInjectionAttack
from .attacks.info_disclosure import InfoDisclosureAttack
from .attacks.policy_bypass import PolicyBypassAttack
from .attacks.chain_of_thought import ChainOfThoughtAttack
from .results import ScanResult, Vulnerability, AttackResult
from .config import RadarConfig
from .utils.logger import setup_logger


@dataclass
class ScanProgress:
    """Track scan progress and statistics."""
    total_patterns: int = 0
    completed_patterns: int = 0
    vulnerabilities_found: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_patterns == 0:
            return 0.0
        return (self.completed_patterns / self.total_patterns) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time


class RadarScanner:
    """
    Main scanner engine for AI agent security testing.
    
    Orchestrates attack pattern execution, result aggregation,
    and report generation for comprehensive agent security assessment.
    """
    
    def __init__(self, config: Optional[RadarConfig] = None):
        """
        Initialize the RadarScanner.
        
        Args:
            config: Configuration object for scanner behavior
        """
        self.config = config or RadarConfig()
        self.logger = setup_logger(__name__, self.config.log_level)
        self.attack_patterns: List[AttackPattern] = []
        self._load_default_patterns()
    
    def _load_default_patterns(self) -> None:
        """Load default attack patterns."""
        default_patterns = [
            PromptInjectionAttack(),
            InfoDisclosureAttack(), 
            PolicyBypassAttack(),
            ChainOfThoughtAttack()
        ]
        
        for pattern in default_patterns:
            if pattern.name.lower() in self.config.enabled_patterns:
                self.attack_patterns.append(pattern)
                self.logger.debug(f"Loaded attack pattern: {pattern.name}")
    
    def register_pattern(self, pattern: AttackPattern) -> None:
        """
        Register a custom attack pattern.
        
        Args:
            pattern: Custom attack pattern to register
        """
        if not isinstance(pattern, AttackPattern):
            raise TypeError("Pattern must inherit from AttackPattern")
        
        self.attack_patterns.append(pattern)
        self.logger.info(f"Registered custom pattern: {pattern.name}")
    
    def list_patterns(self) -> List[str]:
        """
        List all registered attack patterns.
        
        Returns:
            List of pattern names
        """
        return [pattern.name for pattern in self.attack_patterns]
    
    async def scan(self, agent: Agent, progress_callback=None) -> ScanResult:
        """
        Execute comprehensive security scan against an agent.
        
        Args:
            agent: Agent instance to test
            progress_callback: Optional callback for progress updates
            
        Returns:
            ScanResult containing all vulnerabilities and statistics
        """
        self.logger.info(f"Starting security scan of agent: {agent.name}")
        
        progress = ScanProgress(total_patterns=len(self.attack_patterns))
        vulnerabilities: List[Vulnerability] = []
        attack_results: List[AttackResult] = []
        
        # Execute attack patterns with configured concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        
        async def run_pattern(pattern: AttackPattern) -> List[AttackResult]:
            """Run a single attack pattern with concurrency control."""
            async with semaphore:
                try:
                    self.logger.debug(f"Executing pattern: {pattern.name}")
                    results = await pattern.execute(agent, self.config)
                    
                    progress.completed_patterns += 1
                    if progress_callback:
                        progress_callback(progress)
                    
                    return results
                    
                except Exception as e:
                    self.logger.error(f"Pattern {pattern.name} failed: {e}")
                    progress.completed_patterns += 1
                    if progress_callback:
                        progress_callback(progress)
                    return []
        
        # Execute all patterns concurrently
        tasks = [run_pattern(pattern) for pattern in self.attack_patterns]
        pattern_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for results in pattern_results:
            if isinstance(results, Exception):
                self.logger.error(f"Pattern execution failed: {results}")
                continue
            
            attack_results.extend(results)
            
            # Extract vulnerabilities
            for result in results:
                if result.is_vulnerable:
                    vulnerability = Vulnerability(
                        name=result.attack_name,
                        description=result.description,
                        severity=result.severity,
                        category=result.category,
                        evidence=result.evidence,
                        remediation=result.remediation,
                        cwe_id=result.cwe_id,
                        cvss_score=result.cvss_score
                    )
                    vulnerabilities.append(vulnerability)
                    progress.vulnerabilities_found += 1
        
        # Create scan result
        scan_result = ScanResult(
            agent_name=agent.name,
            agent_config=agent.get_config(),
            vulnerabilities=vulnerabilities,
            attack_results=attack_results,
            scan_duration=progress.elapsed_time,
            patterns_executed=len(self.attack_patterns),
            total_tests=sum(len(r.test_cases) for r in attack_results if hasattr(r, 'test_cases')),
            scanner_version=self.config.scanner_version
        )
        
        self.logger.info(
            f"Scan completed: {len(vulnerabilities)} vulnerabilities found "
            f"in {progress.elapsed_time:.2f}s"
        )
        
        return scan_result
    
    def scan_sync(self, agent: Agent, progress_callback=None) -> ScanResult:
        """
        Synchronous wrapper for scan method.
        
        Args:
            agent: Agent instance to test
            progress_callback: Optional callback for progress updates
            
        Returns:
            ScanResult containing all vulnerabilities and statistics
        """
        return asyncio.run(self.scan(agent, progress_callback))
    
    async def scan_multiple(self, agents: List[Agent], progress_callback=None) -> Dict[str, ScanResult]:
        """
        Scan multiple agents concurrently.
        
        Args:
            agents: List of agent instances to test
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping agent names to their scan results
        """
        self.logger.info(f"Starting multi-agent scan of {len(agents)} agents")
        
        # Execute scans with global concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_agent_concurrency)
        
        async def scan_agent(agent: Agent) -> tuple[str, ScanResult]:
            async with semaphore:
                result = await self.scan(agent, progress_callback)
                return agent.name, result
        
        tasks = [scan_agent(agent) for agent in agents]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    def validate_agent(self, agent: Agent) -> List[str]:
        """
        Validate agent configuration before scanning.
        
        Args:
            agent: Agent to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not agent.name:
            errors.append("Agent name is required")
        
        if not hasattr(agent, 'query') or not callable(agent.query):
            errors.append("Agent must implement query() method")
        
        try:
            # Test basic connectivity
            test_response = agent.query("Hello", timeout=5)
            if not test_response:
                errors.append("Agent query() returned empty response")
        except Exception as e:
            errors.append(f"Agent query() failed: {e}")
        
        return errors
    
    def get_pattern_info(self, pattern_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific pattern.
        
        Args:
            pattern_name: Name of the pattern to inspect
            
        Returns:
            Pattern information dictionary or None if not found
        """
        for pattern in self.attack_patterns:
            if pattern.name == pattern_name:
                return {
                    "name": pattern.name,
                    "description": pattern.description,
                    "category": pattern.category,
                    "severity": pattern.severity,
                    "cwe_id": pattern.cwe_id,
                    "references": getattr(pattern, 'references', [])
                }
        return None