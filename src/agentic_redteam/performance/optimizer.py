"""
Performance optimization engine for Agentic RedTeam Radar.

Provides intelligent optimization of scanning workflows, resource allocation,
and concurrent processing for maximum throughput and efficiency.
"""

import asyncio
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import psutil
import gc

from ..utils.logger import get_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring and optimization."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    cpu_usage_start: float = 0.0
    cpu_usage_end: float = 0.0
    memory_usage_start: float = 0.0
    memory_usage_end: float = 0.0
    concurrent_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    network_requests: int = 0
    
    def __post_init__(self):
        """Initialize system metrics."""
        self.cpu_usage_start = psutil.cpu_percent()
        self.memory_usage_start = psutil.virtual_memory().percent
    
    def finalize(self):
        """Finalize metrics collection."""
        self.end_time = time.time()
        self.cpu_usage_end = psutil.cpu_percent()
        self.memory_usage_end = psutil.virtual_memory().percent
    
    @property
    def duration(self) -> float:
        """Calculate total duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate task success rate."""
        total_tasks = self.completed_tasks + self.failed_tasks
        if total_tasks == 0:
            return 0.0
        return self.completed_tasks / total_tasks
    
    @property
    def throughput(self) -> float:
        """Calculate tasks per second."""
        duration = self.duration
        if duration == 0:
            return 0.0
        return self.completed_tasks / duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'duration': self.duration,
            'cpu_usage_delta': self.cpu_usage_end - self.cpu_usage_start,
            'memory_usage_delta': self.memory_usage_end - self.memory_usage_start,
            'concurrent_tasks': self.concurrent_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'success_rate': self.success_rate,
            'throughput': self.throughput,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0.0,
            'network_requests': self.network_requests
        }


