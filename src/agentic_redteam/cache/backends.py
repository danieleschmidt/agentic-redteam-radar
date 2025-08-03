"""
Cache backend implementations for Agentic RedTeam Radar.

Provides memory and Redis-based caching backends with consistent interface.
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from urllib.parse import urlparse

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..utils.logger import get_logger


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, ttl: int) -> bool:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class MemoryCache(CacheBackend):
    """
    In-memory cache backend with TTL support.
    
    Thread-safe implementation using locks for concurrent access.
    Suitable for development and single-instance deployments.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of cache entries
        """
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.logger = get_logger(__name__)
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from memory cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry['expires_at'] < time.time():
                del self._cache[key]
                self._stats['misses'] += 1
                return None
            
            # Update access time for LRU
            entry['accessed_at'] = time.time()
            self._stats['hits'] += 1
            
            return entry['value']
    
    def set(self, key: str, value: str, ttl: int) -> bool:
        """
        Set value in memory cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        with self._lock:
            current_time = time.time()
            
            # Check if we need to evict entries
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = {
                'value': value,
                'expires_at': current_time + ttl,
                'accessed_at': current_time,
                'created_at': current_time
            }
            
            self._stats['sets'] += 1
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete key from memory cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was found and deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                return True
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful
        """
        with self._lock:
            self._cache.clear()
            # Reset stats except for historical counters
            self._stats.update({
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0
            })
            return True
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists and is not expired.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and is valid
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry['expires_at'] < time.time():
                del self._cache[key]
                return False
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            # Clean up expired entries for accurate size
            self._cleanup_expired()
            
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests) if total_requests > 0 else 0.0
            
            return {
                'backend': 'memory',
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                **self._stats
            }
    
    def _evict_oldest(self):
        """Evict the oldest accessed entry."""
        if not self._cache:
            return
        
        # Find the entry with the oldest access time
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]['accessed_at']
        )
        
        del self._cache[oldest_key]
        self._stats['evictions'] += 1
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry['expires_at'] < current_time
        ]
        
        for key in expired_keys:
            del self._cache[key]


class RedisCache(CacheBackend):
    """
    Redis-based cache backend.
    
    Provides distributed caching with persistence and clustering support.
    Suitable for production deployments with multiple instances.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package not available for Redis caching")
        
        self.redis_url = redis_url
        self.logger = get_logger(__name__)
        
        # Parse Redis URL
        parsed = urlparse(redis_url)
        
        # Create Redis connection
        try:
            self.redis_client = redis.Redis(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 6379,
                db=int(parsed.path.lstrip('/')) if parsed.path else 0,
                password=parsed.password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            self.logger.info(f"Connected to Redis: {parsed.hostname}:{parsed.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            value = self.redis_client.get(key)
            return value
        except Exception as e:
            self.logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int) -> bool:
        """
        Set value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        try:
            result = self.redis_client.setex(key, ttl, value)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from Redis cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was found and deleted
        """
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries (flushes the Redis database).
        
        Returns:
            True if successful
        """
        try:
            result = self.redis_client.flushdb()
            return bool(result)
        except Exception as e:
            self.logger.error(f"Redis clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists
        """
        try:
            result = self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            info = self.redis_client.info()
            
            return {
                'backend': 'redis',
                'version': info.get('redis_version', 'unknown'),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'expired_keys': info.get('expired_keys', 0),
                'evicted_keys': info.get('evicted_keys', 0)
            }
        except Exception as e:
            self.logger.error(f"Redis stats error: {e}")
            return {'backend': 'redis', 'error': str(e)}
    
    def close(self):
        """Close Redis connection."""
        try:
            self.redis_client.close()
            self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {e}")