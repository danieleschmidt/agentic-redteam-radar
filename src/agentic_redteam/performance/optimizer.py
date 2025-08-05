"""
Performance optimization module for Agentic RedTeam Radar.

Provides advanced performance optimization, profiling,
and scalability enhancements for high-throughput scanning.
"""

import asyncio
import time
import statistics
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from ..monitoring import error_handler, ErrorCategory, ErrorSeverity
from ..utils.logger import get_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    operation: str
    duration: float
    success: bool
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler:
    """
    Advanced performance profiler with statistical analysis.
    """
    
    def __init__(self, max_samples: int = 10000):
        """
        Initialize performance profiler.
        
        Args:
            max_samples: Maximum number of samples to keep
        """
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.logger = get_logger("agentic_redteam.performance.profiler")
        self._lock = threading.RLock()
    
    def record_metric(self, metric: PerformanceMetrics) -> None:
        """Record a performance metric."""
        with self._lock:
            self.metrics[metric.operation].append(metric)
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """
        Get statistical analysis for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Statistical analysis
        """
        with self._lock:
            samples = list(self.metrics[operation])
        
        if not samples:
            return {"error": "No samples available"}
        
        durations = [s.duration for s in samples]
        successes = [s.success for s in samples]
        
        return {
            "operation": operation,
            "sample_count": len(samples),
            "success_rate": sum(successes) / len(successes),
            "duration_stats": {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "min": min(durations),
                "max": max(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "p95": statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations),
                "p99": statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else max(durations)
            },
            "recent_samples": len([s for s in samples if time.time() - s.timestamp < 300])  # Last 5 minutes
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        with self._lock:
            operations = list(self.metrics.keys())
        
        return {op: self.get_stats(op) for op in operations}
    
    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """
        Detect performance issues across operations.
        
        Returns:
            List of detected issues
        """
        issues = []
        
        for operation in self.metrics:
            stats = self.get_stats(operation)
            
            if stats.get("sample_count", 0) < 10:
                continue  # Not enough data
            
            duration_stats = stats.get("duration_stats", {})
            success_rate = stats.get("success_rate", 1.0)
            
            # Check for performance degradation
            if duration_stats.get("p95", 0) > 10.0:  # 10 seconds
                issues.append({
                    "type": "high_latency",
                    "operation": operation,
                    "p95_duration": duration_stats["p95"],
                    "severity": "high"
                })
            
            # Check for low success rate
            if success_rate < 0.9:  # Less than 90%
                issues.append({
                    "type": "low_success_rate",
                    "operation": operation,
                    "success_rate": success_rate,
                    "severity": "medium"
                })
            
            # Check for high variance
            if duration_stats.get("stdev", 0) > duration_stats.get("mean", 0):
                issues.append({
                    "type": "high_variance",
                    "operation": operation,
                    "coefficient_variation": duration_stats["stdev"] / duration_stats["mean"],
                    "severity": "low"
                })
        
        return issues


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile_performance(operation: str = None):
    """
    Decorator for performance profiling.
    
    Args:
        operation: Operation name (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                finally:
                    duration = time.time() - start_time
                    metric = PerformanceMetrics(
                        operation=op_name,
                        duration=duration,
                        success=success,
                        metadata={"args_count": len(args), "kwargs_count": len(kwargs)}
                    )
                    get_profiler().record_metric(metric)
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                finally:
                    duration = time.time() - start_time
                    metric = PerformanceMetrics(
                        operation=op_name,
                        duration=duration,
                        success=success,
                        metadata={"args_count": len(args), "kwargs_count": len(kwargs)}
                    )
                    get_profiler().record_metric(metric)
            
            return sync_wrapper
    
    return decorator


class AdaptiveConcurrencyController:
    """
    Adaptive concurrency controller that adjusts concurrency based on performance.
    """
    
    def __init__(self, 
                 min_concurrency: int = 1,
                 max_concurrency: int = 50,
                 target_latency: float = 2.0,
                 adjustment_interval: float = 30.0):
        """
        Initialize adaptive concurrency controller.
        
        Args:
            min_concurrency: Minimum concurrency level
            max_concurrency: Maximum concurrency level
            target_latency: Target latency in seconds
            adjustment_interval: How often to adjust concurrency
        """
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.target_latency = target_latency
        self.adjustment_interval = adjustment_interval
        
        self.current_concurrency = min_concurrency
        self.last_adjustment = time.time()
        self.performance_history = deque(maxlen=100)
        
        self.logger = get_logger("agentic_redteam.performance.concurrency")
    
    def record_request(self, latency: float, success: bool) -> None:
        """
        Record request performance.
        
        Args:
            latency: Request latency in seconds
            success: Whether request was successful
        """
        self.performance_history.append({
            "latency": latency,
            "success": success,
            "timestamp": time.time(),
            "concurrency": self.current_concurrency
        })
    
    def should_adjust(self) -> bool:
        """Check if concurrency should be adjusted."""
        return (time.time() - self.last_adjustment) >= self.adjustment_interval
    
    def adjust_concurrency(self) -> int:
        """
        Adjust concurrency based on recent performance.
        
        Returns:
            New concurrency level
        """
        if not self.should_adjust() or len(self.performance_history) < 10:
            return self.current_concurrency
        
        # Calculate recent performance metrics
        recent_samples = [
            sample for sample in self.performance_history
            if time.time() - sample["timestamp"] < self.adjustment_interval
        ]
        
        if not recent_samples:
            return self.current_concurrency
        
        avg_latency = statistics.mean(sample["latency"] for sample in recent_samples)
        success_rate = statistics.mean(sample["success"] for sample in recent_samples)
        
        old_concurrency = self.current_concurrency
        
        # Adjustment logic
        if success_rate < 0.9:  # High error rate
            # Decrease concurrency
            self.current_concurrency = max(
                self.min_concurrency,
                int(self.current_concurrency * 0.8)
            )
        elif avg_latency > self.target_latency * 1.5:  # High latency
            # Decrease concurrency
            self.current_concurrency = max(
                self.min_concurrency,
                int(self.current_concurrency * 0.9)
            )
        elif avg_latency < self.target_latency * 0.5 and success_rate > 0.95:
            # Good performance, increase concurrency
            self.current_concurrency = min(
                self.max_concurrency,
                int(self.current_concurrency * 1.1)
            )
        
        if self.current_concurrency != old_concurrency:
            self.logger.info(
                f"Adjusted concurrency: {old_concurrency} -> {self.current_concurrency} "
                f"(latency: {avg_latency:.2f}s, success_rate: {success_rate:.2f})"
            )
        
        self.last_adjustment = time.time()
        return self.current_concurrency
    
    def get_current_concurrency(self) -> int:
        """Get current concurrency level."""
        return self.current_concurrency


class BatchProcessor:
    """
    Batch processor for efficient handling of multiple requests.
    """
    
    def __init__(self, 
                 batch_size: int = 10,
                 max_wait_time: float = 1.0,
                 max_concurrency: int = 5):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Maximum batch size
            max_wait_time: Maximum time to wait for batch to fill
            max_concurrency: Maximum concurrent batches
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrency = max_concurrency
        
        self.pending_requests = []
        self.pending_futures = []
        self.last_batch_time = time.time()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        
        self.logger = get_logger("agentic_redteam.performance.batch")
    
    async def add_request(self, request_data: Any, processor_func: Callable) -> Any:
        """
        Add request to batch processing queue.
        
        Args:
            request_data: Request data
            processor_func: Function to process the request
            
        Returns:
            Processing result
        """
        # Create future for this request
        future = asyncio.Future()
        
        self.pending_requests.append((request_data, processor_func))
        self.pending_futures.append(future)
        
        # Check if we should process batch
        should_process = (
            len(self.pending_requests) >= self.batch_size or
            time.time() - self.last_batch_time >= self.max_wait_time
        )
        
        if should_process:
            await self._process_batch()
        
        return await future
    
    async def _process_batch(self) -> None:
        """Process current batch of requests."""
        if not self.pending_requests:
            return
        
        async with self.semaphore:
            requests = self.pending_requests[:]
            futures = self.pending_futures[:]
            
            # Clear pending lists
            self.pending_requests.clear()
            self.pending_futures.clear()
            self.last_batch_time = time.time()
            
            self.logger.debug(f"Processing batch of {len(requests)} requests")
            
            # Process requests concurrently
            tasks = []
            for (request_data, processor_func), future in zip(requests, futures):
                task = asyncio.create_task(self._process_single_request(
                    request_data, processor_func, future
                ))
                tasks.append(task)
            
            # Wait for all requests to complete
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_request(self, request_data: Any, 
                                    processor_func: Callable, 
                                    future: asyncio.Future) -> None:
        """Process a single request and set future result."""
        try:
            if asyncio.iscoroutinefunction(processor_func):
                result = await processor_func(request_data)
            else:
                result = processor_func(request_data)
            
            if not future.done():
                future.set_result(result)
        
        except Exception as e:
            if not future.done():
                future.set_exception(e)


class ResourcePool:
    """
    Generic resource pool for managing expensive resources.
    """
    
    def __init__(self, 
                 resource_factory: Callable,
                 min_size: int = 1,
                 max_size: int = 10,
                 idle_timeout: float = 300.0):
        """
        Initialize resource pool.
        
        Args:
            resource_factory: Function to create new resources
            min_size: Minimum pool size
            max_size: Maximum pool size
            idle_timeout: Timeout for idle resources
        """
        self.resource_factory = resource_factory
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        
        self.available_resources = asyncio.Queue()
        self.in_use_resources = set()
        self.resource_created_times = {}
        self.total_created = 0
        
        self.logger = get_logger("agentic_redteam.performance.pool")
    
    async def initialize(self) -> None:
        """Initialize the resource pool."""
        for _ in range(self.min_size):
            resource = await self._create_resource()
            await self.available_resources.put(resource)
    
    async def _create_resource(self) -> Any:
        """Create a new resource."""
        if self.total_created >= self.max_size:
            raise RuntimeError("Resource pool exhausted")
        
        resource = self.resource_factory()
        self.resource_created_times[id(resource)] = time.time()
        self.total_created += 1
        
        self.logger.debug(f"Created new resource (total: {self.total_created})")
        return resource
    
    async def acquire(self, timeout: float = 30.0) -> Any:
        """
        Acquire a resource from the pool.
        
        Args:
            timeout: Timeout for acquiring resource
            
        Returns:
            Resource from pool
        """
        try:
            # Try to get available resource
            resource = await asyncio.wait_for(
                self.available_resources.get(), 
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Try to create new resource if under limit
            if self.total_created < self.max_size:
                resource = await self._create_resource()
            else:
                raise RuntimeError("Resource pool timeout")
        
        self.in_use_resources.add(resource)
        return resource
    
    async def release(self, resource: Any) -> None:
        """
        Release a resource back to the pool.
        
        Args:
            resource: Resource to release
        """
        if resource in self.in_use_resources:
            self.in_use_resources.remove(resource)
            
            # Check if resource is too old
            resource_age = time.time() - self.resource_created_times.get(id(resource), 0)
            
            if resource_age > self.idle_timeout:
                # Dispose of old resource
                await self._dispose_resource(resource)
            else:
                # Return to available pool
                await self.available_resources.put(resource)
    
    async def _dispose_resource(self, resource: Any) -> None:
        """Dispose of a resource."""
        resource_id = id(resource)
        if resource_id in self.resource_created_times:
            del self.resource_created_times[resource_id]
        
        self.total_created -= 1
        
        # Cleanup resource if it has cleanup method
        if hasattr(resource, 'cleanup'):
            try:
                if asyncio.iscoroutinefunction(resource.cleanup):
                    await resource.cleanup()
                else:
                    resource.cleanup()
            except Exception as e:
                self.logger.warning(f"Resource cleanup failed: {e}")
        
        self.logger.debug(f"Disposed resource (total: {self.total_created})")
    
    async def cleanup(self) -> None:
        """Clean up all resources in the pool."""
        # Clean up available resources
        while not self.available_resources.empty():
            try:
                resource = self.available_resources.get_nowait()
                await self._dispose_resource(resource)
            except asyncio.QueueEmpty:
                break
        
        # Clean up in-use resources (force cleanup)
        for resource in list(self.in_use_resources):
            await self._dispose_resource(resource)
        
        self.in_use_resources.clear()
        self.logger.info("Resource pool cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resource pool statistics."""
        return {
            "total_created": self.total_created,
            "available": self.available_resources.qsize(),
            "in_use": len(self.in_use_resources),
            "min_size": self.min_size,
            "max_size": self.max_size,
            "utilization": len(self.in_use_resources) / max(self.max_size, 1)
        }


class PerformanceOptimizer:
    """
    Main performance optimizer that coordinates all optimization strategies.
    """
    
    def __init__(self):
        """Initialize performance optimizer."""
        self.profiler = get_profiler()
        self.concurrency_controller = AdaptiveConcurrencyController()
        self.batch_processor = BatchProcessor()
        self.resource_pools: Dict[str, ResourcePool] = {}
        
        self.logger = get_logger("agentic_redteam.performance.optimizer")
        
        # Start background optimization task
        self._optimization_task = None
    
    async def start_optimization(self) -> None:
        """Start background optimization processes."""
        if self._optimization_task is None:
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            self.logger.info("Performance optimization started")
    
    async def stop_optimization(self) -> None:
        """Stop background optimization processes."""
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            self._optimization_task = None
            self.logger.info("Performance optimization stopped")
    
    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while True:
            try:
                # Adjust concurrency based on performance
                self.concurrency_controller.adjust_concurrency()
                
                # Detect performance issues
                issues = self.profiler.detect_performance_issues()
                if issues:
                    self.logger.warning(f"Detected {len(issues)} performance issues")
                    for issue in issues:
                        self.logger.warning(f"Performance issue: {issue}")
                
                # Clean up old metrics
                # (This would be implemented based on specific cleanup needs)
                
                await asyncio.sleep(30)  # Run every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    def create_resource_pool(self, name: str, resource_factory: Callable,
                           min_size: int = 1, max_size: int = 10) -> ResourcePool:
        """
        Create a named resource pool.
        
        Args:
            name: Pool name
            resource_factory: Function to create resources
            min_size: Minimum pool size
            max_size: Maximum pool size
            
        Returns:
            Resource pool instance
        """
        pool = ResourcePool(resource_factory, min_size, max_size)
        self.resource_pools[name] = pool
        return pool
    
    def get_resource_pool(self, name: str) -> Optional[ResourcePool]:
        """Get resource pool by name."""
        return self.resource_pools.get(name)
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Returns:
            Performance report
        """
        report = {
            "timestamp": time.time(),
            "profiler_stats": self.profiler.get_all_stats(),
            "performance_issues": self.profiler.detect_performance_issues(),
            "concurrency": {
                "current": self.concurrency_controller.get_current_concurrency(),
                "min": self.concurrency_controller.min_concurrency,
                "max": self.concurrency_controller.max_concurrency,
                "target_latency": self.concurrency_controller.target_latency
            },
            "resource_pools": {
                name: pool.get_stats() 
                for name, pool in self.resource_pools.items()
            }
        }
        
        return report


# Global optimizer instance
_global_optimizer: Optional[PerformanceOptimizer] = None


def get_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer()
    return _global_optimizer