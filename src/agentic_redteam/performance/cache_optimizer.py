"""
Advanced caching and performance optimization for Agentic RedTeam Radar.

Implements intelligent caching strategies, connection pooling, and performance
monitoring to optimize the security testing framework.
"""

import asyncio
import hashlib
import pickle
import time
import weakref
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
import logging
from collections import OrderedDict
import threading

from ..utils.logger import get_logger


T = TypeVar('T')


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property 
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl
    
    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheEvictionPolicy(ABC):
    """Abstract base class for cache eviction policies."""
    
    @abstractmethod
    def select_victim(self, cache_entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select a cache entry for eviction."""
        pass


class LRUEvictionPolicy(CacheEvictionPolicy):
    """Least Recently Used eviction policy."""
    
    def select_victim(self, cache_entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select least recently used entry for eviction."""
        if not cache_entries:
            return None
        
        oldest_key = min(
            cache_entries.keys(),
            key=lambda k: cache_entries[k].accessed_at
        )
        return oldest_key


class LFUEvictionPolicy(CacheEvictionPolicy):
    """Least Frequently Used eviction policy."""
    
    def select_victim(self, cache_entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select least frequently used entry for eviction."""
        if not cache_entries:
            return None
        
        least_used_key = min(
            cache_entries.keys(),
            key=lambda k: cache_entries[k].access_count
        )
        return least_used_key


class TTLEvictionPolicy(CacheEvictionPolicy):
    """Time-to-Live based eviction policy."""
    
    def select_victim(self, cache_entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select expired entry for eviction."""
        expired_keys = [
            key for key, entry in cache_entries.items()
            if entry.is_expired()
        ]
        
        if expired_keys:
            # Return the most expired entry
            return min(
                expired_keys,
                key=lambda k: cache_entries[k].created_at
            )
        
        return None


class AdaptiveCache(Generic[T]):
    """High-performance adaptive cache with multiple eviction policies."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        eviction_policy: Optional[CacheEvictionPolicy] = None,
        enable_stats: bool = True
    ):
        """
        Initialize adaptive cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
            eviction_policy: Cache eviction policy
            enable_stats: Whether to collect statistics
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()
        self.enable_stats = enable_stats
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats() if enable_stats else None
        self.logger = get_logger(__name__)
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Convert arguments to a serializable string representation
        try:
            # Convert args to string representations
            arg_strs = []
            for arg in args:
                if hasattr(arg, '__dict__'):
                    # For objects, use string representation
                    arg_strs.append(str(arg))
                else:
                    arg_strs.append(repr(arg))
            
            # Convert kwargs to sorted string pairs
            kwarg_strs = []
            for k, v in sorted(kwargs.items()):
                if hasattr(v, '__dict__'):
                    kwarg_strs.append(f"{k}={str(v)}")
                else:
                    kwarg_strs.append(f"{k}={repr(v)}")
            
            key_str = f"args:{'|'.join(arg_strs)}|kwargs:{'|'.join(kwarg_strs)}"
            return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        except Exception:
            # Fallback to a simple timestamp-based key
            return hashlib.sha256(f"{time.time()}:{len(args)}:{len(kwargs)}".encode('utf-8')).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of cached value."""
        try:
            # Safer size calculation for complex objects
            if hasattr(value, '__len__'):
                return len(str(value))
            elif hasattr(value, '__dict__'):
                return len(str(value.__dict__))
            else:
                return len(str(value))
        except Exception:
            # Fallback for any objects
            return 1024  # Assume 1KB
    
    def _evict_if_needed(self) -> None:
        """Evict entries if cache is full."""
        while len(self._cache) >= self.max_size:
            victim_key = self.eviction_policy.select_victim(self._cache)
            if victim_key is None:
                # Fallback to LRU if policy can't select
                if self._cache:
                    victim_key = next(iter(self._cache))
                else:
                    break
            
            if victim_key in self._cache:
                del self._cache[victim_key]
                if self._stats:
                    self._stats.evictions += 1
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.ttl is not None and current_time > entry.created_at + entry.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        with self._lock:
            if self._stats:
                self._stats.total_requests += 1
            
            self._cleanup_expired()
            
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    entry.touch()
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    
                    if self._stats:
                        self._stats.hits += 1
                    
                    return entry.value
                else:
                    # Entry expired
                    del self._cache[key]
            
            if self._stats:
                self._stats.misses += 1
            
            return None
    
    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
                size=self._calculate_size(value)
            )
            
            # Evict if needed
            self._evict_if_needed()
            
            # Add new entry
            self._cache[key] = entry
            
            if self._stats:
                self._stats.memory_usage += entry.size
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                
                if self._stats:
                    self._stats.memory_usage -= entry.size
                
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            if self._stats:
                self._stats.memory_usage = 0
    
    def get_stats(self) -> Optional[CacheStats]:
        """Get cache statistics."""
        return self._stats
    
    def size(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(
        self,
        cache: Optional[AdaptiveCache] = None,
        ttl: Optional[float] = None,
        key_func: Optional[Callable] = None,
        namespace: Optional[str] = None
    ):
        """
        Initialize cache decorator.
        
        Args:
            cache: Cache instance to use
            ttl: Time-to-live for cached results
            key_func: Function to generate cache keys
            namespace: Namespace for cache keys
        """
        self.cache = cache or AdaptiveCache()
        self.ttl = ttl
        self.key_func = key_func
        self.namespace = namespace or "default"
    
    def __call__(self, func: Callable) -> Callable:
        """Decorate function with caching."""
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if self.key_func:
                cache_key = f"{self.namespace}:{self.key_func(*args, **kwargs)}"
            else:
                cache_key = f"{self.namespace}:{self.cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            self.cache.set(cache_key, result, ttl=self.ttl)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if self.key_func:
                cache_key = f"{self.namespace}:{self.key_func(*args, **kwargs)}"
            else:
                cache_key = f"{self.namespace}:{self.cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache.set(cache_key, result, ttl=self.ttl)
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


class ConnectionPool:
    """Connection pool for managing resource connections."""
    
    def __init__(
        self,
        connection_factory: Callable,
        max_connections: int = 20,
        min_connections: int = 5,
        max_idle_time: float = 300.0,
        connection_timeout: float = 30.0
    ):
        """
        Initialize connection pool.
        
        Args:
            connection_factory: Function to create new connections
            max_connections: Maximum number of connections
            min_connections: Minimum number of connections to maintain
            max_idle_time: Maximum idle time before closing connection
            connection_timeout: Timeout for creating new connections
        """
        self.connection_factory = connection_factory
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self._pool: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._created_count = 0
        self._active_count = 0
        self.logger = get_logger(__name__)
    
    async def acquire(self):
        """Acquire a connection from the pool."""
        async with self._lock:
            # Clean up expired connections
            await self._cleanup_expired()
            
            # Try to get an existing connection
            for i, conn_info in enumerate(self._pool):
                if not conn_info['in_use']:
                    conn_info['in_use'] = True
                    conn_info['last_used'] = time.time()
                    self._active_count += 1
                    return conn_info['connection']
            
            # Create new connection if under limit
            if self._created_count < self.max_connections:
                try:
                    connection = await asyncio.wait_for(
                        self.connection_factory(),
                        timeout=self.connection_timeout
                    )
                    
                    conn_info = {
                        'connection': connection,
                        'created_at': time.time(),
                        'last_used': time.time(),
                        'in_use': True
                    }
                    
                    self._pool.append(conn_info)
                    self._created_count += 1
                    self._active_count += 1
                    
                    return connection
                    
                except asyncio.TimeoutError:
                    self.logger.error("Connection creation timeout")
                    raise
                except Exception as e:
                    self.logger.error(f"Failed to create connection: {e}")
                    raise
            
            # Pool is full
            raise RuntimeError("Connection pool exhausted")
    
    async def release(self, connection):
        """Release a connection back to the pool."""
        async with self._lock:
            for conn_info in self._pool:
                if conn_info['connection'] is connection:
                    conn_info['in_use'] = False
                    conn_info['last_used'] = time.time()
                    self._active_count -= 1
                    return
            
            self.logger.warning("Attempted to release unknown connection")
    
    async def _cleanup_expired(self):
        """Remove expired idle connections."""
        current_time = time.time()
        expired_connections = []
        
        for i, conn_info in enumerate(self._pool):
            if (not conn_info['in_use'] and 
                current_time - conn_info['last_used'] > self.max_idle_time and
                self._created_count > self.min_connections):
                expired_connections.append(i)
        
        # Remove expired connections (reverse order to maintain indices)
        for i in reversed(expired_connections):
            conn_info = self._pool.pop(i)
            self._created_count -= 1
            
            # Close connection if it has a close method
            connection = conn_info['connection']
            if hasattr(connection, 'close'):
                try:
                    await connection.close()
                except Exception as e:
                    self.logger.warning(f"Error closing connection: {e}")
    
    async def close_all(self):
        """Close all connections in the pool."""
        async with self._lock:
            for conn_info in self._pool:
                connection = conn_info['connection']
                if hasattr(connection, 'close'):
                    try:
                        await connection.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing connection: {e}")
            
            self._pool.clear()
            self._created_count = 0
            self._active_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            'total_connections': self._created_count,
            'active_connections': self._active_count,
            'idle_connections': self._created_count - self._active_count,
            'max_connections': self.max_connections,
            'min_connections': self.min_connections
        }


class PerformanceMonitor:
    """Monitor and optimize performance metrics."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            window_size: Size of sliding window for metrics
        """
        self.window_size = window_size
        self._request_times: List[float] = []
        self._error_count = 0
        self._total_requests = 0
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    def record_request(self, duration: float, success: bool = True):
        """Record a request duration and success status."""
        with self._lock:
            self._request_times.append(duration)
            if len(self._request_times) > self.window_size:
                self._request_times.pop(0)
            
            self._total_requests += 1
            if not success:
                self._error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            if not self._request_times:
                return {
                    'avg_response_time': 0.0,
                    'p95_response_time': 0.0,
                    'p99_response_time': 0.0,
                    'error_rate': 0.0,
                    'total_requests': self._total_requests
                }
            
            sorted_times = sorted(self._request_times)
            n = len(sorted_times)
            
            return {
                'avg_response_time': sum(sorted_times) / n,
                'p95_response_time': sorted_times[int(n * 0.95)] if n > 0 else 0.0,
                'p99_response_time': sorted_times[int(n * 0.99)] if n > 0 else 0.0,
                'error_rate': self._error_count / max(self._total_requests, 1),
                'total_requests': self._total_requests,
                'window_size': n
            }
    
    def should_throttle(self, threshold_p95: float = 5.0, error_threshold: float = 0.1) -> bool:
        """Determine if system should throttle requests."""
        metrics = self.get_metrics()
        
        high_latency = metrics['p95_response_time'] > threshold_p95
        high_errors = metrics['error_rate'] > error_threshold
        
        return high_latency or high_errors


# Global instances
_global_cache: Optional[AdaptiveCache] = None
_performance_monitor: Optional[PerformanceMonitor] = None


def get_global_cache() -> AdaptiveCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = AdaptiveCache(max_size=10000, default_ttl=3600)
    return _global_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Convenience decorators
def cache_result(ttl: Optional[float] = None, namespace: str = "default"):
    """Decorator to cache function results."""
    return CacheDecorator(
        cache=get_global_cache(),
        ttl=ttl,
        namespace=namespace
    )


def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    monitor = get_performance_monitor()
    
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            monitor.record_request(duration, success)
    
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            monitor.record_request(duration, success)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper