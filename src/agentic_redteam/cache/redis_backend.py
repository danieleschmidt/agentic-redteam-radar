"""
Redis cache backend for Agentic RedTeam Radar.

Provides distributed caching capabilities with Redis support
for improved performance and scalability.
"""

import json
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict
import time

from ..monitoring import error_handler, ErrorCategory, ErrorSeverity
from ..utils.logger import get_logger


try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    redis = None
    HAS_REDIS = False


class RedisCache:
    """
    Redis-based cache implementation with advanced features.
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 default_ttl: int = 3600,
                 key_prefix: str = "radar:",
                 max_retries: int = 3,
                 enable_compression: bool = True):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
            max_retries: Maximum retry attempts
            enable_compression: Whether to compress large values
        """
        if not HAS_REDIS:
            raise ImportError("Redis library not installed. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.max_retries = max_retries
        self.enable_compression = enable_compression
        
        self._client = None
        self.logger = get_logger("agentic_redteam.cache.redis")
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "compressions": 0
        }
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._client.ping()
            self.logger.info(f"Connected to Redis: {self.redis_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self.logger.info("Disconnected from Redis")
    
    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        return f"{self.key_prefix}{key}"
    
    def _hash_key(self, data: Any) -> str:
        """Create hash key for complex data."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            sorted_data = json.dumps(data, sort_keys=True)
        else:
            sorted_data = str(data)
        
        return hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage."""
        try:
            if hasattr(value, 'to_dict'):
                # Handle custom objects with to_dict method
                serialized = json.dumps(value.to_dict())
            elif hasattr(value, '__dict__'):
                # Handle dataclasses and similar objects
                try:
                    serialized = json.dumps(asdict(value))
                except (TypeError, ValueError):
                    serialized = json.dumps(value.__dict__)
            else:
                serialized = json.dumps(value)
            
            # Compress large values if enabled
            if self.enable_compression and len(serialized) > 1024:
                try:
                    import gzip
                    compressed = gzip.compress(serialized.encode())
                    # Add compression marker
                    serialized = f"GZIP:{compressed.decode('latin1')}"
                    self.stats["compressions"] += 1
                except ImportError:
                    pass  # Compression not available
            
            return serialized
            
        except Exception as e:
            self.logger.warning(f"Failed to serialize value: {e}")
            return json.dumps(str(value))
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from storage."""
        try:
            # Check for compression marker
            if value.startswith("GZIP:"):
                try:
                    import gzip
                    compressed_data = value[5:].encode('latin1')
                    value = gzip.decompress(compressed_data).decode()
                except ImportError:
                    self.logger.warning("Cannot decompress value: gzip not available")
                    return None
            
            return json.loads(value)
            
        except Exception as e:
            self.logger.warning(f"Failed to deserialize value: {e}")
            return None
    
    @error_handler(category=ErrorCategory.NETWORK, severity=ErrorSeverity.MEDIUM)
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self._client:
            await self.connect()
        
        full_key = self._make_key(key)
        
        try:
            value = await self._client.get(full_key)
            if value is not None:
                self.stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    @error_handler(category=ErrorCategory.NETWORK, severity=ErrorSeverity.MEDIUM)
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()
        
        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized = self._serialize_value(value)
            result = await self._client.setex(full_key, ttl, serialized)
            
            if result:
                self.stats["sets"] += 1
                return True
            else:
                self.stats["errors"] += 1
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    @error_handler(category=ErrorCategory.NETWORK, severity=ErrorSeverity.LOW)
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()
        
        full_key = self._make_key(key)
        
        try:
            result = await self._client.delete(full_key)
            self.stats["deletes"] += 1
            return result > 0
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        if not self._client:
            await self.connect()
        
        full_key = self._make_key(key)
        
        try:
            result = await self._client.exists(full_key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration for existing key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()
        
        full_key = self._make_key(key)
        
        try:
            result = await self._client.expire(full_key, ttl)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        if not self._client:
            await self.connect()
        
        full_keys = [self._make_key(key) for key in keys]
        result = {}
        
        try:
            values = await self._client.mget(full_keys)
            
            for key, value in zip(keys, values):
                if value is not None:
                    self.stats["hits"] += 1
                    result[key] = self._deserialize_value(value)
                else:
                    self.stats["misses"] += 1
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            data: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()
        
        ttl = ttl or self.default_ttl
        
        try:
            pipe = self._client.pipeline()
            
            for key, value in data.items():
                full_key = self._make_key(key)
                serialized = self._serialize_value(value)
                pipe.setex(full_key, ttl, serialized)
            
            results = await pipe.execute()
            success_count = sum(1 for result in results if result)
            
            self.stats["sets"] += success_count
            return success_count == len(data)
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache set_many error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (uses Redis SCAN)
            
        Returns:
            Number of keys deleted
        """
        if not self._client:
            await self.connect()
        
        full_pattern = self._make_key(pattern)
        deleted_count = 0
        
        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=full_pattern, count=100)
                
                if keys:
                    await self._client.delete(*keys)
                    deleted_count += len(keys)
                
                if cursor == 0:
                    break
            
            self.stats["deletes"] += deleted_count
            return deleted_count
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Cache clear_pattern error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            if not self._client:
                await self.connect()
            
            info = await self._client.info("memory")
            
            return {
                **self.stats,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_connected_clients": info.get("connected_clients", 0),
                "hit_rate": (
                    self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                    if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
                ),
                "compression_rate": (
                    self.stats["compressions"] / self.stats["sets"]
                    if self.stats["sets"] > 0 else 0
                )
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return self.stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        try:
            if not self._client:
                await self.connect()
            
            start_time = time.time()
            await self._client.ping()
            latency = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connected": True
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }


