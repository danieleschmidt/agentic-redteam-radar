"""
Simple health monitoring system without external dependencies.
"""

import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """Basic system metrics without psutil."""
    timestamp: float = field(default_factory=time.time)
    checks_passed: int = 0
    checks_failed: int = 0
    total_checks: int = 0
    uptime: float = 0.0


@dataclass
class HealthCheck:
    """Individual health check configuration."""
    name: str
    check_function: Callable[[], bool]
    critical: bool = False
    timeout: float = 5.0
    interval: float = 30.0
    failure_threshold: int = 3
    
    # Runtime state
    last_run: Optional[float] = None
    consecutive_failures: int = 0
    last_success: Optional[float] = None
    last_error: Optional[str] = None
    is_healthy: bool = True


@dataclass
class SystemHealth:
    """Overall system health assessment."""
    status: HealthStatus
    score: float  # 0.0 - 1.0
    checks: Dict[str, bool]
    metrics: SystemMetrics
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class SimpleHealthMonitor:
    """
    Simple system health monitoring without external dependencies.
    
    Provides basic health checking functionality for reliability monitoring.
    """
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self._start_time = time.time()
        
        # Health check task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # Health history for trend analysis
        self._health_history: List[SystemHealth] = []
        self._max_history = 100
        
        # Register default simple checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default simple health checks."""
        
        def basic_functionality_check() -> bool:
            """Basic functionality check."""
            try:
                # Simple computation test
                test_value = sum(range(100))
                return test_value == 4950
            except:
                return False
        
        def memory_availability_check() -> bool:
            """Basic memory availability check."""
            try:
                # Test simple memory allocation
                test_list = list(range(1000))
                return len(test_list) == 1000
            except:
                return False
        
        def time_consistency_check() -> bool:
            """Check time consistency."""
            try:
                now = time.time()
                return now > self._start_time
            except:
                return False
        
        # Register checks
        self.register_health_check("basic_functionality", basic_functionality_check, 
                                 critical=True, interval=60.0)
        self.register_health_check("memory_availability", memory_availability_check, 
                                 critical=True, interval=120.0)
        self.register_health_check("time_consistency", time_consistency_check, 
                                 critical=False, interval=300.0)
    
    def register_health_check(self, name: str, check_function: Callable[[], bool], 
                            critical: bool = False, timeout: float = 5.0, 
                            interval: float = 30.0, failure_threshold: int = 3):
        """
        Register a new health check.
        
        Args:
            name: Unique name for the health check
            check_function: Function that returns True if healthy
            critical: Whether this check is critical for system operation
            timeout: Timeout for the check in seconds
            interval: How often to run the check in seconds
            failure_threshold: Number of failures before marking as unhealthy
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            critical=critical,
            timeout=timeout,
            interval=interval,
            failure_threshold=failure_threshold
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                # Run health checks that are due
                await self._run_due_checks()
                
                # Brief sleep before next iteration
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(30)  # Back off on error
    
    async def _run_due_checks(self):
        """Run health checks that are due."""
        current_time = time.time()
        
        for check in self.health_checks.values():
            # Skip if not due
            if check.last_run and (current_time - check.last_run) < check.interval:
                continue
            
            try:
                # Run check with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(check.check_function),
                    timeout=check.timeout
                )
                
                check.last_run = current_time
                
                if result:
                    # Check passed
                    check.consecutive_failures = 0
                    check.last_success = current_time
                    check.is_healthy = True
                    check.last_error = None
                else:
                    # Check failed
                    check.consecutive_failures += 1
                    
                    if check.consecutive_failures >= check.failure_threshold:
                        check.is_healthy = False
                
            except asyncio.TimeoutError:
                check.last_error = f"Timeout after {check.timeout}s"
                check.consecutive_failures += 1
                
                if check.consecutive_failures >= check.failure_threshold:
                    check.is_healthy = False
                
            except Exception as e:
                check.last_error = str(e)
                check.consecutive_failures += 1
                
                if check.consecutive_failures >= check.failure_threshold:
                    check.is_healthy = False
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current simple system metrics."""
        checks_passed = sum(1 for check in self.health_checks.values() if check.is_healthy)
        checks_failed = len(self.health_checks) - checks_passed
        uptime = time.time() - self._start_time
        
        return SystemMetrics(
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            total_checks=len(self.health_checks),
            uptime=uptime
        )
    
    def get_current_health(self) -> SystemHealth:
        """Get current comprehensive health assessment."""
        metrics = self.get_system_metrics()
        
        # Assess individual checks
        check_results = {}
        critical_failures = 0
        total_failures = 0
        
        for name, check in self.health_checks.items():
            is_healthy = check.is_healthy
            check_results[name] = is_healthy
            
            if not is_healthy:
                total_failures += 1
                if check.critical:
                    critical_failures += 1
        
        # Determine overall status
        status = HealthStatus.HEALTHY
        issues = []
        recommendations = []
        
        # Critical failures = Critical status
        if critical_failures > 0:
            status = HealthStatus.CRITICAL
            issues.append(f"{critical_failures} critical health checks failing")
            recommendations.append("Immediate intervention required for critical issues")
        
        # Non-critical failures
        elif total_failures > 0:
            if total_failures >= len(self.health_checks) / 2:
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.DEGRADED
            
            issues.append(f"{total_failures} health checks failing")
            recommendations.append("Investigate failing health checks")
        
        # Calculate health score (0.0 - 1.0)
        if len(self.health_checks) > 0:
            success_rate = metrics.checks_passed / len(self.health_checks)
            score = success_rate
        else:
            score = 1.0
        
        # Apply critical failure penalty
        if critical_failures > 0:
            score *= 0.5  # Severe penalty for critical failures
        
        health = SystemHealth(
            status=status,
            score=score,
            checks=check_results,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations
        )
        
        # Add to history
        self._health_history.append(health)
        if len(self._health_history) > self._max_history:
            self._health_history.pop(0)
        
        return health
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health status and statistics."""
        current_health = self.get_current_health()
        
        # Check statistics
        total_checks = len(self.health_checks)
        healthy_checks = sum(1 for check in self.health_checks.values() if check.is_healthy)
        critical_checks = sum(1 for check in self.health_checks.values() if check.critical)
        
        return {
            "overall_status": current_health.status.value,
            "health_score": current_health.score,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "critical_checks": critical_checks,
            "uptime": current_health.metrics.uptime,
            "issues": current_health.issues,
            "recommendations": current_health.recommendations,
            "timestamp": current_health.timestamp
        }