"""
Performance optimization utilities for Agentic RedTeam Radar.

This module provides performance optimization, profiling, and resource
management utilities for the security testing framework.
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

from ..utils.logger import get_logger


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available: int = 0
    disk_usage: float = 0.0
    network_io: Dict[str, int] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass 
class PerformanceProfile:
    """Performance profiling data."""
    function_name: str
    total_calls: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    last_call: float = 0.0
    
    def update(self, duration: float):
        """Update profile with new timing data."""
        self.total_calls += 1
        self.total_time += duration
        self.average_time = self.total_time / self.total_calls
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.last_call = time.time()


class ResourceMonitor:
    """Monitor system resources and performance."""
    
    def __init__(self, collection_interval: float = 5.0):
        """
        Initialize resource monitor.
        
        Args:
            collection_interval: Interval between metric collections
        """
        self.collection_interval = collection_interval
        self.metrics_history: deque = deque(maxlen=1000)
        self.is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.logger = get_logger(__name__)
    
    async def start_monitoring(self):
        """Start resource monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._collect_metrics())
        self.logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Resource monitoring stopped")
    
    async def _collect_metrics(self):
        """Collect system metrics periodically."""
        while self.is_monitoring:
            try:
                metrics = self._get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Log warnings for high resource usage
                if metrics.cpu_percent > 80:
                    self.logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
                if metrics.memory_percent > 85:
                    self.logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def _get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O (if available)
            network_io = {}
            try:
                net_io = psutil.net_io_counters()
                network_io = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                }
            except Exception:
                pass
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available,
                disk_usage=disk.percent,
                network_io=network_io
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
            return SystemMetrics()
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics synchronously."""
        return self._get_current_metrics()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = list(self.metrics_history)[-60:]  # Last 60 samples
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'samples': len(recent_metrics),
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0
            },
            'memory': {
                'current': memory_values[-1] if memory_values else 0,
                'average': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0
            },
            'latest_timestamp': recent_metrics[-1].timestamp if recent_metrics else 0
        }


class PerformanceProfiler:
    """Profile function performance and execution times."""
    
    def __init__(self):
        """Initialize performance profiler."""
        self.profiles: Dict[str, PerformanceProfile] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile function performance."""
        func_name = f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self._record_timing(func_name, duration)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self._record_timing(func_name, duration)
            return sync_wrapper
    
    def _record_timing(self, func_name: str, duration: float):
        """Record timing for a function."""
        with self._lock:
            if func_name not in self.profiles:
                self.profiles[func_name] = PerformanceProfile(func_name)
            
            self.profiles[func_name].update(duration)
    
    def get_profile(self, func_name: str) -> Optional[PerformanceProfile]:
        """Get profile for a specific function."""
        return self.profiles.get(func_name)
    
    def get_all_profiles(self) -> Dict[str, PerformanceProfile]:
        """Get all function profiles."""
        return self.profiles.copy()
    
    def get_top_functions(self, limit: int = 10, sort_by: str = 'total_time') -> List[PerformanceProfile]:
        """Get top functions by specified metric."""
        valid_sort_keys = ['total_time', 'average_time', 'total_calls', 'max_time']
        if sort_by not in valid_sort_keys:
            sort_by = 'total_time'
        
        sorted_profiles = sorted(
            self.profiles.values(),
            key=lambda p: getattr(p, sort_by),
            reverse=True
        )
        
        return sorted_profiles[:limit]
    
    def clear_profiles(self):
        """Clear all profiling data."""
        with self._lock:
            self.profiles.clear()