class AdaptiveResourceManager:
    """
    Adaptive resource management for optimal performance.
    
    Automatically adjusts resource allocation based on system load,
    task complexity, and performance metrics.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize resource manager.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.logger = get_logger(__name__)
        
        # System information
        self.cpu_count = psutil.cpu_count()
        self.total_memory = psutil.virtual_memory().total
        
        # Resource limits
        self.max_workers = max_workers or min(32, (self.cpu_count or 1) + 4)
        self.max_memory_usage = 0.8  # 80% of total memory
        self.max_cpu_usage = 0.9     # 90% CPU utilization
        
        # Dynamic resource allocation
        self.current_workers = min(4, self.max_workers)
        self.task_queue = PriorityQueue()
        self.active_tasks = {}
        self.resource_lock = threading.Lock()
        
        # Performance tracking
        self.metrics_history = []
        self.optimization_enabled = True
        
        self.logger.info(f"Resource manager initialized: {self.current_workers}/{self.max_workers} workers")
    
    def get_optimal_concurrency(self) -> int:
        """
        Calculate optimal concurrency level based on current system state.
        
        Returns:
            Optimal number of concurrent tasks
        """
        try:
            # Get current system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Base concurrency on CPU cores
            base_concurrency = self.cpu_count
            
            # Adjust based on CPU usage
            if cpu_percent > 80:
                cpu_factor = 0.5  # Reduce concurrency if CPU is high
            elif cpu_percent < 30:
                cpu_factor = 1.5  # Increase concurrency if CPU is low
            else:
                cpu_factor = 1.0
            
            # Adjust based on memory usage
            if memory_percent > 70:
                memory_factor = 0.7  # Reduce concurrency if memory is high
            elif memory_percent < 40:
                memory_factor = 1.2  # Increase concurrency if memory is low
            else:
                memory_factor = 1.0
            
            # Calculate optimal concurrency
            optimal = int(base_concurrency * cpu_factor * memory_factor)
            optimal = max(1, min(optimal, self.max_workers))
            
            self.logger.debug(f"Optimal concurrency: {optimal} (CPU: {cpu_percent}%, Memory: {memory_percent}%)")
            return optimal
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal concurrency: {e}")
            return self.current_workers
    
    def should_scale_up(self) -> bool:
        """Determine if we should increase resource allocation."""
        if not self.optimization_enabled:
            return False
        
        try:
            # Check system resources
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            # Check if we have capacity to scale up
            can_scale_cpu = cpu_percent < (self.max_cpu_usage * 100)
            can_scale_memory = memory_percent < (self.max_memory_usage * 100)
            can_scale_workers = self.current_workers < self.max_workers
            
            # Check if there's demand (queued tasks)
            has_demand = not self.task_queue.empty()
            
            return can_scale_cpu and can_scale_memory and can_scale_workers and has_demand
            
        except Exception as e:
            self.logger.error(f"Error checking scale up conditions: {e}")
            return False
    
    def should_scale_down(self) -> bool:
        """Determine if we should decrease resource allocation."""
        if not self.optimization_enabled:
            return False
        
        try:
            # Check if we have idle workers
            active_count = len(self.active_tasks)
            idle_workers = self.current_workers - active_count
            
            # Scale down if more than half workers are idle
            should_scale = idle_workers > (self.current_workers // 2) and self.current_workers > 1
            
            return should_scale
            
        except Exception as e:
            self.logger.error(f"Error checking scale down conditions: {e}")
            return False
    
    def adjust_resources(self):
        """Dynamically adjust resource allocation."""
        with self.resource_lock:
            try:
                if self.should_scale_up():
                    new_workers = min(self.current_workers + 1, self.max_workers)
                    if new_workers > self.current_workers:
                        self.current_workers = new_workers
                        self.logger.info(f"Scaled up to {self.current_workers} workers")
                
                elif self.should_scale_down():
                    new_workers = max(self.current_workers - 1, 1)
                    if new_workers < self.current_workers:
                        self.current_workers = new_workers
                        self.logger.info(f"Scaled down to {self.current_workers} workers")
                
            except Exception as e:
                self.logger.error(f"Error adjusting resources: {e}")


class ConcurrentTaskExecutor:
    """
    High-performance concurrent task executor with intelligent scheduling.
    
    Provides optimized concurrent execution with resource management,
    priority scheduling, and automatic error recovery.
    """
    
    def __init__(self, resource_manager: Optional[AdaptiveResourceManager] = None):
        """
        Initialize concurrent executor.
        
        Args:
            resource_manager: Optional resource manager instance
        """
        self.logger = get_logger(__name__)
        self.resource_manager = resource_manager or AdaptiveResourceManager()
        
        # Execution state
        self.executor: Optional[ThreadPoolExecutor] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.active_futures = set()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.task_timings = {}
        
        # Error handling
        self.max_retries = 3
        self.retry_delay = 1.0
        self.error_callback: Optional[Callable] = None
    
    async def execute_concurrent(
        self,
        tasks: List[Tuple[Callable, tuple, dict]],
        max_concurrency: Optional[int] = None,
        priority_func: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Execute tasks concurrently with intelligent resource management.
        
        Args:
            tasks: List of (function, args, kwargs) tuples
            max_concurrency: Maximum concurrent tasks (auto-optimized if None)
            priority_func: Function to determine task priority
            progress_callback: Callback for progress updates
            
        Returns:
            List of task results
        """
        if not tasks:
            return []
        
        # Determine optimal concurrency
        if max_concurrency is None:
            max_concurrency = self.resource_manager.get_optimal_concurrency()
        
        self.logger.info(f"Executing {len(tasks)} tasks with concurrency {max_concurrency}")
        
        # Initialize semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrency)
        
        # Create prioritized task list
        if priority_func:
            prioritized_tasks = [(priority_func(task), i, task) for i, task in enumerate(tasks)]
            prioritized_tasks.sort(key=lambda x: x[0], reverse=True)
            tasks = [task for _, _, task in prioritized_tasks]
        
        # Execute tasks concurrently
        results = [None] * len(tasks)
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_single_task(index: int, task: Tuple[Callable, tuple, dict]):
            """Execute a single task with error handling and metrics."""
            func, args, kwargs = task
            
            async with semaphore:
                self.metrics.concurrent_tasks += 1
                start_time = time.time()
                
                try:
                    # Execute task
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(func, *args, **kwargs)
                    
                    # Record success
                    results[index] = result
                    self.metrics.completed_tasks += 1
                    
                    # Track timing
                    duration = time.time() - start_time
                    self.task_timings[index] = duration
                    
                    # Progress callback
                    if progress_callback:
                        await asyncio.to_thread(progress_callback, {
                            'completed': self.metrics.completed_tasks,
                            'total': len(tasks),
                            'current_task': index,
                            'duration': duration
                        })
                    
                    return result
                    
                except Exception as e:
                    self.logger.error(f"Task {index} failed: {e}")
                    self.metrics.failed_tasks += 1
                    
                    # Error callback
                    if self.error_callback:
                        await asyncio.to_thread(self.error_callback, index, e)
                    
                    return None
                
                finally:
                    self.metrics.concurrent_tasks -= 1
        
        # Execute all tasks
        task_coroutines = [
            execute_single_task(i, task) for i, task in enumerate(tasks)
        ]
        
        await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # Finalize metrics
        self.metrics.finalize()
        
        self.logger.info(f"Completed execution: {self.metrics.completed_tasks}/{len(tasks)} successful")
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        base_metrics = self.metrics.to_dict()
        
        # Add task timing statistics
        if self.task_timings:
            timings = list(self.task_timings.values())
            base_metrics.update({
                'avg_task_duration': sum(timings) / len(timings),
                'min_task_duration': min(timings),
                'max_task_duration': max(timings),
                'total_task_time': sum(timings)
            })
        
        # Add resource utilization
        base_metrics.update({
            'current_workers': self.resource_manager.current_workers,
            'max_workers': self.resource_manager.max_workers,
            'cpu_count': self.resource_manager.cpu_count,
            'worker_utilization': self.resource_manager.current_workers / self.resource_manager.max_workers
        })
        
        return base_metrics


