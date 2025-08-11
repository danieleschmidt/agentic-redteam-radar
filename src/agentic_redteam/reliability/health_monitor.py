"""
Advanced health monitoring system for production readiness.
"""

import asyncio
import time
import psutil
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_io: Dict[str, int] = field(default_factory=dict)
    process_count: int = 0
    thread_count: int = 0
    open_files: int = 0
    timestamp: float = field(default_factory=time.time)


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


class HealthMonitor:
    """
    Comprehensive system health monitoring.
    
    Monitors system resources, application health checks, and provides
    actionable health assessments with recommendations.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.reliability.health_monitor")
        self.health_checks: Dict[str, HealthCheck] = {}
        self.system_thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 75.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0
        }
        
        # Health check task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # Health history for trend analysis
        self._health_history: List[SystemHealth] = []
        self._max_history = 100
        
        # Register default system checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default system health checks."""
        
        def cpu_check() -> bool:
            """Check CPU usage is within acceptable limits."""
            return psutil.cpu_percent(interval=1) < self.system_thresholds['cpu_critical']
        
        def memory_check() -> bool:
            """Check memory usage is within acceptable limits."""
            return psutil.virtual_memory().percent < self.system_thresholds['memory_critical']
        
        def disk_check() -> bool:
            """Check disk usage is within acceptable limits."""
            return psutil.disk_usage('/').percent < self.system_thresholds['disk_critical']
        
        def process_check() -> bool:
            """Check process health."""
            try:
                # Check if current process is responding
                current_process = psutil.Process()
                return current_process.is_running() and current_process.status() != psutil.STATUS_ZOMBIE
            except:
                return False
        
        # Register checks
        self.register_health_check("system_cpu", cpu_check, critical=True, interval=15.0)
        self.register_health_check("system_memory", memory_check, critical=True, interval=15.0)
        self.register_health_check("system_disk", disk_check, critical=False, interval=60.0)
        self.register_health_check("process_health", process_check, critical=True, interval=30.0)
    
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
        
        self.logger.info(f"Registered health check: {name} (critical: {critical})")
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                # Run health checks that are due
                await self._run_due_checks()
                
                # Brief sleep before next iteration
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
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
                    if not check.is_healthy:
                        self.logger.info(f"Health check {check.name} recovered")
                    
                    check.consecutive_failures = 0
                    check.last_success = current_time
                    check.is_healthy = True
                    check.last_error = None
                else:
                    # Check failed
                    check.consecutive_failures += 1
                    
                    if check.consecutive_failures >= check.failure_threshold:
                        if check.is_healthy:
                            self.logger.warning(
                                f"Health check {check.name} failed threshold "
                                f"({check.consecutive_failures}/{check.failure_threshold})"
                            )
                        check.is_healthy = False
                
            except asyncio.TimeoutError:
                check.last_error = f"Timeout after {check.timeout}s"
                check.consecutive_failures += 1
                
                if check.consecutive_failures >= check.failure_threshold:
                    check.is_healthy = False
                    
                self.logger.warning(f"Health check {check.name} timed out")
                
            except Exception as e:
                check.last_error = str(e)
                check.consecutive_failures += 1
                
                if check.consecutive_failures >= check.failure_threshold:
                    check.is_healthy = False
                
                self.logger.error(f"Health check {check.name} failed with error: {e}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Disk usage for root partition
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network_io = {}
            try:
                net_io = psutil.net_io_counters()
                if net_io:
                    network_io = {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv
                    }
            except:
                pass
            
            # Process information
            try:
                current_process = psutil.Process()
                process_count = len(psutil.pids())
                thread_count = current_process.num_threads()
                
                # Open files (if supported)
                open_files = 0
                try:
                    open_files = len(current_process.open_files())
                except:
                    pass
                    
            except:
                process_count = 0
                thread_count = 0
                open_files = 0
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                thread_count=thread_count,
                open_files=open_files
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics()  # Return empty metrics on error
    
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
        
        # System resource issues
        elif (metrics.cpu_percent > self.system_thresholds['cpu_critical'] or
              metrics.memory_percent > self.system_thresholds['memory_critical']):
            status = HealthStatus.CRITICAL
            if metrics.cpu_percent > self.system_thresholds['cpu_critical']:
                issues.append(f"CPU usage critical: {metrics.cpu_percent:.1f}%")
                recommendations.append("Reduce CPU load or scale resources")
            if metrics.memory_percent > self.system_thresholds['memory_critical']:
                issues.append(f"Memory usage critical: {metrics.memory_percent:.1f}%")
                recommendations.append("Clear memory or increase available RAM")
        
        # Non-critical failures or resource warnings
        elif (total_failures > 0 or 
              metrics.cpu_percent > self.system_thresholds['cpu_warning'] or
              metrics.memory_percent > self.system_thresholds['memory_warning']):
            
            status = HealthStatus.DEGRADED
            
            if total_failures > 0:
                issues.append(f"{total_failures} health checks failing")
                recommendations.append("Investigate failing health checks")
            
            if metrics.cpu_percent > self.system_thresholds['cpu_warning']:
                issues.append(f"CPU usage elevated: {metrics.cpu_percent:.1f}%")
                recommendations.append("Monitor CPU usage trends")
            
            if metrics.memory_percent > self.system_thresholds['memory_warning']:
                issues.append(f"Memory usage elevated: {metrics.memory_percent:.1f}%")
                recommendations.append("Monitor memory usage trends")
        
        # Calculate health score (0.0 - 1.0)
        base_score = 1.0
        
        # Penalize for failed checks
        if len(self.health_checks) > 0:
            check_penalty = total_failures / len(self.health_checks) * 0.4
            base_score -= check_penalty
        
        # Penalize for resource usage
        cpu_penalty = max(0, (metrics.cpu_percent - 50) / 50) * 0.3
        memory_penalty = max(0, (metrics.memory_percent - 50) / 50) * 0.3
        base_score -= cpu_penalty + memory_penalty
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, base_score))
        
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
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze health trends over time."""
        if not self._health_history:
            return {"trend": "unknown", "data": []}
        
        # Filter to requested time window
        cutoff_time = time.time() - (hours * 3600)
        recent_health = [h for h in self._health_history if h.timestamp > cutoff_time]
        
        if len(recent_health) < 2:
            return {"trend": "insufficient_data", "data": recent_health}
        
        # Analyze trends
        scores = [h.score for h in recent_health]
        cpu_usage = [h.metrics.cpu_percent for h in recent_health]
        memory_usage = [h.metrics.memory_percent for h in recent_health]
        
        # Calculate trends (simple linear)
        def calculate_trend(values):
            if len(values) < 2:
                return "stable"
            
            recent_avg = sum(values[-5:]) / min(5, len(values))
            earlier_avg = sum(values[:5]) / min(5, len(values))
            
            if recent_avg > earlier_avg * 1.1:
                return "increasing"
            elif recent_avg < earlier_avg * 0.9:
                return "decreasing"
            else:
                return "stable"
        
        return {
            "trend": calculate_trend(scores),
            "score_trend": calculate_trend(scores),
            "cpu_trend": calculate_trend(cpu_usage),
            "memory_trend": calculate_trend(memory_usage),
            "average_score": sum(scores) / len(scores),
            "recent_score": scores[-1] if scores else 0,
            "data_points": len(recent_health),
            "time_range_hours": hours
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health status and statistics."""
        current_health = self.get_current_health()
        trends = self.get_health_trends()
        
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
            "system_metrics": {
                "cpu_percent": current_health.metrics.cpu_percent,
                "memory_percent": current_health.metrics.memory_percent,
                "disk_percent": current_health.metrics.disk_percent,
                "process_count": current_health.metrics.process_count
            },
            "trends": trends,
            "issues": current_health.issues,
            "recommendations": current_health.recommendations,
            "timestamp": current_health.timestamp
        }