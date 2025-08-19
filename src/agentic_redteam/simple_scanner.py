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
        self.start_time = time.time()
        
        # Generation 2: Reliability metrics
        self.successful_scans = 0
        self.failed_scans = 0
        self.total_vulnerabilities = 0
        
        # Generation 3: Performance optimization and scaling
        self.scan_cache = {}  # Simple result caching
        self.performance_history = []  # Track performance over time
        self.adaptive_concurrency = 2  # Dynamic concurrency adjustment
        self.max_cache_size = 100
        self.cache_ttl = 300  # 5 minutes
        
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
        Execute comprehensive security scan against an agent with Generation 3 optimizations.
        
        Args:
            agent: Agent instance to test
            progress_callback: Optional callback for progress updates
            
        Returns:
            ScanResult containing all vulnerabilities and statistics
        """
        scan_id = f"scan_{int(time.time())}"
        scan_start_time = time.time()
        
        # Generation 3: Check cache first
        cache_key = f"{agent.name}_{hash(str(sorted(p.name for p in self.attack_patterns)))}"
        if cache_key in self.scan_cache:
            cached_result, cache_time = self.scan_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                self.logger.info(f"Cache hit for agent {agent.name} - returning cached result")
                # Update scan statistics even for cached results
                self.scan_count += 1
                self.successful_scans += 1
                return cached_result
            else:
                # Cache expired, remove it
                del self.scan_cache[cache_key]
        
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
            
            # Generation 2: Update reliability metrics
            self.successful_scans += 1
            self.total_vulnerabilities += len(vulnerabilities)
            
            # Generation 3: Performance tracking and optimization
            scan_duration = time.time() - scan_start_time
            self.performance_history.append({
                'timestamp': time.time(),
                'duration': scan_duration,
                'vulnerabilities': len(vulnerabilities),
                'patterns': len(self.attack_patterns),
                'agent_name': agent.name
            })
            
            # Keep only recent performance history
            if len(self.performance_history) > 50:
                self.performance_history = self.performance_history[-25:]
            
            # Cache the result
            if len(self.scan_cache) >= self.max_cache_size:
                # Remove oldest cached entry
                oldest_key = min(self.scan_cache.keys(), 
                               key=lambda k: self.scan_cache[k][1])
                del self.scan_cache[oldest_key]
            
            self.scan_cache[cache_key] = (scan_result, time.time())
            
            # Adaptive concurrency adjustment based on performance
            if len(self.performance_history) >= 5:
                recent_avg_duration = sum(p['duration'] for p in self.performance_history[-5:]) / 5
                if recent_avg_duration < 0.1 and self.adaptive_concurrency < 5:
                    self.adaptive_concurrency += 1
                elif recent_avg_duration > 0.5 and self.adaptive_concurrency > 1:
                    self.adaptive_concurrency = max(1, self.adaptive_concurrency - 1)
            
            self.logger.info(
                f"Scan completed: {len(vulnerabilities)} vulnerabilities found "
                f"in {progress.elapsed_time:.2f}s [scan_id: {scan_id}] [cached]"
            )
            
            return scan_result
            
        except Exception as e:
            self.error_count += 1
            self.failed_scans += 1  # Generation 2: Track failed scans
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
    
    # Generation 2: Enhanced robustness and monitoring methods
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scanner health status.
        
        Returns:
            Health status dictionary with reliability metrics
        """
        uptime = time.time() - self.start_time
        error_rate = self.error_count / max(self.scan_count, 1)
        success_rate = self.successful_scans / max(self.scan_count, 1)
        
        return {
            'status': 'healthy' if self.is_healthy and error_rate < 0.5 else 'degraded',
            'scanner': {
                'scanner_healthy': self.is_healthy,
                'scan_count': self.scan_count,
                'successful_scans': self.successful_scans,
                'failed_scans': self.failed_scans,
                'error_count': self.error_count,
                'error_rate': error_rate,
                'success_rate': success_rate,
                'pattern_count': len(self.attack_patterns),
                'uptime_seconds': uptime,
                'total_vulnerabilities': self.total_vulnerabilities
            },
            'timestamp': time.time()
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report for the scanner.
        
        Returns:
            Performance report with metrics and statistics
        """
        uptime = time.time() - self.start_time
        scans_per_minute = (self.scan_count / max(uptime / 60, 1)) if uptime > 0 else 0
        avg_vulnerabilities_per_scan = self.total_vulnerabilities / max(self.scan_count, 1)
        
        return {
            'scanner_metrics': {
                'total_scans': self.scan_count,
                'successful_scans': self.successful_scans,
                'failed_scans': self.failed_scans,
                'error_rate': self.error_count / max(self.scan_count, 1),
                'success_rate': self.successful_scans / max(self.scan_count, 1),
                'is_healthy': self.is_healthy,
                'scans_per_minute': scans_per_minute,
                'avg_vulnerabilities_per_scan': avg_vulnerabilities_per_scan,
                'total_vulnerabilities_found': self.total_vulnerabilities,
                'uptime_seconds': uptime
            },
            'performance_stats': {
                'patterns_loaded': len(self.attack_patterns),
                'last_error_count': self.error_count,
                'optimization_enabled': True  # Simple scanner always optimized
            },
            'timestamp': time.time()
        }
    
    async def scan_multiple(self, agents: List[Agent], progress_callback=None, 
                          auto_scale: bool = True) -> Dict[str, ScanResult]:
        """
        Scan multiple agents concurrently with load balancing.
        
        Args:
            agents: List of agent instances to test
            progress_callback: Optional callback for progress updates
            auto_scale: Whether to enable auto-scaling (simple implementation)
            
        Returns:
            Dictionary mapping agent names to their scan results
        """
        self.logger.info(f"Starting multi-agent scan of {len(agents)} agents")
        
        # Generation 3: Adaptive auto-scaling based on performance history
        if auto_scale:
            # Use adaptive concurrency based on historical performance
            max_concurrent = self.adaptive_concurrency
            self.logger.info(f"Using adaptive concurrency: {max_concurrent}")
        else:
            max_concurrent = 2
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_semaphore(agent: Agent) -> tuple[str, ScanResult]:
            async with semaphore:
                result = await self.scan(agent, progress_callback)
                return agent.name, result
        
        # Execute scans with concurrency control
        tasks = [scan_with_semaphore(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = {}
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Multi-agent scan failure: {result}")
                failed_count += 1
                self.failed_scans += 1
            else:
                agent_name, scan_result = result
                successful_results[agent_name] = scan_result
        
        if failed_count > 0:
            self.logger.warning(f"Multi-agent scan had {failed_count} failures")
        
        self.logger.info(f"Multi-agent scan completed: {len(successful_results)}/{len(agents)} successful")
        return successful_results
    
    def validate_input(self, input_data: Any, context: str = "general") -> Tuple[Any, List[str]]:
        """
        Validate and sanitize input data for Generation 2 robustness.
        
        Args:
            input_data: Data to validate
            context: Context for validation
            
        Returns:
            Tuple of (sanitized_data, warnings)
        """
        warnings = []
        
        try:
            if isinstance(input_data, str):
                # Basic string sanitization
                if len(input_data) > 10000:
                    warnings.append("Input string truncated to 10000 characters")
                    input_data = input_data[:10000]
                
                # Check for potentially dangerous patterns
                dangerous_patterns = ['__import__', 'eval(', 'exec(', 'subprocess', 'os.system']
                for pattern in dangerous_patterns:
                    if pattern in input_data:
                        warnings.append(f"Potentially dangerous pattern detected: {pattern}")
                
                return input_data, warnings
                
            elif isinstance(input_data, dict):
                # Basic dict validation
                if len(str(input_data)) > 50000:
                    warnings.append("Input dict size may be too large")
                
                return input_data, warnings
            else:
                return input_data, warnings
                
        except Exception as e:
            warnings.append(f"Input validation error: {e}")
            return None, warnings
    
    # Generation 3: Advanced performance and scaling methods
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for Generation 3 performance monitoring."""
        return {
            'cache_size': len(self.scan_cache),
            'max_cache_size': self.max_cache_size,
            'cache_ttl_seconds': self.cache_ttl,
            'cache_hit_ratio': self._calculate_cache_hit_ratio(),
            'oldest_entry_age': self._get_oldest_cache_entry_age()
        }
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio from recent performance history."""
        if not self.performance_history:
            return 0.0
        
        # Estimate based on scan patterns - simplified calculation
        unique_agents = len(set(p['agent_name'] for p in self.performance_history))
        total_scans = len(self.performance_history)
        
        if unique_agents == 0:
            return 0.0
        
        # Rough estimation: higher ratio when scanning same agents repeatedly
        return max(0.0, min(1.0, (total_scans - unique_agents) / max(total_scans, 1)))
    
    def _get_oldest_cache_entry_age(self) -> float:
        """Get age of oldest cache entry in seconds."""
        if not self.scan_cache:
            return 0.0
        
        current_time = time.time()
        oldest_time = min(cache_time for _, cache_time in self.scan_cache.values())
        return current_time - oldest_time
    
    def optimize_performance(self) -> Dict[str, Any]:
        """
        Apply Generation 3 performance optimizations and return optimization report.
        """
        optimizations_applied = []
        
        # Clean expired cache entries
        current_time = time.time()
        expired_keys = [
            key for key, (_, cache_time) in self.scan_cache.items() 
            if current_time - cache_time > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.scan_cache[key]
        
        if expired_keys:
            optimizations_applied.append(f"Cleaned {len(expired_keys)} expired cache entries")
        
        # Optimize attack patterns based on performance
        if len(self.performance_history) >= 10:
            avg_duration = sum(p['duration'] for p in self.performance_history[-10:]) / 10
            
            if avg_duration > 1.0:  # If scans are taking too long
                # Could implement pattern prioritization here
                optimizations_applied.append("Flagged slow performance for pattern optimization")
            
            # Adjust cache TTL based on performance
            if avg_duration < 0.2:  # Fast scans
                self.cache_ttl = min(600, self.cache_ttl + 60)  # Increase cache TTL
                optimizations_applied.append("Increased cache TTL for fast scanning")
            elif avg_duration > 0.8:  # Slow scans
                self.cache_ttl = max(60, self.cache_ttl - 60)  # Decrease cache TTL
                optimizations_applied.append("Decreased cache TTL for slow scanning")
        
        # Memory optimization
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-50:]
            optimizations_applied.append("Trimmed performance history")
        
        return {
            'timestamp': time.time(),
            'optimizations_applied': optimizations_applied,
            'current_cache_size': len(self.scan_cache),
            'current_cache_ttl': self.cache_ttl,
            'adaptive_concurrency': self.adaptive_concurrency,
            'performance_history_size': len(self.performance_history)
        }
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """
        Get Generation 3 performance insights and recommendations.
        """
        if not self.performance_history:
            return {'status': 'insufficient_data', 'message': 'No performance data available'}
        
        recent_scans = self.performance_history[-10:] if len(self.performance_history) >= 10 else self.performance_history
        
        avg_duration = sum(p['duration'] for p in recent_scans) / len(recent_scans)
        avg_vulnerabilities = sum(p['vulnerabilities'] for p in recent_scans) / len(recent_scans)
        
        # Performance classification
        if avg_duration < 0.1:
            performance_class = 'excellent'
        elif avg_duration < 0.3:
            performance_class = 'good'
        elif avg_duration < 0.8:
            performance_class = 'fair'
        else:
            performance_class = 'needs_optimization'
        
        recommendations = []
        
        if avg_duration > 0.5:
            recommendations.append("Consider reducing attack patterns or optimizing pattern execution")
        
        if len(self.scan_cache) < 5 and self.scan_count > 10:
            recommendations.append("Cache hit ratio may be low - consider adjusting cache TTL")
        
        if self.adaptive_concurrency == 1 and avg_duration < 0.2:
            recommendations.append("System can handle higher concurrency - adaptive scaling available")
        
        return {
            'performance_class': performance_class,
            'avg_scan_duration': avg_duration,
            'avg_vulnerabilities_per_scan': avg_vulnerabilities,
            'cache_efficiency': len(self.scan_cache) / max(self.scan_count, 1),
            'adaptive_concurrency': self.adaptive_concurrency,
            'recommendations': recommendations,
            'scan_throughput': len(recent_scans) / max(sum(p['duration'] for p in recent_scans), 1),
            'performance_trend': self._analyze_performance_trend()
        }
    
    def _analyze_performance_trend(self) -> str:
        """Analyze performance trend over recent scans."""
        if len(self.performance_history) < 4:
            return 'insufficient_data'
        
        recent_half = self.performance_history[-len(self.performance_history)//2:]
        older_half = self.performance_history[:len(self.performance_history)//2]
        
        if not older_half or not recent_half:
            return 'insufficient_data'
        
        recent_avg = sum(p['duration'] for p in recent_half) / len(recent_half)
        older_avg = sum(p['duration'] for p in older_half) / len(older_half)
        
        if recent_avg < older_avg * 0.9:
            return 'improving'
        elif recent_avg > older_avg * 1.1:
            return 'degrading'
        else:
            return 'stable'