class PerformanceOptimizer:
    """
    Advanced performance optimizer for scanning operations.
    
    Provides intelligent optimization of scanning workflows through
    machine learning, caching strategies, and resource management.
    """
    
    def __init__(self):
        """Initialize performance optimizer."""
        self.logger = get_logger(__name__)
        self.resource_manager = AdaptiveResourceManager()
        self.executor = ConcurrentTaskExecutor(self.resource_manager)
        
        # Optimization strategies
        self.strategies = {
            'batch_processing': True,
            'intelligent_caching': True,
            'adaptive_scheduling': True,
            'memory_optimization': True,
            'connection_pooling': True
        }
        
        # Performance history for learning
        self.performance_history = []
        self.optimization_model = None
        
        self.logger.info("Performance optimizer initialized")
    
    def optimize_scan_workflow(self, config, patterns, agent_count):
        """
        Optimize scanning workflow based on configuration and targets.
        
        Args:
            config: Scanner configuration
            patterns: Attack patterns to execute
            agent_count: Number of agents to scan
            
        Returns:
            Optimized configuration and execution plan
        """
        self.logger.info(f"Optimizing workflow for {agent_count} agents, {len(patterns)} patterns")
        
        # Calculate optimal batch sizes
        optimal_batch_size = self._calculate_optimal_batch_size(len(patterns), agent_count)
        
        # Determine concurrency levels
        optimal_concurrency = self.resource_manager.get_optimal_concurrency()
        
        # Create execution plan
        execution_plan = {
            'batch_size': optimal_batch_size,
            'max_concurrency': optimal_concurrency,
            'enable_caching': config.cache_results,
            'memory_optimization': self.strategies['memory_optimization'],
            'estimated_duration': self._estimate_execution_time(patterns, agent_count)
        }
        
        self.logger.info(f"Optimized execution plan: {execution_plan}")
        return execution_plan
    
    def _calculate_optimal_batch_size(self, pattern_count: int, agent_count: int) -> int:
        """Calculate optimal batch size for processing."""
        # Base batch size on available memory and CPU cores
        base_batch_size = max(1, self.resource_manager.cpu_count * 2)
        
        # Adjust based on task complexity
        complexity_factor = min(pattern_count * agent_count, 100) / 100
        adjusted_batch_size = int(base_batch_size * (1 + complexity_factor))
        
        # Ensure reasonable bounds
        return max(1, min(adjusted_batch_size, 50))
    
    def _estimate_execution_time(self, patterns: List, agent_count: int) -> float:
        """Estimate execution time based on historical data."""
        if not self.performance_history:
            # Default estimation
            base_time_per_pattern = 0.1  # seconds
            return len(patterns) * agent_count * base_time_per_pattern
        
        # Use historical data for more accurate estimation
        recent_metrics = self.performance_history[-10:]  # Last 10 runs
        avg_throughput = sum(m.get('throughput', 1) for m in recent_metrics) / len(recent_metrics)
        
        total_tasks = len(patterns) * agent_count
        estimated_time = total_tasks / max(avg_throughput, 1)
        
        return estimated_time
    
    def enable_memory_optimization(self):
        """Enable aggressive memory optimization."""
        self.logger.info("Enabling memory optimization")
        
        # Force garbage collection
        gc.collect()
        
        # Configure garbage collection thresholds
        gc.set_threshold(100, 10, 10)  # More aggressive collection
        
        # Enable memory optimization strategies
        self.strategies['memory_optimization'] = True
    
    def cleanup_resources(self):
        """Clean up resources and perform maintenance."""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clear performance history if too large
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-50:]  # Keep last 50
            
            # Reset resource manager if needed
            if hasattr(self.resource_manager, 'active_tasks'):
                self.resource_manager.active_tasks.clear()
            
            self.logger.debug("Resource cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        report = {
            'optimizer_status': 'active',
            'current_strategies': self.strategies.copy(),
            'resource_manager': {
                'current_workers': self.resource_manager.current_workers,
                'max_workers': self.resource_manager.max_workers,
                'cpu_count': self.resource_manager.cpu_count
            },
            'performance_history_size': len(self.performance_history),
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        try:
            # Check system resources
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent()
            
            if memory_percent > 80:
                recommendations.append("Consider reducing batch size due to high memory usage")
            
            if cpu_percent < 30:
                recommendations.append("System has spare CPU capacity - consider increasing concurrency")
            elif cpu_percent > 90:
                recommendations.append("CPU utilization is high - consider reducing concurrency")
            
            # Check performance history
            if len(self.performance_history) > 5:
                recent_throughput = [m.get('throughput', 0) for m in self.performance_history[-5:]]
                if recent_throughput and max(recent_throughput) / min(recent_throughput) > 2:
                    recommendations.append("Performance variance detected - consider stabilizing workload")
            
            if not recommendations:
                recommendations.append("System is performing optimally")
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to system error")
        
        return recommendations