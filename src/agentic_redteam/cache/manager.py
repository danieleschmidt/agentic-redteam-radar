"""
Cache manager for Agentic RedTeam Radar.

Provides high-level caching interface with multiple backend support.
"""

import os
import json
import hashlib
from typing import Any, Optional, Union
from urllib.parse import urlparse

from .backends import CacheBackend, MemoryCache, RedisCache
from ..utils.logger import get_logger


class CacheManager:
    """
    High-level cache manager with configurable backends.
    
    Provides a unified interface for caching operations with
    support for multiple backend implementations.
    """
    
    def __init__(self, backend: Optional[CacheBackend] = None, 
                 default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend implementation
            default_ttl: Default time-to-live in seconds
        """
        self.backend = backend or MemoryCache()
        self.default_ttl = default_ttl
        self.logger = get_logger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            value = self.backend.get(key)
            if value is not None:
                self.logger.debug(f"Cache hit: {key}")
                return self._deserialize(value)
            else:
                self.logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            serialized_value = self._serialize(value)
            ttl = ttl or self.default_ttl
            
            success = self.backend.set(key, serialized_value, ttl)
            if success:
                self.logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            else:
                self.logger.warning(f"Cache set failed: {key}")
            
            return success
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False if not found or error
        """
        try:
            success = self.backend.delete(key)
            if success:
                self.logger.debug(f"Cache delete: {key}")
            return success
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.backend.clear()
            if success:
                self.logger.info("Cache cleared")
            return success
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return self.backend.exists(key)
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            return self.backend.get_stats()
        except Exception as e:
            self.logger.error(f"Cache stats error: {e}")
            return {}
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        # Create a string representation of all arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())  # Sort for consistency
        }
        
        # Serialize and hash the key data
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"radar:{key_hash[:16]}"
    
    def cache_scan_result(self, agent_name: str, patterns: list, 
                         result: Any, ttl: Optional[int] = None) -> str:
        """
        Cache scan result with automatic key generation.
        
        Args:
            agent_name: Name of the scanned agent
            patterns: List of attack patterns used
            result: Scan result to cache
            ttl: Time-to-live in seconds
            
        Returns:
            Cache key used for storage
        """
        key = self.generate_key("scan_result", agent_name, patterns)
        self.set(key, result, ttl)
        return key
    
    def get_scan_result(self, agent_name: str, patterns: list) -> Optional[Any]:
        """
        Get cached scan result.
        
        Args:
            agent_name: Name of the scanned agent
            patterns: List of attack patterns used
            
        Returns:
            Cached scan result if found, None otherwise
        """
        key = self.generate_key("scan_result", agent_name, patterns)
        return self.get(key)
    
    def cache_agent_response(self, agent_name: str, prompt: str, 
                           response: str, ttl: Optional[int] = None) -> str:
        """
        Cache agent response.
        
        Args:
            agent_name: Name of the agent
            prompt: Input prompt
            response: Agent response
            ttl: Time-to-live in seconds
            
        Returns:
            Cache key used for storage
        """
        key = self.generate_key("agent_response", agent_name, prompt)
        self.set(key, response, ttl)
        return key
    
    def get_agent_response(self, agent_name: str, prompt: str) -> Optional[str]:
        """
        Get cached agent response.
        
        Args:
            agent_name: Name of the agent
            prompt: Input prompt
            
        Returns:
            Cached response if found, None otherwise
        """
        key = self.generate_key("agent_response", agent_name, prompt)
        return self.get(key)
    
    def _serialize(self, value: Any) -> str:
        """
        Serialize value for cache storage.
        
        Args:
            value: Value to serialize
            
        Returns:
            Serialized string
        """
        return json.dumps(value, default=str)
    
    def _deserialize(self, value: str) -> Any:
        """
        Deserialize value from cache.
        
        Args:
            value: Serialized string
            
        Returns:
            Deserialized value
        """
        return json.loads(value)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = create_cache_manager()
    
    return _cache_manager


def create_cache_manager(cache_url: Optional[str] = None, 
                        default_ttl: int = 3600) -> CacheManager:
    """
    Create cache manager with configured backend.
    
    Args:
        cache_url: Cache backend URL (Redis or memory)
        default_ttl: Default time-to-live in seconds
        
    Returns:
        Configured CacheManager instance
    """
    if cache_url is None:
        cache_url = os.getenv('REDIS_URL', 'memory://')
    
    parsed = urlparse(cache_url)
    
    if parsed.scheme == 'redis':
        backend = RedisCache(cache_url)
    else:
        backend = MemoryCache()
    
    return CacheManager(backend, default_ttl)


def init_cache(cache_url: Optional[str] = None, 
               default_ttl: int = 3600) -> CacheManager:
    """
    Initialize global cache manager.
    
    Args:
        cache_url: Cache backend URL
        default_ttl: Default time-to-live in seconds
        
    Returns:
        CacheManager instance
    """
    global _cache_manager
    _cache_manager = create_cache_manager(cache_url, default_ttl)
    return _cache_manager