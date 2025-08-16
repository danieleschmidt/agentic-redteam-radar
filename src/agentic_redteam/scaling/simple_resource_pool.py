"""
Simple resource pool management without external dependencies.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum

T = TypeVar('T')


class PoolStrategy(Enum):
    """Resource pool strategies."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"


@dataclass
class SimplePoolMetrics:
    """Simple resource pool metrics."""
    total_resources: int = 0
    active_resources: int = 0
    idle_resources: int = 0
    total_acquisitions: int = 0
    successful_acquisitions: int = 0
    timestamp: float = field(default_factory=time.time)


class SimpleResourcePool(Generic[T]):
    """
    Simple resource pool for efficient resource management.
    
    Provides basic resource pooling with minimal dependencies.
    """
    
    def __init__(self, name: str, resource_factory: Callable[[], T],
                 min_size: int = 1, max_size: int = 10, 
                 strategy: PoolStrategy = PoolStrategy.DYNAMIC):
        self.name = name
        self.resource_factory = resource_factory
        self.min_size = min_size
        self.max_size = max_size
        self.strategy = strategy
        
        # Resource management
        self._pool: List[T] = []
        self._active_resources: set = set()
        self._lock = asyncio.Lock()
        
        # Metrics tracking
        self._metrics = SimplePoolMetrics()
        
        # Initialize pool
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the pool is initialized."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            for _ in range(self.min_size):
                try:
                    resource = self.resource_factory()
                    self._pool.append(resource)
                    self._metrics.total_resources += 1
                except Exception:
                    # Ignore initialization errors for simplicity
                    pass
            
            self._initialized = True
    
    async def acquire(self, timeout: float = 30.0) -> T:
        """Acquire a resource from the pool."""
        await self._ensure_initialized()
        
        try:
            async with self._lock:
                # Try to get existing resource
                if self._pool:
                    resource = self._pool.pop()
                    self._active_resources.add(id(resource))
                    self._metrics.active_resources += 1
                    self._metrics.idle_resources = len(self._pool)
                    self._metrics.total_acquisitions += 1
                    self._metrics.successful_acquisitions += 1
                    
                    return resource
                
                # Create new resource if under limit
                if self._metrics.total_resources < self.max_size:
                    try:
                        resource = self.resource_factory()
                        self._active_resources.add(id(resource))
                        self._metrics.total_resources += 1
                        self._metrics.active_resources += 1
                        self._metrics.total_acquisitions += 1
                        self._metrics.successful_acquisitions += 1
                        
                        return resource
                    except Exception:
                        pass
                
                # Pool exhausted
                self._metrics.total_acquisitions += 1
                raise ResourceExhaustedError(f"Pool '{self.name}' exhausted")
                
        except asyncio.TimeoutError:
            self._metrics.total_acquisitions += 1
            raise ResourceTimeoutError(f"Timeout acquiring resource from pool '{self.name}'")
    
    async def release(self, resource: T):
        """Release a resource back to the pool."""
        async with self._lock:
            resource_id = id(resource)
            
            if resource_id not in self._active_resources:
                return  # Resource not from this pool
            
            self._active_resources.remove(resource_id)
            self._metrics.active_resources -= 1
            
            # Return to pool if under min size or strategy allows
            if (len(self._pool) < self.min_size or 
                (self.strategy == PoolStrategy.DYNAMIC and len(self._pool) < self.max_size)):
                self._pool.append(resource)
                self._metrics.idle_resources = len(self._pool)
            else:
                # Remove excess resource
                self._metrics.total_resources -= 1
    
    async def clear(self):
        """Clear all resources from the pool."""
        async with self._lock:
            self._pool.clear()
            self._active_resources.clear()
            self._metrics = SimplePoolMetrics()
            self._initialized = False
    
    def get_metrics(self) -> SimplePoolMetrics:
        """Get current pool metrics."""
        self._metrics.idle_resources = len(self._pool)
        self._metrics.timestamp = time.time()
        return self._metrics
    
    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._pool)
    
    @property
    def active_count(self) -> int:
        """Get number of active resources."""
        return len(self._active_resources)


class ResourceExhaustedError(Exception):
    """Raised when resource pool is exhausted."""
    pass


class ResourceTimeoutError(Exception):
    """Raised when resource acquisition times out."""
    pass


class ConcurrencyManager:
    """
    Simple concurrency management for scaling operations.
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks: set = set()
    
    async def run_concurrent(self, coroutines: List[Any]) -> List[Any]:
        """Run coroutines with concurrency control."""
        async def run_with_semaphore(coro):
            async with self.semaphore:
                return await coro
        
        # Create tasks with semaphore control
        tasks = [asyncio.create_task(run_with_semaphore(coro)) for coro in coroutines]
        
        try:
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        finally:
            # Clean up any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
    
    async def throttled_execution(self, func: Callable, items: List[Any], 
                                batch_size: int = None) -> List[Any]:
        """Execute function on items with throttling."""
        if batch_size is None:
            batch_size = self.max_concurrent
        
        results = []
        
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_coroutines = [func(item) for item in batch]
            
            batch_results = await self.run_concurrent(batch_coroutines)
            results.extend(batch_results)
        
        return results


class LoadBalancer:
    """
    Simple load balancer for distributing work across resources.
    """
    
    def __init__(self, resources: List[Any]):
        self.resources = resources
        self.current_index = 0
        self.request_counts = {id(r): 0 for r in resources}
    
    def get_next_resource(self) -> Any:
        """Get next resource using round-robin."""
        if not self.resources:
            raise ValueError("No resources available")
        
        resource = self.resources[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.resources)
        self.request_counts[id(resource)] += 1
        
        return resource
    
    def get_least_used_resource(self) -> Any:
        """Get resource with least usage."""
        if not self.resources:
            raise ValueError("No resources available")
        
        # Find resource with minimum requests
        min_requests = min(self.request_counts.values())
        for resource in self.resources:
            if self.request_counts[id(resource)] == min_requests:
                self.request_counts[id(resource)] += 1
                return resource
        
        # Fallback to first resource
        resource = self.resources[0]
        self.request_counts[id(resource)] += 1
        return resource
    
    def add_resource(self, resource: Any):
        """Add a new resource to the load balancer."""
        self.resources.append(resource)
        self.request_counts[id(resource)] = 0
    
    def remove_resource(self, resource: Any):
        """Remove a resource from the load balancer."""
        if resource in self.resources:
            self.resources.remove(resource)
            self.request_counts.pop(id(resource), None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        total_requests = sum(self.request_counts.values())
        
        return {
            "total_resources": len(self.resources),
            "total_requests": total_requests,
            "avg_requests_per_resource": total_requests / max(len(self.resources), 1),
            "request_distribution": dict(self.request_counts)
        }