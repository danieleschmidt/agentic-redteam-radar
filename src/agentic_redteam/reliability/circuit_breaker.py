"""
Circuit breaker pattern implementation for Generation 2 reliability.

Provides automatic failure detection and recovery for external services.
"""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from contextlib import contextmanager

from ..utils.logger import setup_logger
from ..monitoring.telemetry import record_error_metrics


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, calls rejected
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 30.0      # Seconds before attempting recovery
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 10.0               # Operation timeout seconds
    expected_exception: type = Exception  # Exception type to monitor


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for automatic failure handling.
    
    Implements the circuit breaker pattern to prevent cascading failures
    and provide automatic recovery mechanisms.
    """
    
    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name for logging
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitConfig()
        self.logger = setup_logger(f"agentic_redteam.circuit_breaker.{name}")
        
        # State management
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = threading.RLock()
        
        # Callbacks
        self._on_open_callback: Optional[Callable] = None
        self._on_close_callback: Optional[Callable] = None
        self._on_half_open_callback: Optional[Callable] = None
        
        self.logger.info(f"Circuit breaker '{name}' initialized: {config}")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenException: When circuit is open
            Original exception: When function fails
        """
        with self._lock:
            self._stats.total_calls += 1
        
        # Check if circuit is open
        if self._should_reject_call():
            error_msg = f"Circuit breaker '{self.name}' is OPEN - rejecting call"
            self.logger.warning(error_msg)
            record_error_metrics("circuit_open", f"circuit_breaker.{self.name}", "call rejected")
            raise CircuitOpenException(error_msg)
        
        # Attempt the call
        start_time = time.time()
        try:
            # Set timeout if supported
            if hasattr(func, '__timeout__'):
                kwargs['timeout'] = self.config.timeout
            
            result = func(*args, **kwargs)
            
            # Record success
            call_duration = time.time() - start_time
            self._on_success(call_duration)
            
            return result
            
        except self.config.expected_exception as e:
            # Record failure
            call_duration = time.time() - start_time
            self._on_failure(e, call_duration)
            raise
    
    @contextmanager
    def protect(self):
        """
        Context manager for circuit breaker protection.
        
        Usage:
            with circuit_breaker.protect():
                # Protected code here
                result = risky_operation()
        """
        if self._should_reject_call():
            error_msg = f"Circuit breaker '{self.name}' is OPEN - rejecting call"
            self.logger.warning(error_msg)
            raise CircuitOpenException(error_msg)
        
        start_time = time.time()
        try:
            yield
            # If we reach here, the operation succeeded
            call_duration = time.time() - start_time
            self._on_success(call_duration)
            
        except self.config.expected_exception as e:
            call_duration = time.time() - start_time
            self._on_failure(e, call_duration)
            raise
    
    def _should_reject_call(self) -> bool:
        """Check if call should be rejected based on current state."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return False
            elif self._state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                    return False
                return True
            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                return False
            else:
                return True
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt circuit reset."""
        return time.time() - self._stats.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self, call_duration: float) -> None:
        """Handle successful call."""
        with self._lock:
            self._stats.success_count += 1
            self._stats.total_successes += 1
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Check if we should close the circuit
                if self._stats.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._stats.failure_count = 0
            
            self.logger.debug(
                f"Circuit '{self.name}' - Success (duration: {call_duration:.3f}s, "
                f"state: {self._state.value}, success_count: {self._stats.success_count})"
            )
    
    def _on_failure(self, exception: Exception, call_duration: float) -> None:
        """Handle failed call."""
        with self._lock:
            self._stats.failure_count += 1
            self._stats.total_failures += 1
            self._stats.last_failure_time = time.time()
            
            # Reset success count on failure
            if self._state in [CircuitState.HALF_OPEN, CircuitState.CLOSED]:
                self._stats.success_count = 0
            
            # Check if we should open the circuit
            if self._state == CircuitState.CLOSED:
                if self._stats.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self._state == CircuitState.HALF_OPEN:
                # Go back to open on any failure in half-open state
                self._transition_to_open()
            
            self.logger.warning(
                f"Circuit '{self.name}' - Failure (duration: {call_duration:.3f}s, "
                f"error: {exception}, state: {self._state.value}, "
                f"failure_count: {self._stats.failure_count})"
            )
            
            # Record error metrics
            record_error_metrics(
                "circuit_breaker_failure", 
                f"circuit_breaker.{self.name}",
                f"{type(exception).__name__}: {str(exception)}"
            )
    
    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._stats.failure_count = 0  # Reset for next cycle
        
        self.logger.warning(
            f"Circuit breaker '{self.name}' opened "
            f"({old_state.value} -> {self._state.value}) - "
            f"failures: {self._stats.total_failures}, "
            f"threshold: {self.config.failure_threshold}"
        )
        
        if self._on_open_callback:
            try:
                self._on_open_callback(self)
            except Exception as e:
                self.logger.error(f"Error in on_open callback: {e}")
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._stats.success_count = 0  # Reset for recovery test
        
        self.logger.info(
            f"Circuit breaker '{self.name}' transitioning to half-open "
            f"({old_state.value} -> {self._state.value}) - testing recovery"
        )
        
        if self._on_half_open_callback:
            try:
                self._on_half_open_callback(self)
            except Exception as e:
                self.logger.error(f"Error in on_half_open callback: {e}")
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._stats.failure_count = 0
        self._stats.success_count = 0
        
        self.logger.info(
            f"Circuit breaker '{self.name}' closed "
            f"({old_state.value} -> {self._state.value}) - recovery successful"
        )
        
        if self._on_close_callback:
            try:
                self._on_close_callback(self)
            except Exception as e:
                self.logger.error(f"Error in on_close callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            uptime = time.time() - (self._stats.last_failure_time or time.time())
            success_rate = (
                self._stats.total_successes / max(self._stats.total_calls, 1)
            ) if self._stats.total_calls > 0 else 0.0
            
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._stats.failure_count,
                'success_count': self._stats.success_count,
                'total_calls': self._stats.total_calls,
                'total_failures': self._stats.total_failures,
                'total_successes': self._stats.total_successes,
                'success_rate': success_rate,
                'last_failure_time': self._stats.last_failure_time,
                'last_success_time': self._stats.last_success_time,
                'uptime_seconds': uptime,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'recovery_timeout': self.config.recovery_timeout,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout
                }
            }
    
    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._stats.failure_count = 0
            self._stats.success_count = 0
            
            self.logger.info(
                f"Circuit breaker '{self.name}' manually reset "
                f"({old_state.value} -> {self._state.value})"
            )
    
    def force_open(self) -> None:
        """Manually force circuit breaker to OPEN state."""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.OPEN
            self._stats.last_failure_time = time.time()
            
            self.logger.warning(
                f"Circuit breaker '{self.name}' manually opened "
                f"({old_state.value} -> {self._state.value})"
            )
    
    def set_callbacks(self, 
                     on_open: Optional[Callable] = None,
                     on_close: Optional[Callable] = None, 
                     on_half_open: Optional[Callable] = None) -> None:
        """Set callback functions for state transitions."""
        self._on_open_callback = on_open
        self._on_close_callback = on_close
        self._on_half_open_callback = on_half_open


class CircuitOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    
    Provides centralized management and monitoring of circuit breakers.
    """
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.logger = setup_logger("agentic_redteam.circuit_breaker_manager")
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        
        self.logger.info("Circuit breaker manager initialized")
    
    def create_circuit(self, name: str, config: Optional[CircuitConfig] = None) -> CircuitBreaker:
        """Create and register a new circuit breaker."""
        with self._lock:
            if name in self._circuits:
                self.logger.debug(f"Circuit breaker '{name}' already exists, returning existing instance")
                return self._circuits[name]
            
            circuit = CircuitBreaker(name, config)
            self._circuits[name] = circuit
            
            self.logger.info(f"Created circuit breaker: {name}")
            return circuit
    
    def get_circuit(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        with self._lock:
            return self._circuits.get(name)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            stats = {}
            for name, circuit in self._circuits.items():
                stats[name] = circuit.get_stats()
            
            return {
                'circuits': stats,
                'total_circuits': len(self._circuits),
                'open_circuits': len([c for c in self._circuits.values() if c.is_open]),
                'half_open_circuits': len([c for c in self._circuits.values() if c.is_half_open]),
                'closed_circuits': len([c for c in self._circuits.values() if c.is_closed]),
                'timestamp': time.time()
            }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._lock:
            for circuit in self._circuits.values():
                circuit.reset()
            
            self.logger.info("All circuit breakers reset")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all circuits."""
        stats = self.get_all_stats()
        
        # Determine overall health
        open_count = stats['open_circuits']
        total_count = stats['total_circuits']
        
        if total_count == 0:
            health_status = "no_circuits"
        elif open_count == 0:
            health_status = "healthy"
        elif open_count < total_count * 0.5:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            'status': health_status,
            'open_circuits': open_count,
            'total_circuits': total_count,
            'healthy_percentage': ((total_count - open_count) / max(total_count, 1)) * 100,
            'timestamp': time.time()
        }


# Global circuit breaker manager instance
_circuit_manager = None
_manager_lock = threading.Lock()


def get_circuit_manager() -> CircuitBreakerManager:
    """Get or create global circuit breaker manager."""
    global _circuit_manager
    
    if _circuit_manager is None:
        with _manager_lock:
            if _circuit_manager is None:
                _circuit_manager = CircuitBreakerManager()
    
    return _circuit_manager