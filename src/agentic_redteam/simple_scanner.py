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
            
            # Validate agent before scanning (with graceful degradation)
            agent_validation_errors = self.validate_agent(agent)
            if agent_validation_errors:
                self.error_count += 1
                self.logger.warning(f"Agent validation issues for {agent.name}: {'; '.join(agent_validation_errors)}")
                
                # For completely failing agents, return graceful degraded result instead of error
                if len(agent_validation_errors) > 0 and any("failed after retries" in error for error in agent_validation_errors):
                    self.logger.info(f"Creating degraded scan result for failing agent: {agent.name}")
                    return ScanResult(
                        agent_name=agent.name,
                        agent_config=agent.get_config() if hasattr(agent, 'get_config') else {},
                        vulnerabilities=[],
                        attack_results=[],
                        scan_duration=0.1,
                        patterns_executed=0,
                        total_tests=0,
                        scanner_version=self.config.scanner_version,
                        error_count=1,
                        scan_status="degraded",
                        status_message="Agent unresponsive - graceful degradation applied"
                    )
            
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
            # Test basic connectivity with retry logic
            for attempt in range(3):  # Retry up to 3 times
                try:
                    test_response = agent.query("Hello", timeout=5)
                    if not test_response:
                        if attempt == 2:  # Last attempt
                            errors.append("Agent query() returned empty response after retries")
                    else:
                        break  # Success
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        errors.append(f"Agent query() failed after retries: {e}")
                    else:
                        time.sleep(0.1)  # Brief delay before retry
                        continue
        except Exception as e:
            errors.append(f"Agent validation error: {e}")
        
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
    
    def validate_input(self, input_data: Any, context: str = "general") -> Tuple[Any, List[str]]:
        """
        Validate and sanitize input data.
        
        Args:
            input_data: Data to validate
            context: Context for validation
            
        Returns:
            Tuple of (sanitized_data, warnings)
        """
        warnings = []
        
        if input_data is None:
            warnings.append("Null input detected")
            return "", warnings
        
        if isinstance(input_data, str):
            # Check for suspicious patterns
            suspicious_patterns = [
                ("<script", "Potential XSS attempt"),
                ("javascript:", "JavaScript injection attempt"),
                ("SELECT", "Potential SQL injection"),
                ("DROP", "Dangerous SQL command"),
                ("../", "Directory traversal attempt"),
                ("eval(", "Code execution attempt"),
            ]
            
            input_lower = input_data.lower()
            for pattern, warning in suspicious_patterns:
                if pattern.lower() in input_lower:
                    warnings.append(warning)
            
            # Check length
            if len(input_data) > 10000:
                warnings.append("Input exceeds maximum length")
                input_data = input_data[:10000] + "..."
            
            return input_data, warnings
        
        elif isinstance(input_data, dict):
            warnings.append("Dictionary input converted to string")
            return str(input_data), warnings
        
        else:
            warnings.append(f"Unexpected input type: {type(input_data)}")
            return str(input_data), warnings
    
    async def scan_multiple(self, agents: List[Agent], auto_scale: bool = True) -> Dict[str, ScanResult]:
        """
        Scan multiple agents with auto-scaling capabilities.
        
        Args:
            agents: List of agent instances to test
            auto_scale: Enable automatic scaling optimization
            
        Returns:
            Dictionary mapping agent names to scan results
        """
        results = {}
        
        if auto_scale:
            # Implement simple auto-scaling logic
            max_concurrent = min(len(agents), self.config.max_concurrency)
            semaphore = asyncio.Semaphore(max_concurrent)
        else:
            semaphore = asyncio.Semaphore(1)  # Sequential
        
        async def scan_agent(agent: Agent) -> Tuple[str, ScanResult]:
            """Scan a single agent with concurrency control."""
            async with semaphore:
                result = await self.scan(agent)
                return agent.name, result
        
        # Execute all scans concurrently with auto-scaling
        tasks = [scan_agent(agent) for agent in agents]
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in scan_results:
            if isinstance(result, Exception):
                self.logger.error(f"Agent scan failed: {result}")
                continue
            
            agent_name, scan_result = result
            results[agent_name] = scan_result
        
        return results
    
    async def cleanup_resources(self) -> None:
        """Clean up scanner resources to prevent memory leaks."""
        # Simple cleanup implementation
        import gc
        gc.collect()  # Force garbage collection
        
        # Reset any cached data
        self.scan_count = max(0, self.scan_count - 1) if self.scan_count > 10 else self.scan_count
        
        self.logger.debug("Scanner resources cleaned up")
    
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