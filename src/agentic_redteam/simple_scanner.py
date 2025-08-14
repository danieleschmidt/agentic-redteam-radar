"""
Simplified scanner for basic functionality testing without external dependencies.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Type, Union, Tuple, Any
from dataclasses import dataclass, field

from .agent import Agent
from .attacks.base import AttackPattern
from .attacks.prompt_injection import PromptInjectionAttack
from .attacks.info_disclosure import InfoDisclosureAttack
from .attacks.policy_bypass import PolicyBypassAttack
from .attacks.chain_of_thought import ChainOfThoughtAttack
from .results import ScanResult, Vulnerability, AttackResult
from .config_simple import RadarConfig
from .utils.simple_logger import setup_logger


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


class SimpleRadarScanner:
    """
    Simplified scanner engine for AI agent security testing.
    
    Orchestrates attack pattern execution without complex dependencies.
    """
    
    def __init__(self, config: Optional[RadarConfig] = None):
        """
        Initialize the SimpleRadarScanner.
        
        Args:
            config: Configuration object for scanner behavior
        """
        self.config = config or RadarConfig()
        self.logger = setup_logger(__name__, self.config.log_level)
        
        # Scanner state
        self.attack_patterns: List[AttackPattern] = []
        self.is_healthy = True
        self.scan_count = 0
        self.error_count = 0
        
        self._load_default_patterns()
        
        self.logger.info(f"Simple scanner initialized with {len(self.attack_patterns)} patterns")
    
    def _load_default_patterns(self) -> None:
        """Load default attack patterns."""
        default_patterns = [
            PromptInjectionAttack(),
            InfoDisclosureAttack(), 
            PolicyBypassAttack(),
            ChainOfThoughtAttack()
        ]
        
        for pattern in default_patterns:
            # Extract the pattern type from class name
            import re
            class_name = pattern.__class__.__name__
            clean_name = class_name.replace("Attack", "").replace("Pattern", "")
            pattern_type = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', clean_name).lower()
            
            enabled_patterns = getattr(self.config, 'enabled_patterns', set())
            if not enabled_patterns or pattern_type in enabled_patterns or pattern.name.lower() in enabled_patterns:
                self.attack_patterns.append(pattern)
                self.logger.debug(f"Loaded attack pattern: {pattern.name} (type: {pattern_type})")
    
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
        scan_id = f"scan_{int(time.time())}"
        self.logger.info(f"Starting security scan of agent: {agent.name} [scan_id: {scan_id}]")
        
        try:
            # Increment scan count
            self.scan_count += 1
            
            # Validate agent before scanning
            agent_validation_errors = self.validate_agent(agent)
            if agent_validation_errors:
                self.error_count += 1
                raise ValueError(f"Agent validation failed: {'; '.join(agent_validation_errors)}")
            
            progress = ScanProgress(total_patterns=len(self.attack_patterns))
            vulnerabilities: List[Vulnerability] = []
            attack_results: List[AttackResult] = []
        
            # Use simple semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.config.max_concurrency)
            
            async def run_pattern(pattern: AttackPattern) -> List[AttackResult]:
                """Run a single attack pattern."""
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
                        self.error_count += 1
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
                    self.error_count += 1
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
                total_tests=len(attack_results),
                scanner_version=self.config.scanner_version
            )
            
            self.logger.info(
                f"Scan completed: {len(vulnerabilities)} vulnerabilities found "
                f"in {progress.elapsed_time:.2f}s [scan_id: {scan_id}]"
            )
            
            return scan_result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Scan failed for agent {agent.name}: {e}")
            raise RuntimeError(f"Security scan failed: {e}") from e
    
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
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get scanner health status.
        
        Returns:
            Health status dictionary
        """
        return {
            'status': 'healthy' if self.is_healthy else 'unhealthy',
            'scanner_healthy': self.is_healthy,
            'scan_count': self.scan_count,
            'error_count': self.error_count,
            'pattern_count': len(self.attack_patterns),
            'error_rate': self.error_count / max(self.scan_count, 1),
            'timestamp': time.time()
        }
    
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