class AdaptiveOptimizer:
    """Adaptive performance optimizer that adjusts based on system load."""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        """
        Initialize adaptive optimizer.
        
        Args:
            resource_monitor: Resource monitor instance
        """
        self.resource_monitor = resource_monitor
        self.optimization_rules: List[Callable] = []
        self.logger = get_logger(__name__)
        
        # Default optimization thresholds
        self.cpu_threshold = 75.0
        self.memory_threshold = 80.0
        
        # Current optimization state
        self.current_optimizations: Dict[str, Any] = {}
    
    def add_optimization_rule(self, rule: Callable[[SystemMetrics], Dict[str, Any]]):
        """Add a custom optimization rule."""
        self.optimization_rules.append(rule)
    
    def apply_optimizations(self) -> Dict[str, Any]:
        """Apply optimizations based on current system state."""
        current_metrics = self.resource_monitor.get_current_metrics()
        optimizations = {}
        
        # Apply built-in optimizations
        if current_metrics.cpu_percent > self.cpu_threshold:
            optimizations.update(self._optimize_for_high_cpu())
        
        if current_metrics.memory_percent > self.memory_threshold:
            optimizations.update(self._optimize_for_high_memory())
        
        # Apply custom rules
        for rule in self.optimization_rules:
            try:
                rule_optimizations = rule(current_metrics)
                if rule_optimizations:
                    optimizations.update(rule_optimizations)
            except Exception as e:
                self.logger.error(f"Optimization rule failed: {e}")
        
        # Update current state
        self.current_optimizations.update(optimizations)
        
        if optimizations:
            self.logger.info(f"Applied optimizations: {list(optimizations.keys())}")
        
        return optimizations
    
    def _optimize_for_high_cpu(self) -> Dict[str, Any]:
        """Optimizations for high CPU usage."""
        return {
            'reduce_concurrency': True,
            'increase_cache_ttl': True,
            'defer_non_critical_tasks': True
        }
    
    def _optimize_for_high_memory(self) -> Dict[str, Any]:
        """Optimizations for high memory usage."""
        return {
            'clear_caches': True,
            'reduce_batch_sizes': True,
            'enable_garbage_collection': True
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get current optimization suggestions."""
        current_metrics = self.resource_monitor.get_current_metrics()
        suggestions = []
        
        if current_metrics.cpu_percent > 60:
            suggestions.append("Consider reducing concurrent operations")
        
        if current_metrics.memory_percent > 70:
            suggestions.append("Consider clearing caches or reducing batch sizes")
        
        metrics_summary = self.resource_monitor.get_metrics_summary()
        if metrics_summary.get('cpu', {}).get('average', 0) > 50:
            suggestions.append("Consistent high CPU usage detected - consider optimization")
        
        return suggestions


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        """Initialize performance optimizer."""
        self.resource_monitor = ResourceMonitor()
        self.profiler = PerformanceProfiler()
        self.adaptive_optimizer = AdaptiveOptimizer(self.resource_monitor)
        self.logger = get_logger(__name__)
        
        # Add default optimization rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default optimization rules."""
        def memory_pressure_rule(metrics: SystemMetrics) -> Dict[str, Any]:
            if metrics.memory_percent > 90:
                return {'emergency_cleanup': True}
            return {}
        
        def cpu_pressure_rule(metrics: SystemMetrics) -> Dict[str, Any]:
            if metrics.cpu_percent > 95:
                return {'throttle_requests': True}
            return {}
        
        self.adaptive_optimizer.add_optimization_rule(memory_pressure_rule)
        self.adaptive_optimizer.add_optimization_rule(cpu_pressure_rule)
    
    async def start(self):
        """Start performance monitoring and optimization."""
        await self.resource_monitor.start_monitoring()
        self.logger.info("Performance optimizer started")
    
    async def stop(self):
        """Stop performance monitoring."""
        await self.resource_monitor.stop_monitoring()
        self.logger.info("Performance optimizer stopped")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics_summary = self.resource_monitor.get_metrics_summary()
        top_functions = self.profiler.get_top_functions(limit=5)
        suggestions = self.adaptive_optimizer.get_optimization_suggestions()
        
        return {
            'system_metrics': metrics_summary,
            'top_functions': [
                {
                    'name': p.function_name,
                    'total_calls': p.total_calls,
                    'total_time': p.total_time,
                    'average_time': p.average_time
                }
                for p in top_functions
            ],
            'optimization_suggestions': suggestions,
            'current_optimizations': self.adaptive_optimizer.current_optimizations
        }


# Global performance optimizer instance
_global_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer()
    return _global_optimizer


def profile_performance(func: Callable) -> Callable:
    """Decorator to profile function performance."""
    optimizer = get_performance_optimizer()
    return optimizer.profiler.profile_function(func)