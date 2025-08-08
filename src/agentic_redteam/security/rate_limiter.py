"""
Rate limiting and resource protection for Agentic RedTeam Radar.

Implements various rate limiting strategies to protect against resource exhaustion
and ensure fair usage of the security testing framework.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from abc import ABC, abstractmethod
import logging

from ..utils.logger import get_logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_allowance: int = 10
    cooldown_period: int = 60
    max_concurrent_requests: int = 50


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        pass
    
    @abstractmethod
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for the key."""
        pass
    
    @abstractmethod
    def get_reset_time(self, key: str) -> float:
        """Get when the rate limit resets for the key."""
        pass


class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize token bucket rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)
        
        # Convert to per-second rates
        self.tokens_per_second = config.requests_per_minute / 60.0
        self.bucket_capacity = config.burst_allowance
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed using token bucket algorithm."""
        now = time.time()
        
        if key not in self.buckets:
            self.buckets[key] = {
                'tokens': self.bucket_capacity,
                'last_refill': now
            }
        
        bucket = self.buckets[key]
        
        # Refill tokens based on time elapsed
        time_elapsed = now - bucket['last_refill']
        tokens_to_add = time_elapsed * self.tokens_per_second
        bucket['tokens'] = min(
            self.bucket_capacity,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = now
        
        # Check if we have tokens available
        if bucket['tokens'] >= 1.0:
            bucket['tokens'] -= 1.0
            return True
        
        self.logger.warning(f"Rate limit exceeded for key: {key}")
        return False
    
    def get_remaining(self, key: str) -> int:
        """Get remaining tokens for the key."""
        if key not in self.buckets:
            return self.bucket_capacity
        
        return int(self.buckets[key]['tokens'])
    
    def get_reset_time(self, key: str) -> float:
        """Get when bucket will be full again."""
        if key not in self.buckets:
            return time.time()
        
        bucket = self.buckets[key]
        tokens_needed = self.bucket_capacity - bucket['tokens']
        if tokens_needed <= 0:
            return time.time()
        
        seconds_to_fill = tokens_needed / self.tokens_per_second
        return time.time() + seconds_to_fill


class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize sliding window rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.windows: Dict[str, deque] = defaultdict(deque)
        self.logger = get_logger(__name__)
        
        # Window size in seconds
        self.window_size = 60  # 1 minute
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed using sliding window."""
        now = time.time()
        window = self.windows[key]
        
        # Remove old requests outside the window
        while window and window[0] <= now - self.window_size:
            window.popleft()
        
        # Check if we're under the limit
        if len(window) < self.config.requests_per_minute:
            window.append(now)
            return True
        
        self.logger.warning(f"Rate limit exceeded for key: {key}")
        return False
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in the current window."""
        now = time.time()
        window = self.windows[key]
        
        # Clean old entries
        while window and window[0] <= now - self.window_size:
            window.popleft()
        
        return max(0, self.config.requests_per_minute - len(window))
    
    def get_reset_time(self, key: str) -> float:
        """Get when the oldest request in window expires."""
        window = self.windows[key]
        if not window:
            return time.time()
        
        return window[0] + self.window_size


class ConcurrencyLimiter:
    """Limits concurrent requests to prevent resource exhaustion."""
    
    def __init__(self, max_concurrent: int = 50):
        """
        Initialize concurrency limiter.
        
        Args:
            max_concurrent: Maximum concurrent requests allowed
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests: Dict[str, int] = defaultdict(int)
        self.logger = get_logger(__name__)
    
    async def acquire(self, key: str = "global") -> bool:
        """
        Acquire a concurrency slot.
        
        Args:
            key: Key to track concurrency for (default: global)
            
        Returns:
            True if slot acquired, False otherwise
        """
        try:
            # Use a timeout to avoid hanging
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=30.0
            )
            self.active_requests[key] += 1
            return True
        except asyncio.TimeoutError:
            self.logger.warning(f"Concurrency limit timeout for key: {key}")
            return False
    
    def release(self, key: str = "global") -> None:
        """
        Release a concurrency slot.
        
        Args:
            key: Key to release concurrency for
        """
        self.semaphore.release()
        self.active_requests[key] = max(0, self.active_requests[key] - 1)
    
    def get_active_count(self, key: str = "global") -> int:
        """Get number of active requests for key."""
        return self.active_requests[key]
    
    def get_available_slots(self) -> int:
        """Get number of available concurrency slots."""
        return self.semaphore._value


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on system load."""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize adaptive rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.base_limiter = TokenBucketRateLimiter(config)
        self.concurrency_limiter = ConcurrencyLimiter(config.max_concurrent_requests)
        self.logger = get_logger(__name__)
        
        # Adaptive parameters
        self.load_factor = 1.0
        self.last_load_check = time.time()
        self.load_check_interval = 30  # seconds
        
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed with adaptive throttling."""
        await self._update_load_factor()
        
        # Apply load-based scaling
        if self.load_factor > 0.8:
            # High load - be more restrictive
            adjusted_config = RateLimitConfig(
                requests_per_minute=int(self.config.requests_per_minute * 0.5),
                burst_allowance=int(self.config.burst_allowance * 0.7)
            )
            temp_limiter = TokenBucketRateLimiter(adjusted_config)
            return await temp_limiter.is_allowed(key)
        
        return await self.base_limiter.is_allowed(key)
    
    async def _update_load_factor(self) -> None:
        """Update system load factor."""
        now = time.time()
        if now - self.last_load_check < self.load_check_interval:
            return
        
        self.last_load_check = now
        
        # Calculate load based on concurrency usage
        available_slots = self.concurrency_limiter.get_available_slots()
        total_slots = self.config.max_concurrent_requests
        usage_ratio = 1.0 - (available_slots / total_slots)
        
        # Smooth the load factor
        self.load_factor = (self.load_factor * 0.7) + (usage_ratio * 0.3)
        
        if self.load_factor > 0.8:
            self.logger.warning(f"High system load detected: {self.load_factor:.2f}")
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests considering load factor."""
        remaining = self.base_limiter.get_remaining(key)
        if self.load_factor > 0.8:
            remaining = int(remaining * 0.5)
        return remaining
    
    def get_reset_time(self, key: str) -> float:
        """Get reset time from base limiter."""
        return self.base_limiter.get_reset_time(key)


class RateLimitManager:
    """Manages multiple rate limiters for different resources."""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limit manager.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Different limiters for different resources
        self.limiters = {
            'api': AdaptiveRateLimiter(config),
            'scan': TokenBucketRateLimiter(RateLimitConfig(
                requests_per_minute=config.requests_per_minute // 2,
                burst_allowance=config.burst_allowance // 2
            )),
            'pattern': SlidingWindowRateLimiter(RateLimitConfig(
                requests_per_minute=config.requests_per_minute * 2
            ))
        }
        
        self.concurrency_limiter = ConcurrencyLimiter(config.max_concurrent_requests)
    
    async def check_rate_limit(
        self, 
        resource: str, 
        key: str, 
        action: str = "request"
    ) -> Dict[str, Any]:
        """
        Check rate limit for a resource and key.
        
        Args:
            resource: Resource type (api, scan, pattern)
            key: Identification key (user_id, agent_name, etc.)
            action: Action being performed
            
        Returns:
            Dictionary with rate limit status
        """
        if resource not in self.limiters:
            self.logger.warning(f"Unknown resource type: {resource}")
            return {
                'allowed': True,
                'remaining': 1000,
                'reset_time': time.time() + 3600,
                'message': f"No rate limit configured for {resource}"
            }
        
        limiter = self.limiters[resource]
        allowed = await limiter.is_allowed(key)
        
        result = {
            'allowed': allowed,
            'remaining': limiter.get_remaining(key),
            'reset_time': limiter.get_reset_time(key),
            'resource': resource,
            'key': key,
            'action': action
        }
        
        if not allowed:
            result['message'] = f"Rate limit exceeded for {resource}:{key}"
            self.logger.warning(
                f"Rate limit exceeded - Resource: {resource}, Key: {key}, Action: {action}"
            )
        
        return result
    
    async def acquire_concurrency_slot(self, key: str = "global") -> bool:
        """Acquire a concurrency slot."""
        return await self.concurrency_limiter.acquire(key)
    
    def release_concurrency_slot(self, key: str = "global") -> None:
        """Release a concurrency slot."""
        self.concurrency_limiter.release(key)
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall rate limiting status."""
        return {
            'limiters': list(self.limiters.keys()),
            'concurrency': {
                'active': self.concurrency_limiter.get_active_count(),
                'available': self.concurrency_limiter.get_available_slots(),
                'max': self.config.max_concurrent_requests
            },
            'config': {
                'requests_per_minute': self.config.requests_per_minute,
                'requests_per_hour': self.config.requests_per_hour,
                'burst_allowance': self.config.burst_allowance
            }
        }