class CacheManager:
    """
    High-level cache manager with intelligent caching strategies.
    """
    
    def __init__(self, backend: RedisCache):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend implementation
        """
        self.backend = backend
        self.logger = get_logger("agentic_redteam.cache.manager")
    
    async def cache_scan_result(self, agent_config: Dict[str, Any], 
                              patterns: List[str], result: Any) -> str:
        """
        Cache scan result with intelligent key generation.
        
        Args:
            agent_config: Agent configuration
            patterns: List of attack patterns used
            result: Scan result to cache
            
        Returns:
            Cache key used
        """
        # Create cache key from configuration
        cache_data = {
            "agent": {k: v for k, v in agent_config.items() 
                     if k not in ["api_key", "credentials"]},  # Exclude sensitive data
            "patterns": sorted(patterns),
            "timestamp": int(time.time() / 3600)  # Hour-based bucketing
        }
        
        cache_key = f"scan_result:{self.backend._hash_key(cache_data)}"
        
        # Cache for 24 hours by default
        await self.backend.set(cache_key, result, ttl=86400)
        
        self.logger.info(f"Cached scan result with key: {cache_key}")
        return cache_key
    
    async def get_cached_scan_result(self, agent_config: Dict[str, Any],
                                   patterns: List[str]) -> Optional[Any]:
        """
        Retrieve cached scan result.
        
        Args:
            agent_config: Agent configuration
            patterns: List of attack patterns
            
        Returns:
            Cached result or None
        """
        cache_data = {
            "agent": {k: v for k, v in agent_config.items() 
                     if k not in ["api_key", "credentials"]},
            "patterns": sorted(patterns),
            "timestamp": int(time.time() / 3600)
        }
        
        cache_key = f"scan_result:{self.backend._hash_key(cache_data)}"
        result = await self.backend.get(cache_key)
        
        if result:
            self.logger.info(f"Retrieved cached scan result: {cache_key}")
        
        return result
    
    async def cache_attack_response(self, attack_id: str, agent_id: str,
                                  payload: str, response: str) -> None:
        """
        Cache individual attack response.
        
        Args:
            attack_id: Attack pattern ID
            agent_id: Agent identifier
            payload: Attack payload
            response: Agent response
        """
        cache_key = f"attack:{attack_id}:{agent_id}:{self.backend._hash_key(payload)}"
        
        cache_data = {
            "payload": payload,
            "response": response,
            "timestamp": time.time()
        }
        
        # Cache for 1 hour
        await self.backend.set(cache_key, cache_data, ttl=3600)
    
    async def get_cached_attack_response(self, attack_id: str, agent_id: str,
                                       payload: str) -> Optional[str]:
        """
        Get cached attack response.
        
        Args:
            attack_id: Attack pattern ID
            agent_id: Agent identifier
            payload: Attack payload
            
        Returns:
            Cached response or None
        """
        cache_key = f"attack:{attack_id}:{agent_id}:{self.backend._hash_key(payload)}"
        cached = await self.backend.get(cache_key)
        
        if cached and isinstance(cached, dict):
            return cached.get("response")
        
        return None
    
    async def invalidate_agent_cache(self, agent_id: str) -> int:
        """
        Invalidate all cache entries for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Number of keys invalidated
        """
        patterns = [
            f"scan_result:*{agent_id}*",
            f"attack:*:{agent_id}:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.backend.clear_pattern(pattern)
            total_deleted += deleted
        
        self.logger.info(f"Invalidated {total_deleted} cache entries for agent {agent_id}")
        return total_deleted