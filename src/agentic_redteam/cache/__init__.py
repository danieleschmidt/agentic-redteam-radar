"""
Caching layer for Agentic RedTeam Radar.

Provides caching capabilities for scan results, API responses,
and other data to improve performance.
"""

from .manager import CacheManager, get_cache_manager
from .backends import MemoryCache, RedisCache

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "MemoryCache", 
    "RedisCache"
]