"""
Adaptive load balancer for Generation 3 scaling capabilities.

Provides intelligent load distribution across multiple scanner instances
with automatic failover and performance optimization.
"""

import time
import asyncio
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from collections import deque, defaultdict

from ..utils.logger import setup_logger
from ..monitoring.telemetry import record_error_metrics, get_telemetry_collector


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME = "response_time"
    ADAPTIVE = "adaptive"


class InstanceHealth(Enum):
    """Instance health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class InstanceMetrics:
    """Performance metrics for a scanner instance."""
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_request_time: float = 0
    last_health_check: float = 0
    health_status: InstanceHealth = InstanceHealth.HEALTHY
    weight: float = 1.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def load_score(self) -> float:
        """Calculate load score (lower is better)."""
        # Combine response time, connections, and success rate
        time_factor = self.avg_response_time * 1000  # Convert to ms
        connection_factor = self.active_connections * 100
        success_factor = (1.0 - self.success_rate) * 1000
        
        return time_factor + connection_factor + success_factor


@dataclass
class ScannerInstance:
    """Scanner instance configuration."""
    id: str
    endpoint: Optional[str] = None
    scanner_func: Optional[Callable] = None
    weight: float = 1.0
    enabled: bool = True
    max_connections: int = 10
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdaptiveLoadBalancer:
    """
    Adaptive load balancer with intelligent traffic distribution.
    
    Features:
    - Multiple load balancing strategies
    - Health monitoring and automatic failover
    - Adaptive weight adjustment based on performance
    - Circuit breaker integration
    - Real-time metrics and monitoring
    """
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE):
        """
        Initialize adaptive load balancer.
        
        Args:
            strategy: Load balancing strategy to use
        """
        self.strategy = strategy
        self.logger = setup_logger("agentic_redteam.scaling.load_balancer")
        
        # Instance management
        self.instances: Dict[str, ScannerInstance] = {}
        self.metrics: Dict[str, InstanceMetrics] = {}
        self._lock = Lock()
        
        # Strategy state
        self._round_robin_index = 0
        
        # Health checking
        self.health_check_interval = 30.0  # seconds
        self.health_check_timeout = 5.0
        self._last_health_check = 0
        
        # Performance monitoring
        self.telemetry = get_telemetry_collector()
        
        # Adaptive tuning
        self.adaptive_window = 300.0  # 5 minutes
        self.weight_adjustment_threshold = 0.1
        
        self.logger.info(f"Adaptive load balancer initialized with strategy: {strategy.value}")
    
    def add_instance(self, instance: ScannerInstance) -> None:
        """
        Add a scanner instance to the load balancer.
        
        Args:
            instance: Scanner instance to add
        """
        with self._lock:
            if instance.id in self.instances:
                raise ValueError(f"Instance {instance.id} already exists")
            
            self.instances[instance.id] = instance
            self.metrics[instance.id] = InstanceMetrics(weight=instance.weight)
            
            self.logger.info(f"Added scanner instance: {instance.id} (weight: {instance.weight})")
    
    def remove_instance(self, instance_id: str) -> None:
        """
        Remove a scanner instance from the load balancer.
        
        Args:
            instance_id: ID of instance to remove
        """
        with self._lock:
            if instance_id not in self.instances:
                self.logger.warning(f"Instance {instance_id} not found for removal")
                return
            
            del self.instances[instance_id]
            del self.metrics[instance_id]
            
            self.logger.info(f"Removed scanner instance: {instance_id}")
    
    def enable_instance(self, instance_id: str) -> None:
        """Enable a scanner instance."""
        with self._lock:
            if instance_id in self.instances:
                self.instances[instance_id].enabled = True
                self.metrics[instance_id].health_status = InstanceHealth.HEALTHY
                self.logger.info(f"Enabled instance: {instance_id}")
    
    def disable_instance(self, instance_id: str) -> None:
        """Disable a scanner instance."""
        with self._lock:
            if instance_id in self.instances:
                self.instances[instance_id].enabled = False
                self.metrics[instance_id].health_status = InstanceHealth.MAINTENANCE
                self.logger.info(f"Disabled instance: {instance_id}")
    
    async def select_instance(self) -> Optional[ScannerInstance]:
        """
        Select the best instance based on current strategy and metrics.
        
        Returns:
            Selected scanner instance or None if none available
        """
        await self._perform_health_checks_if_needed()
        
        with self._lock:
            available_instances = [
                (instance_id, instance) 
                for instance_id, instance in self.instances.items()
                if instance.enabled and 
                   self.metrics[instance_id].health_status != InstanceHealth.UNHEALTHY
            ]
            
            if not available_instances:
                self.logger.warning("No healthy instances available")
                return None
            
            # Apply load balancing strategy
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                selected = self._select_round_robin(available_instances)
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                selected = self._select_least_connections(available_instances)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                selected = self._select_weighted_round_robin(available_instances)
            elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME:
                selected = self._select_by_response_time(available_instances)
            elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
                selected = self._select_adaptive(available_instances)
            else:
                selected = self._select_round_robin(available_instances)
            
            if selected:
                # Update connection count
                self.metrics[selected.id].active_connections += 1
                self.logger.debug(f"Selected instance: {selected.id} (strategy: {self.strategy.value})")
            
            return selected
    
    def _select_round_robin(self, available_instances: List[Tuple[str, ScannerInstance]]) -> Optional[ScannerInstance]:
        """Select instance using round-robin strategy."""
        if not available_instances:
            return None
        
        instance_count = len(available_instances)
        selected_index = self._round_robin_index % instance_count
        self._round_robin_index = (self._round_robin_index + 1) % instance_count
        
        return available_instances[selected_index][1]
    
    def _select_least_connections(self, available_instances: List[Tuple[str, ScannerInstance]]) -> Optional[ScannerInstance]:
        """Select instance with least active connections."""
        if not available_instances:
            return None
        
        min_connections = float('inf')
        selected_instance = None
        
        for instance_id, instance in available_instances:
            connections = self.metrics[instance_id].active_connections
            if connections < min_connections:
                min_connections = connections
                selected_instance = instance
        
        return selected_instance
    
    def _select_weighted_round_robin(self, available_instances: List[Tuple[str, ScannerInstance]]) -> Optional[ScannerInstance]:
        """Select instance using weighted round-robin."""
        if not available_instances:
            return None
        
        # Create weighted list
        weighted_instances = []
        for instance_id, instance in available_instances:
            weight = int(self.metrics[instance_id].weight * 10)  # Scale for integer weights
            weighted_instances.extend([instance] * max(1, weight))
        
        if not weighted_instances:
            return available_instances[0][1]
        
        selected_index = self._round_robin_index % len(weighted_instances)
        self._round_robin_index = (self._round_robin_index + 1) % len(weighted_instances)
        
        return weighted_instances[selected_index]
    
    def _select_by_response_time(self, available_instances: List[Tuple[str, ScannerInstance]]) -> Optional[ScannerInstance]:
        """Select instance with best average response time."""
        if not available_instances:
            return None
        
        best_time = float('inf')
        selected_instance = None
        
        for instance_id, instance in available_instances:
            avg_time = self.metrics[instance_id].avg_response_time
            if avg_time < best_time:
                best_time = avg_time
                selected_instance = instance
        
        return selected_instance
    
    def _select_adaptive(self, available_instances: List[Tuple[str, ScannerInstance]]) -> Optional[ScannerInstance]:
        """Select instance using adaptive algorithm combining multiple factors."""
        if not available_instances:
            return None
        
        # Calculate composite score for each instance
        best_score = float('inf')
        selected_instance = None
        
        for instance_id, instance in available_instances:
            metrics = self.metrics[instance_id]
            
            # Composite score based on multiple factors
            load_score = metrics.load_score
            health_factor = 1.0 if metrics.health_status == InstanceHealth.HEALTHY else 2.0
            
            total_score = load_score * health_factor / metrics.weight
            
            if total_score < best_score:
                best_score = total_score
                selected_instance = instance
        
        return selected_instance
    
    async def execute_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """
        Execute a request through the load balancer.
        
        Args:
            request_func: Function to execute (should accept instance as first param)
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Request result
            
        Raises:
            Exception: If no healthy instances available or all requests fail
        """
        max_retries = 3
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            instance = await self.select_instance()
            
            if not instance:
                raise Exception("No healthy instances available for request execution")
            
            start_time = time.time()
            
            try:
                # Execute the request
                if asyncio.iscoroutinefunction(request_func):
                    result = await request_func(instance, *args, **kwargs)
                else:
                    result = request_func(instance, *args, **kwargs)
                
                # Record successful request
                response_time = time.time() - start_time
                self._record_request_success(instance.id, response_time)
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                self._record_request_failure(instance.id, response_time, e)
                
                last_exception = e
                retry_count += 1
                
                self.logger.warning(
                    f"Request failed on instance {instance.id} "
                    f"(attempt {retry_count}/{max_retries}): {e}"
                )
                
                # Mark instance as unhealthy if too many failures
                if self.metrics[instance.id].success_rate < 0.5:
                    self.metrics[instance.id].health_status = InstanceHealth.DEGRADED
        
        # All retries exhausted
        record_error_metrics("load_balancer_failure", "scaling", str(last_exception))
        raise Exception(f"Request failed on all attempts: {last_exception}")
    
    def _record_request_success(self, instance_id: str, response_time: float) -> None:
        """Record successful request metrics."""
        with self._lock:
            if instance_id in self.metrics:
                metrics = self.metrics[instance_id]
                metrics.response_times.append(response_time)
                metrics.total_requests += 1
                metrics.successful_requests += 1
                metrics.last_request_time = time.time()
                metrics.active_connections = max(0, metrics.active_connections - 1)
                
                # Adaptive weight adjustment
                if self.strategy == LoadBalancingStrategy.ADAPTIVE:
                    self._adjust_weight(instance_id, success=True)
    
    def _record_request_failure(self, instance_id: str, response_time: float, exception: Exception) -> None:
        """Record failed request metrics."""
        with self._lock:
            if instance_id in self.metrics:
                metrics = self.metrics[instance_id]
                metrics.response_times.append(response_time)
                metrics.total_requests += 1
                metrics.failed_requests += 1
                metrics.last_request_time = time.time()
                metrics.active_connections = max(0, metrics.active_connections - 1)
                
                # Adaptive weight adjustment
                if self.strategy == LoadBalancingStrategy.ADAPTIVE:
                    self._adjust_weight(instance_id, success=False)
    
    def _adjust_weight(self, instance_id: str, success: bool) -> None:
        """Adjust instance weight based on performance."""
        metrics = self.metrics[instance_id]
        
        current_weight = metrics.weight
        adjustment = 0.05 if success else -0.1
        
        new_weight = max(0.1, min(5.0, current_weight + adjustment))
        
        if abs(new_weight - current_weight) > self.weight_adjustment_threshold:
            metrics.weight = new_weight
            self.logger.debug(f"Adjusted weight for {instance_id}: {current_weight:.2f} -> {new_weight:.2f}")
    
    async def _perform_health_checks_if_needed(self) -> None:
        """Perform health checks on instances if needed."""
        current_time = time.time()
        
        if current_time - self._last_health_check < self.health_check_interval:
            return
        
        self._last_health_check = current_time
        
        # Perform health checks asynchronously
        health_check_tasks = []
        
        with self._lock:
            for instance_id in list(self.instances.keys()):
                task = asyncio.create_task(self._health_check_instance(instance_id))
                health_check_tasks.append(task)
        
        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)
    
    async def _health_check_instance(self, instance_id: str) -> None:
        """Perform health check on a specific instance."""
        try:
            # Simple health check - could be more sophisticated
            start_time = time.time()
            
            # For now, just mark as healthy if it's been recently active
            with self._lock:
                if instance_id not in self.metrics:
                    return
                
                metrics = self.metrics[instance_id]
                current_time = time.time()
                
                # Consider instance healthy if:
                # 1. High success rate
                # 2. Recent activity
                # 3. Reasonable response times
                is_healthy = (
                    metrics.success_rate > 0.8 and
                    (current_time - metrics.last_request_time) < 300 and  # Active in last 5 min
                    metrics.avg_response_time < 10.0  # Response time under 10s
                )
                
                if is_healthy:
                    if metrics.health_status == InstanceHealth.UNHEALTHY:
                        self.logger.info(f"Instance {instance_id} recovered to healthy state")
                    metrics.health_status = InstanceHealth.HEALTHY
                else:
                    if metrics.success_rate < 0.3:
                        metrics.health_status = InstanceHealth.UNHEALTHY
                        self.logger.warning(f"Instance {instance_id} marked as unhealthy (success rate: {metrics.success_rate:.2f})")
                    else:
                        metrics.health_status = InstanceHealth.DEGRADED
                
                metrics.last_health_check = current_time
                
        except Exception as e:
            self.logger.error(f"Health check failed for instance {instance_id}: {e}")
            with self._lock:
                if instance_id in self.metrics:
                    self.metrics[instance_id].health_status = InstanceHealth.UNHEALTHY
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics."""
        with self._lock:
            instance_stats = {}
            
            for instance_id, instance in self.instances.items():
                metrics = self.metrics[instance_id]
                
                instance_stats[instance_id] = {
                    'enabled': instance.enabled,
                    'health_status': metrics.health_status.value,
                    'weight': metrics.weight,
                    'active_connections': metrics.active_connections,
                    'total_requests': metrics.total_requests,
                    'successful_requests': metrics.successful_requests,
                    'failed_requests': metrics.failed_requests,
                    'success_rate': metrics.success_rate,
                    'avg_response_time': metrics.avg_response_time,
                    'load_score': metrics.load_score,
                    'last_request_time': metrics.last_request_time,
                    'last_health_check': metrics.last_health_check
                }
            
            # Overall stats
            total_instances = len(self.instances)
            healthy_instances = len([
                m for m in self.metrics.values() 
                if m.health_status == InstanceHealth.HEALTHY
            ])
            degraded_instances = len([
                m for m in self.metrics.values() 
                if m.health_status == InstanceHealth.DEGRADED
            ])
            
            return {
                'strategy': self.strategy.value,
                'total_instances': total_instances,
                'healthy_instances': healthy_instances,
                'degraded_instances': degraded_instances,
                'unhealthy_instances': total_instances - healthy_instances - degraded_instances,
                'health_percentage': (healthy_instances / max(total_instances, 1)) * 100,
                'instances': instance_stats,
                'last_health_check': self._last_health_check,
                'timestamp': time.time()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the load balancer."""
        stats = self.get_stats()
        
        if stats['healthy_instances'] == 0:
            status = "unhealthy"
        elif stats['healthy_instances'] == stats['total_instances']:
            status = "healthy"
        else:
            status = "degraded"
        
        return {
            'status': status,
            'healthy_instances': stats['healthy_instances'],
            'total_instances': stats['total_instances'],
            'health_percentage': stats['health_percentage'],
            'strategy': stats['strategy'],
            'timestamp': time.time()
        }