"""
Resource pool management for efficient resource utilization.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger

T = TypeVar('T')


class PoolStrategy(Enum):
    """Resource pool strategies."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    ELASTIC = "elastic"


@dataclass
class PoolMetrics:
    """Resource pool metrics."""
    total_resources: int = 0
    active_resources: int = 0
    idle_resources: int = 0
    pending_requests: int = 0
    total_acquisitions: int = 0
    successful_acquisitions: int = 0
    avg_wait_time_ms: float = 0.0
    avg_utilization: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ResourcePool(Generic[T]):
    """
    Advanced resource pool for efficient resource management.
    
    Provides thread-safe resource pooling with dynamic scaling,
    health monitoring, and performance optimization.
    """
    
    def __init__(self, name: str, resource_factory: Callable[[], T],
                 min_size: int = 1, max_size: int = 10, 
                 strategy: PoolStrategy = PoolStrategy.DYNAMIC):
        self.name = name
        self.resource_factory = resource_factory
        self.min_size = min_size
        self.max_size = max_size
        self.strategy = strategy
        
        self.logger = get_logger(f"agentic_redteam.scaling.resource_pool.{name}")
        
        # Resource management
        self._pool: List[T] = []
        self._active_resources: set = set()
        self._lock = asyncio.Lock()
        
        # Request tracking
        self._pending_requests: List[asyncio.Future] = []
        self._metrics = PoolMetrics()
        
        # Health monitoring
        self._health_check_function: Optional[Callable[[T], bool]] = None
        self._cleanup_function: Optional[Callable[[T], None]] = None
        
        # Initialize pool
        asyncio.create_task(self._initialize_pool())
    
    async def _initialize_pool(self):
        """Initialize the resource pool with minimum resources."""
        async with self._lock:
            for _ in range(self.min_size):
                try:
                    resource = self.resource_factory()
                    self._pool.append(resource)
                    self._metrics.total_resources += 1
                except Exception as e:
                    self.logger.error(f"Failed to create initial resource: {e}")
        
        self.logger.info(f"Initialized pool '{self.name}' with {len(self._pool)} resources")
    
    async def acquire(self, timeout: float = 30.0) -> T:
        """Acquire a resource from the pool."""
        start_time = time.time()
        
        try:
            async with asyncio.wait_for(self._lock, timeout=timeout):
                # Try to get existing resource
                if self._pool:
                    resource = self._pool.pop()
                    self._active_resources.add(id(resource))
                    self._metrics.active_resources += 1
                    self._metrics.idle_resources = len(self._pool)
                    self._metrics.total_acquisitions += 1
                    self._metrics.successful_acquisitions += 1
                    
                    wait_time = (time.time() - start_time) * 1000
                    self._update_avg_wait_time(wait_time)
                    
                    return resource
                
                # Create new resource if under limit
                if self._metrics.total_resources < self.max_size:
                    resource = self.resource_factory()
                    self._active_resources.add(id(resource))
                    self._metrics.total_resources += 1
                    self._metrics.active_resources += 1
                    self._metrics.total_acquisitions += 1
                    self._metrics.successful_acquisitions += 1
                    
                    return resource
                
                # Wait for resource to become available
                future: asyncio.Future[T] = asyncio.Future()
                self._pending_requests.append(future)
                self._metrics.pending_requests = len(self._pending_requests)
            
            # Wait outside the lock
            resource = await asyncio.wait_for(future, timeout=timeout - (time.time() - start_time))
            
            wait_time = (time.time() - start_time) * 1000
            self._update_avg_wait_time(wait_time)
            
            return resource
        
        except asyncio.TimeoutError:
            self._metrics.total_acquisitions += 1
            raise asyncio.TimeoutError(f"Failed to acquire resource from pool '{self.name}' within {timeout}s")
    
    async def release(self, resource: T):
        """Release a resource back to the pool."""
        async with self._lock:
            resource_id = id(resource)
            
            if resource_id not in self._active_resources:
                self.logger.warning(f"Attempted to release resource not in active set")
                return
            
            self._active_resources.discard(resource_id)
            self._metrics.active_resources -= 1
            
            # Health check resource before returning to pool
            if self._health_check_function and not self._health_check_function(resource):
                self.logger.info("Resource failed health check, disposing")
                if self._cleanup_function:
                    try:
                        self._cleanup_function(resource)
                    except Exception as e:
                        self.logger.error(f"Error cleaning up resource: {e}")
                
                self._metrics.total_resources -= 1
                
                # Create replacement if needed
                if self._metrics.total_resources < self.min_size:
                    try:
                        replacement = self.resource_factory()
                        self._pool.append(replacement)
                        self._metrics.total_resources += 1
                        self._metrics.idle_resources = len(self._pool)
                    except Exception as e:
                        self.logger.error(f"Failed to create replacement resource: {e}")
                
                return
            
            # Return healthy resource to pool or fulfill pending request
            if self._pending_requests:
                future = self._pending_requests.pop(0)
                if not future.cancelled():
                    future.set_result(resource)
                    self._active_resources.add(resource_id)
                    self._metrics.active_resources += 1
                else:
                    # Future was cancelled, return to pool
                    self._pool.append(resource)
                    self._metrics.idle_resources = len(self._pool)
                
                self._metrics.pending_requests = len(self._pending_requests)
            else:
                # No pending requests, return to pool
                self._pool.append(resource)
                self._metrics.idle_resources = len(self._pool)
    
    def set_health_check(self, health_check: Callable[[T], bool]):
        """Set health check function for resources."""
        self._health_check_function = health_check
    
    def set_cleanup_function(self, cleanup: Callable[[T], None]):
        """Set cleanup function for disposing resources."""
        self._cleanup_function = cleanup
    
    def _update_avg_wait_time(self, wait_time_ms: float):
        """Update average wait time using exponential moving average."""
        alpha = 0.2  # Smoothing factor
        if self._metrics.avg_wait_time_ms == 0:
            self._metrics.avg_wait_time_ms = wait_time_ms
        else:
            self._metrics.avg_wait_time_ms = (1 - alpha) * self._metrics.avg_wait_time_ms + alpha * wait_time_ms
    
    async def resize_pool(self, new_min_size: int, new_max_size: int):
        """Resize the pool limits."""
        async with self._lock:
            old_min = self.min_size
            old_max = self.max_size
            
            self.min_size = new_min_size
            self.max_size = new_max_size
            
            # Adjust current pool size
            current_total = len(self._pool) + len(self._active_resources)
            
            # Add resources if below minimum
            while len(self._pool) + len(self._active_resources) < new_min_size:
                try:
                    resource = self.resource_factory()
                    self._pool.append(resource)
                    self._metrics.total_resources += 1
                except Exception as e:
                    self.logger.error(f"Failed to create resource during resize: {e}")
                    break
            
            # Remove excess idle resources if above maximum
            while (len(self._pool) + len(self._active_resources) > new_max_size and 
                   len(self._pool) > 0):
                resource = self._pool.pop()
                if self._cleanup_function:
                    try:
                        self._cleanup_function(resource)
                    except Exception as e:
                        self.logger.error(f"Error cleaning up resource during resize: {e}")
                self._metrics.total_resources -= 1
            
            self._metrics.idle_resources = len(self._pool)
            
            self.logger.info(f"Pool '{self.name}' resized: {old_min}-{old_max} -> {new_min_size}-{new_max_size}")
    
    async def drain_pool(self):
        """Drain all resources from the pool."""
        async with self._lock:
            while self._pool:
                resource = self._pool.pop()
                if self._cleanup_function:
                    try:
                        self._cleanup_function(resource)
                    except Exception as e:
                        self.logger.error(f"Error cleaning up resource during drain: {e}")
                self._metrics.total_resources -= 1
            
            # Cancel pending requests
            for future in self._pending_requests:
                if not future.cancelled():
                    future.cancel()
            
            self._pending_requests.clear()
            self._metrics.idle_resources = 0
            self._metrics.pending_requests = 0
            
            self.logger.info(f"Pool '{self.name}' drained")
    
    def get_metrics(self) -> PoolMetrics:
        """Get current pool metrics."""
        self._metrics.timestamp = time.time()
        
        # Calculate utilization
        if self._metrics.total_resources > 0:
            self._metrics.avg_utilization = self._metrics.active_resources / self._metrics.total_resources
        
        return self._metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed pool status."""
        metrics = self.get_metrics()
        
        return {
            'name': self.name,
            'strategy': self.strategy.value,
            'size_limits': {
                'min_size': self.min_size,
                'max_size': self.max_size
            },
            'current_state': {
                'total_resources': metrics.total_resources,
                'active_resources': metrics.active_resources,
                'idle_resources': metrics.idle_resources,
                'pending_requests': metrics.pending_requests
            },
            'performance': {
                'avg_wait_time_ms': metrics.avg_wait_time_ms,
                'avg_utilization': metrics.avg_utilization,
                'success_rate': metrics.successful_acquisitions / max(metrics.total_acquisitions, 1)
            },
            'health_monitoring': {
                'health_check_enabled': self._health_check_function is not None,
                'cleanup_enabled': self._cleanup_function is not None
            }
        }


class ResourceManager:
    """
    Manages multiple resource pools for different resource types.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.scaling.resource_manager")
        self.pools: Dict[str, ResourcePool] = {}
        
        # Global metrics
        self.total_acquisitions = 0
        self.total_releases = 0
        self.start_time = time.time()
    
    def create_pool(self, pool_name: str, resource_factory: Callable,
                   min_size: int = 1, max_size: int = 10,
                   strategy: PoolStrategy = PoolStrategy.DYNAMIC) -> ResourcePool:
        """Create a new resource pool."""
        if pool_name in self.pools:
            raise ValueError(f"Pool '{pool_name}' already exists")
        
        pool = ResourcePool(pool_name, resource_factory, min_size, max_size, strategy)
        self.pools[pool_name] = pool
        
        self.logger.info(f"Created resource pool '{pool_name}'")
        return pool
    
    def get_pool(self, pool_name: str) -> Optional[ResourcePool]:
        """Get a resource pool by name."""
        return self.pools.get(pool_name)
    
    async def acquire_resource(self, pool_name: str, timeout: float = 30.0):
        """Acquire a resource from the named pool."""
        if pool_name not in self.pools:
            raise ValueError(f"Pool '{pool_name}' does not exist")
        
        resource = await self.pools[pool_name].acquire(timeout)
        self.total_acquisitions += 1
        return resource
    
    async def release_resource(self, pool_name: str, resource):
        """Release a resource back to the named pool."""
        if pool_name not in self.pools:
            raise ValueError(f"Pool '{pool_name}' does not exist")
        
        await self.pools[pool_name].release(resource)
        self.total_releases += 1
    
    async def resize_pool(self, pool_name: str, new_min_size: int, new_max_size: int):
        """Resize a pool."""
        if pool_name not in self.pools:
            raise ValueError(f"Pool '{pool_name}' does not exist")
        
        await self.pools[pool_name].resize_pool(new_min_size, new_max_size)
    
    async def remove_pool(self, pool_name: str):
        """Remove a pool and clean up its resources."""
        if pool_name not in self.pools:
            return
        
        await self.pools[pool_name].drain_pool()
        del self.pools[pool_name]
        
        self.logger.info(f"Removed resource pool '{pool_name}'")
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global resource management metrics."""
        uptime_hours = (time.time() - self.start_time) / 3600
        
        total_resources = sum(pool.get_metrics().total_resources for pool in self.pools.values())
        active_resources = sum(pool.get_metrics().active_resources for pool in self.pools.values())
        pending_requests = sum(pool.get_metrics().pending_requests for pool in self.pools.values())
        
        return {
            'total_pools': len(self.pools),
            'uptime_hours': uptime_hours,
            'global_stats': {
                'total_acquisitions': self.total_acquisitions,
                'total_releases': self.total_releases,
                'acquisitions_per_hour': self.total_acquisitions / max(uptime_hours, 0.01)
            },
            'resource_summary': {
                'total_resources': total_resources,
                'active_resources': active_resources,
                'pending_requests': pending_requests,
                'utilization': active_resources / max(total_resources, 1)
            },
            'pools': {
                name: pool.get_status() for name, pool in self.pools.items()
            }
        }