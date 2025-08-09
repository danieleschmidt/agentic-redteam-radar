"""
Core scanner engine for Agentic RedTeam Radar.

This module provides the main RadarScanner class that orchestrates 
security testing workflows for AI agents.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Type, Union, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

from .agent import Agent
from .attacks.base import AttackPattern
from .attacks.prompt_injection import PromptInjectionAttack
from .attacks.info_disclosure import InfoDisclosureAttack
from .attacks.policy_bypass import PolicyBypassAttack
from .attacks.chain_of_thought import ChainOfThoughtAttack
from .results import ScanResult, Vulnerability, AttackResult
try:
    from .config_simple import RadarConfig
except ImportError:
    from .config import RadarConfig
from .utils.logger import setup_logger
from .monitoring.telemetry import get_metrics_collector, get_performance_monitor
from .security.input_sanitizer import InputSanitizer, SecurityPolicy
from .performance.optimizer import get_performance_optimizer, profile_performance
from .cache.manager import get_cache_manager


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
        # Handle the case where config may not have initialized properly
        log_level = getattr(self.config, 'log_level', 'INFO')
        if hasattr(self.config, 'logging') and self.config.logging:
            log_level = self.config.logging.level
        self.logger = setup_logger(__name__, log_level)
        
        # Initialize security components
        self.input_sanitizer = InputSanitizer(SecurityPolicy())
        self.metrics_collector = get_metrics_collector()
        self.performance_monitor = get_performance_monitor()
        
        # Performance and optimization components
        self.performance_optimizer = get_performance_optimizer()
        self.cache_manager = get_cache_manager()
        
        # Resource pooling and concurrency control
        self.agent_semaphore = asyncio.Semaphore(getattr(config, 'max_agent_concurrency', 3))
        self.pattern_semaphore = asyncio.Semaphore(getattr(config, 'max_concurrency', 5))
        
        # Scanner state
        self.attack_patterns: List[AttackPattern] = []
        self.is_healthy = True
        self.scan_count = 0
        self.error_count = 0
        self.optimization_enabled = True
        
        self._load_default_patterns()
        self._setup_health_checks()
    
    def _load_default_patterns(self) -> None:
        """Load default attack patterns."""
        default_patterns = [
            PromptInjectionAttack(),
            InfoDisclosureAttack(), 
            PolicyBypassAttack(),
            ChainOfThoughtAttack()
        ]
        
        for pattern in default_patterns:
            # Extract the pattern type from class name (e.g., "PromptInjectionAttack" -> "prompt_injection")
            import re
            class_name = pattern.__class__.__name__
            clean_name = class_name.replace("Attack", "").replace("Pattern", "")
            pattern_type = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', clean_name).lower()
            
            enabled_patterns = getattr(self.config, 'enabled_patterns', set())
            if not enabled_patterns:
                # If no enabled patterns specified, enable all by default
                self.attack_patterns.append(pattern)
                self.logger.debug(f"Loaded attack pattern: {pattern.name} (type: {pattern_type}) - default enabled")
            elif pattern_type in enabled_patterns or pattern.name.lower() in enabled_patterns:
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
    
    @profile_performance
    async def scan(self, agent: Agent, progress_callback=None, use_cache: bool = True) -> ScanResult:
        """
        Execute comprehensive security scan against an agent.
        
        Args:
            agent: Agent instance to test
            progress_callback: Optional callback for progress updates
            use_cache: Whether to use caching for results
            
        Returns:
            ScanResult containing all vulnerabilities and statistics
        """
        # Start performance monitoring
        await self.performance_optimizer.start()
        
        # Apply adaptive optimizations if enabled
        if self.optimization_enabled:
            optimizations = self.performance_optimizer.adaptive_optimizer.apply_optimizations()
            if optimizations.get('reduce_concurrency'):
                # Reduce concurrency dynamically
                self.pattern_semaphore = asyncio.Semaphore(max(1, self.pattern_semaphore._value // 2))
                
        # Check cache first if enabled
        if use_cache:
            pattern_names = [p.name for p in self.attack_patterns]
            cached_result = self.cache_manager.get_scan_result(agent.name, pattern_names)
            if cached_result:
                self.logger.info(f"Cache hit for agent {agent.name} - returning cached results")
                return cached_result
        
        # Start metrics collection
        scan_id = self.metrics_collector.start_scan_metrics(agent.name)
        self.logger.info(f"Starting security scan of agent: {agent.name} [scan_id: {scan_id}]")
        
        try:
            # Increment scan count and reset health if needed
            self.scan_count += 1
            if self.error_count > 0 and self.scan_count % 10 == 0:  # Reset health periodically
                self.is_healthy = True
                self.error_count = 0
            
            # Validate agent before scanning
            agent_validation_errors = self.validate_agent(agent)
            if agent_validation_errors:
                self.error_count += 1
                raise ValueError(f"Agent validation failed: {'; '.join(agent_validation_errors)}")
            
            progress = ScanProgress(total_patterns=len(self.attack_patterns))
            vulnerabilities: List[Vulnerability] = []
            attack_results: List[AttackResult] = []
        
            # Use adaptive concurrency control
            active_semaphore = self.pattern_semaphore
            
            async def run_pattern(pattern: AttackPattern) -> List[AttackResult]:
                """Run a single attack pattern with concurrency control."""
                async with active_semaphore:
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
            
            # Update scan metrics
            self.metrics_collector.update_scan_metrics(
                scan_id,
                patterns_executed=len(self.attack_patterns),
                total_tests=len(attack_results),
                successful_tests=len([r for r in attack_results if not isinstance(r, Exception)]),
                failed_tests=self.error_count,
                vulnerabilities_found=len(vulnerabilities),
                critical_vulnerabilities=len([v for v in vulnerabilities if v.severity.value == 'critical']),
                high_vulnerabilities=len([v for v in vulnerabilities if v.severity.value == 'high'])
            )
            
            # Create scan result
            scan_result = ScanResult(
                agent_name=agent.name,
                agent_config=agent.get_config(),
                vulnerabilities=vulnerabilities,
                attack_results=attack_results,
                scan_duration=progress.elapsed_time,
                patterns_executed=len(self.attack_patterns),
                total_tests=len(attack_results),
                scanner_version=getattr(self.config, 'scanner_version', '0.1.0')
            )
            
            # Finalize metrics and check performance
            scan_metrics = self.metrics_collector.finalize_scan_metrics(scan_id)
            if scan_metrics:
                self.performance_monitor.check_performance_thresholds(scan_metrics)
            
            # Cache the result if enabled and successful
            if use_cache and len(vulnerabilities) >= 0:  # Always cache, even if no vulnerabilities
                pattern_names = [p.name for p in self.attack_patterns]
                cache_ttl = 1800 if len(vulnerabilities) == 0 else 3600  # Cache clean results for 30min, vulnerabilities for 1hr
                self.cache_manager.cache_scan_result(agent.name, pattern_names, scan_result, cache_ttl)
                self.logger.debug(f"Cached scan result for {agent.name} (TTL: {cache_ttl}s)")
            
            self.logger.info(
                f"Scan completed: {len(vulnerabilities)} vulnerabilities found "
                f"in {progress.elapsed_time:.2f}s [scan_id: {scan_id}]"
            )
            
            return scan_result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Scan failed for agent {agent.name}: {e}")
            
            # Try to finalize metrics even on failure
            try:
                self.metrics_collector.finalize_scan_metrics(scan_id)
            except:
                pass
            
            raise RuntimeError(f"Security scan failed: {e}") from e
    
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
    
    @profile_performance
    async def scan_multiple(self, agents: List[Agent], progress_callback=None, 
                          auto_scale: bool = True) -> Dict[str, ScanResult]:
        """
        Scan multiple agents concurrently with load balancing and auto-scaling.
        
        Args:
            agents: List of agent instances to test
            progress_callback: Optional callback for progress updates
            auto_scale: Whether to enable auto-scaling based on system resources
            
        Returns:
            Dictionary mapping agent names to their scan results
        """
        self.logger.info(f"Starting multi-agent scan of {len(agents)} agents")
        
        # Auto-scale concurrency based on system resources if enabled
        if auto_scale:
            current_metrics = self.performance_optimizer.resource_monitor.get_current_metrics()
            
            # Calculate optimal concurrency based on system resources
            base_concurrency = getattr(self.config, 'max_agent_concurrency', 3)
            
            if current_metrics.cpu_percent < 50 and current_metrics.memory_percent < 60:
                # System has capacity - increase concurrency
                optimal_concurrency = min(len(agents), base_concurrency * 2)
            elif current_metrics.cpu_percent > 80 or current_metrics.memory_percent > 85:
                # System under pressure - reduce concurrency
                optimal_concurrency = max(1, base_concurrency // 2)
            else:
                optimal_concurrency = base_concurrency
                
            self.logger.info(f"Auto-scaling: Using {optimal_concurrency} concurrent agents "
                           f"(CPU: {current_metrics.cpu_percent:.1f}%, "
                           f"Memory: {current_metrics.memory_percent:.1f}%)")
        else:
            optimal_concurrency = getattr(self.config, 'max_agent_concurrency', 3)
        
        # Use dynamic agent semaphore with load balancing
        agent_semaphore = asyncio.Semaphore(optimal_concurrency)
        
        async def scan_agent_with_balancing(agent: Agent) -> tuple[str, ScanResult]:
            """Scan agent with resource-aware load balancing."""
            async with agent_semaphore:
                # Check system load before each scan
                if auto_scale:
                    current_load = self.performance_optimizer.resource_monitor.get_current_metrics()
                    if current_load.cpu_percent > 90:
                        # Brief throttle if system is overloaded
                        await asyncio.sleep(0.5)
                
                result = await self.scan(agent, progress_callback, use_cache=True)
                return agent.name, result
        
        # Execute scans with load balancing
        tasks = [scan_agent_with_balancing(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        successful_results = {}
        failed_scans = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_scans.append(str(result))
                self.error_count += 1
            else:
                agent_name, scan_result = result
                successful_results[agent_name] = scan_result
        
        if failed_scans:
            self.logger.warning(f"Multi-agent scan had {len(failed_scans)} failures: {failed_scans}")
        
        self.logger.info(f"Multi-agent scan completed: {len(successful_results)}/{len(agents)} successful")
        return successful_results
    
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
    
    def _setup_health_checks(self) -> None:
        """Setup health monitoring and alerts."""
        try:
            # Add performance alert handler
            def alert_handler(alert_type: str, alert_data: Dict[str, Any]):
                self.logger.warning(f"Performance alert: {alert_type} - {alert_data}")
                if alert_type in ['performance_degradation', 'quality_degradation']:
                    self.error_count += 1
                    if self.error_count > 10:  # Threshold for unhealthy
                        self.is_healthy = False
            
            self.performance_monitor.add_alert_handler(alert_handler)
            self.logger.info("Health checks configured")
        except Exception as e:
            self.logger.error(f"Failed to setup health checks: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scanner health status.
        
        Returns:
            Health status dictionary
        """
        try:
            base_status = self.performance_monitor.get_health_status()
            
            scanner_status = {
                'scanner_healthy': self.is_healthy,
                'scan_count': self.scan_count,
                'error_count': self.error_count,
                'pattern_count': len(self.attack_patterns),
                'error_rate': self.error_count / max(self.scan_count, 1)
            }
            
            return {**base_status, 'scanner': scanner_status}
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {
                'status': 'unknown',
                'error': str(e),
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
        try:
            if isinstance(input_data, str):
                return self.input_sanitizer.sanitize_string(input_data, context)
            elif isinstance(input_data, dict):
                return self.input_sanitizer.sanitize_json(input_data)
            else:
                return input_data, []
        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            return None, [f"Validation failed: {e}"]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report for the scanner.
        
        Returns:
            Performance report including metrics and optimization suggestions
        """
        return {
            **self.performance_optimizer.get_performance_report(),
            'scanner_metrics': {
                'total_scans': self.scan_count,
                'error_rate': self.error_count / max(self.scan_count, 1),
                'is_healthy': self.is_healthy,
                'optimization_enabled': self.optimization_enabled
            },
            'cache_stats': self.cache_manager.get_stats()
        }
    
    async def cleanup_resources(self):
        """Clean up resources and optimize system for continued operation."""
        try:
            # Clear caches if system is under memory pressure
            current_metrics = self.performance_optimizer.resource_monitor.get_current_metrics()
            if current_metrics.memory_percent > 85:
                cleared = self.cache_manager.clear()
                if cleared:
                    self.logger.info("Cache cleared due to high memory usage")
            
            # Reset optimization state periodically
            if self.scan_count % 50 == 0:  # Every 50 scans
                self.performance_optimizer.profiler.clear_profiles()
                self.error_count = max(0, self.error_count - 5)  # Gradually reduce error count
                self.logger.info("Performance data reset for continued optimization")
            
            await self.performance_optimizer.stop()
            
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")