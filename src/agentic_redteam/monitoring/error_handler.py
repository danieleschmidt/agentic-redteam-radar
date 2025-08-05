"""
Comprehensive error handling and monitoring for Agentic RedTeam Radar.

Provides structured error handling, recovery mechanisms, and monitoring
for production-ready operation.
"""

import traceback
import time
import asyncio
from typing import Any, Dict, List, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager, contextmanager

from ..utils.logger import get_logger


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    AGENT = "agent"
    ATTACK = "attack"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    occurrence_count: int = 1


class ErrorRegistry:
    """Registry for tracking and analyzing errors."""
    
    def __init__(self, max_errors: int = 1000):
        """
        Initialize error registry.
        
        Args:
            max_errors: Maximum number of errors to keep in memory
        """
        self.max_errors = max_errors
        self.errors: Dict[str, ErrorInfo] = {}
        self.error_counts: Dict[str, int] = {}
        self.logger = get_logger("agentic_redteam.monitoring.errors")
    
    def register_error(self, error_info: ErrorInfo) -> None:
        """Register an error occurrence."""
        error_key = f"{error_info.category.value}:{error_info.message}"
        
        if error_key in self.errors:
            # Update existing error
            existing = self.errors[error_key]
            existing.occurrence_count += 1
            existing.timestamp = error_info.timestamp
            existing.context.update(error_info.context)
        else:
            # Add new error
            self.errors[error_key] = error_info
            
            # Maintain max size
            if len(self.errors) > self.max_errors:
                oldest_key = min(self.errors.keys(), 
                               key=lambda k: self.errors[k].timestamp)
                del self.errors[oldest_key]
        
        # Update counts
        self.error_counts[error_info.category.value] = \
            self.error_counts.get(error_info.category.value, 0) + 1
        
        # Log error
        self._log_error(error_info)
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error to the logging system."""
        context_str = ", ".join(f"{k}={v}" for k, v in error_info.context.items())
        log_message = (
            f"ERROR_REGISTERED: id={error_info.error_id}, "
            f"category={error_info.category.value}, "
            f"severity={error_info.severity.value}, "
            f"message={error_info.message}, "
            f"context={context_str}"
        )
        
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": len(self.errors),
            "error_counts_by_category": self.error_counts.copy(),
            "recent_critical_errors": [
                {
                    "id": error.error_id,
                    "category": error.category.value,
                    "message": error.message,
                    "timestamp": error.timestamp,
                    "count": error.occurrence_count
                }
                for error in self.errors.values()
                if error.severity == ErrorSeverity.CRITICAL
                and time.time() - error.timestamp < 3600  # Last hour
            ]
        }
    
    def clear_old_errors(self, max_age_seconds: int = 86400) -> int:
        """Clear errors older than specified age."""
        current_time = time.time()
        old_keys = [
            key for key, error in self.errors.items()
            if current_time - error.timestamp > max_age_seconds
        ]
        
        for key in old_keys:
            del self.errors[key]
        
        return len(old_keys)


class RecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def __init__(self, max_attempts: int = 3, backoff_factor: float = 2.0):
        """
        Initialize recovery strategy.
        
        Args:
            max_attempts: Maximum recovery attempts
            backoff_factor: Exponential backoff factor
        """
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
    
    async def attempt_recovery(self, error_info: ErrorInfo, 
                             context: Dict[str, Any]) -> bool:
        """
        Attempt to recover from an error.
        
        Args:
            error_info: Information about the error
            context: Additional context for recovery
            
        Returns:
            True if recovery was successful
        """
        for attempt in range(self.max_attempts):
            try:
                await self._execute_recovery(error_info, context, attempt)
                return True
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    break
                
                # Exponential backoff
                wait_time = (self.backoff_factor ** attempt)
                await asyncio.sleep(wait_time)
        
        return False
    
    async def _execute_recovery(self, error_info: ErrorInfo, 
                              context: Dict[str, Any], attempt: int) -> None:
        """Execute recovery logic (to be implemented by subclasses)."""
        raise NotImplementedError


class NetworkRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for network-related errors."""
    
    async def _execute_recovery(self, error_info: ErrorInfo,
                              context: Dict[str, Any], attempt: int) -> None:
        """Attempt network recovery."""
        if "connection" in context:
            # Reset connection
            connection = context["connection"]
            if hasattr(connection, "reset"):
                connection.reset()
        
        if "client" in context:
            # Reinitialize client
            client = context["client"]
            if hasattr(client, "_initialize_client"):
                client._initialize_client()


class RateLimitRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for rate limit errors."""
    
    def __init__(self, base_wait_time: float = 60.0, **kwargs):
        """Initialize rate limit recovery with longer waits."""
        super().__init__(**kwargs)
        self.base_wait_time = base_wait_time
    
    async def _execute_recovery(self, error_info: ErrorInfo,
                              context: Dict[str, Any], attempt: int) -> None:
        """Wait for rate limit to reset."""
        wait_time = self.base_wait_time * (self.backoff_factor ** attempt)
        await asyncio.sleep(wait_time)


class ErrorHandler:
    """
    Comprehensive error handler with recovery mechanisms.
    """
    
    def __init__(self, enable_recovery: bool = True):
        """
        Initialize error handler.
        
        Args:
            enable_recovery: Whether to enable automatic recovery
        """
        self.enable_recovery = enable_recovery
        self.registry = ErrorRegistry()
        self.recovery_strategies: Dict[ErrorCategory, RecoveryStrategy] = {
            ErrorCategory.NETWORK: NetworkRecoveryStrategy(),
            ErrorCategory.RATE_LIMIT: RateLimitRecoveryStrategy(),
        }
        self.logger = get_logger("agentic_redteam.monitoring.error_handler")
    
    def add_recovery_strategy(self, category: ErrorCategory, 
                            strategy: RecoveryStrategy) -> None:
        """Add or update recovery strategy for error category."""
        self.recovery_strategies[category] = strategy
    
    async def handle_error(self, exception: Exception, 
                         context: Dict[str, Any] = None,
                         category: ErrorCategory = ErrorCategory.UNKNOWN,
                         severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
        """
        Handle an error with optional recovery.
        
        Args:
            exception: The exception that occurred
            context: Additional context information
            category: Error category
            severity: Error severity
            
        Returns:
            True if error was handled/recovered successfully
        """
        context = context or {}
        
        # Create error info
        error_info = ErrorInfo(
            error_id=f"{category.value}_{int(time.time() * 1000)}",
            category=category,
            severity=severity,
            message=str(exception),
            details=traceback.format_exc(),
            context=context,
            stack_trace=traceback.format_exc()
        )
        
        # Register error
        self.registry.register_error(error_info)
        
        # Attempt recovery if enabled
        if self.enable_recovery and category in self.recovery_strategies:
            error_info.recovery_attempted = True
            try:
                recovery_successful = await self.recovery_strategies[category].attempt_recovery(
                    error_info, context
                )
                error_info.recovery_successful = recovery_successful
                
                if recovery_successful:
                    self.logger.info(f"Recovery successful for error {error_info.error_id}")
                    return True
                else:
                    self.logger.warning(f"Recovery failed for error {error_info.error_id}")
            
            except Exception as recovery_error:
                self.logger.error(f"Recovery attempt failed: {recovery_error}")
        
        return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        return self.registry.get_error_stats()


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def error_handler(category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 reraise: bool = True):
    """
    Decorator for automatic error handling.
    
    Args:
        category: Error category
        severity: Error severity
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    handler = get_error_handler()
                    context = {
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                    
                    handled = await handler.handle_error(e, context, category, severity)
                    
                    if reraise or not handled:
                        raise
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    handler = get_error_handler()
                    context = {
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                    
                    # Note: Sync wrapper can't use async recovery
                    handler.registry.register_error(ErrorInfo(
                        error_id=f"{category.value}_{int(time.time() * 1000)}",
                        category=category,
                        severity=severity,
                        message=str(e),
                        details=traceback.format_exc(),
                        context=context,
                        stack_trace=traceback.format_exc()
                    ))
                    
                    if reraise:
                        raise
            
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def error_boundary(category: ErrorCategory = ErrorCategory.UNKNOWN,
                        severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Async context manager for error boundary.
    
    Args:
        category: Error category
        severity: Error severity
    """
    try:
        yield
    except Exception as e:
        handler = get_error_handler()
        context = {"boundary": True}
        await handler.handle_error(e, context, category, severity)
        raise


@contextmanager
def sync_error_boundary(category: ErrorCategory = ErrorCategory.UNKNOWN,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Sync context manager for error boundary.
    
    Args:
        category: Error category
        severity: Error severity
    """
    try:
        yield
    except Exception as e:
        handler = get_error_handler()
        context = {"boundary": True}
        
        # Register error (sync version)
        error_info = ErrorInfo(
            error_id=f"{category.value}_{int(time.time() * 1000)}",
            category=category,
            severity=severity,
            message=str(e),
            details=traceback.format_exc(),
            context=context,
            stack_trace=traceback.format_exc()
        )
        handler.registry.register_error(error_info)
        raise


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    """
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.logger = get_logger("agentic_redteam.monitoring.circuit_breaker")
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                self.logger.info("Circuit breaker transitioning to half-open")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "half-open":
                self._reset()
            
            return result
            
        except self.expected_exception as e:
            self._record_failure()
            raise
    
    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _reset(self) -> None:
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        self.logger.info("Circuit breaker reset to closed state")


def circuit_breaker(failure_threshold: int = 5, 
                   recovery_timeout: float = 60.0,
                   expected_exception: Type[Exception] = Exception):
    """
    Decorator for circuit breaker functionality.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery
        expected_exception: Exception type to track
    """
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    
    return decorator