# Context manager for rate-limited operations
class RateLimitedOperation:
    """Context manager for rate-limited operations."""
    
    def __init__(
        self, 
        rate_limit_manager: RateLimitManager,
        resource: str,
        key: str,
        action: str = "operation"
    ):
        """
        Initialize rate-limited operation context.
        
        Args:
            rate_limit_manager: Rate limit manager instance
            resource: Resource type
            key: Identification key
            action: Action description
        """
        self.manager = rate_limit_manager
        self.resource = resource
        self.key = key
        self.action = action
        self.concurrency_acquired = False
        self.logger = get_logger(__name__)
    
    async def __aenter__(self):
        """Enter rate-limited context."""
        # Check rate limit
        rate_status = await self.manager.check_rate_limit(
            self.resource, self.key, self.action
        )
        
        if not rate_status['allowed']:
            raise RuntimeError(
                f"Rate limit exceeded: {rate_status.get('message', 'Unknown')}"
            )
        
        # Acquire concurrency slot
        self.concurrency_acquired = await self.manager.acquire_concurrency_slot(self.key)
        if not self.concurrency_acquired:
            raise RuntimeError("Concurrency limit exceeded")
        
        return rate_status
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit rate-limited context."""
        if self.concurrency_acquired:
            self.manager.release_concurrency_slot(self.key)


# Global rate limit manager instance
_rate_limit_manager: Optional[RateLimitManager] = None


def get_rate_limit_manager(config: Optional[RateLimitConfig] = None) -> RateLimitManager:
    """Get global rate limit manager instance."""
    global _rate_limit_manager
    
    if _rate_limit_manager is None:
        if config is None:
            config = RateLimitConfig()
        _rate_limit_manager = RateLimitManager(config)
    
    return _rate_limit_manager


def reset_rate_limit_manager() -> None:
    """Reset global rate limit manager (useful for testing)."""
    global _rate_limit_manager
    _rate_limit_manager = None