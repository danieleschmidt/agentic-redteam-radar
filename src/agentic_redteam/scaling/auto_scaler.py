"""
Auto-scaling system for Generation 3 scaling capabilities.

Provides intelligent horizontal and vertical scaling based on workload patterns,
performance metrics, and resource utilization.
"""

import time
import asyncio
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from collections import deque

from ..utils.logger import setup_logger
from ..monitoring.telemetry import get_telemetry_collector, record_error_metrics
from .adaptive_load_balancer import ScannerInstance, AdaptiveLoadBalancer, LoadBalancingStrategy


class ScalingDirection(Enum):
    """Scaling direction options."""
    UP = "up"
    DOWN = "down"
    NONE = "none"


class ScalingTrigger(Enum):
    """Scaling trigger types."""
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CUSTOM_METRIC = "custom_metric"


@dataclass
class ScalingRule:
    """Auto-scaling rule configuration."""
    name: str
    trigger: ScalingTrigger
    metric_threshold: float
    direction: ScalingDirection
    cooldown_seconds: float = 300.0  # 5 minutes
    evaluation_periods: int = 3
    scale_amount: int = 1
    enabled: bool = True


@dataclass
class ScalingEvent:
    """Scaling event record."""
    timestamp: float
    rule_name: str
    direction: ScalingDirection
    old_capacity: int
    new_capacity: int
    trigger_value: float
    reason: str


@dataclass
class ScalingMetrics:
    """Scaling metrics for auto-scaler decisions."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    queue_length: int = 0
    active_scans: int = 0
    pending_scans: int = 0
    throughput: float = 0.0
    error_rate: float = 0.0
    response_time_ms: float = 0.0


@dataclass
class ScalingPolicy:
    """Scaling policy configuration."""
    name: str
    trigger: ScalingTrigger
    scale_up_threshold: float
    scale_down_threshold: float
    cooldown_period: float = 300.0
    min_instances: int = 1
    max_instances: int = 10
    scale_up_increment: int = 1
    scale_down_increment: int = 1


@dataclass
class AutoScalerConfig:
    """Auto-scaler configuration."""
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_utilization: float = 70.0
    target_response_time_ms: float = 1000.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    evaluation_window_seconds: float = 300.0
    cooldown_seconds: float = 300.0
    aggressive_scaling: bool = False


class AutoScaler:
    """
    Intelligent auto-scaling system for scanner instances.
    
    Features:
    - Rule-based scaling with multiple triggers
    - Predictive scaling based on historical patterns
    - Resource utilization monitoring
    - Cooldown periods to prevent thrashing
    - Integration with load balancer
    - Detailed scaling event tracking
    """
    
    def __init__(self, 
                 load_balancer: AdaptiveLoadBalancer,
                 config: Optional[AutoScalerConfig] = None):
        """
        Initialize auto-scaler.
        
        Args:
            load_balancer: Load balancer instance to manage
            config: Auto-scaler configuration
        """
        self.load_balancer = load_balancer
        self.config = config or AutoScalerConfig()
        self.logger = setup_logger("agentic_redteam.scaling.auto_scaler")
        
        # State management
        self._lock = Lock()
        self._is_running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Scaling rules
        self.scaling_rules: Dict[str, ScalingRule] = {}
        self._setup_default_rules()
        
        # Metrics and history
        self.telemetry = get_telemetry_collector()
        self.scaling_events: deque = deque(maxlen=100)
        self.metric_history: Dict[str, deque] = {
            'cpu_utilization': deque(maxlen=100),
            'memory_utilization': deque(maxlen=100),
            'response_time': deque(maxlen=100),
            'error_rate': deque(maxlen=100),
            'queue_length': deque(maxlen=100),
            'instance_count': deque(maxlen=100)
        }
        
        # Predictive scaling
        self.prediction_window = 600.0  # 10 minutes
        self.workload_patterns: Dict[str, List[float]] = {}
        
        # Instance management callbacks
        self.instance_creator: Optional[Callable] = None
        self.instance_destroyer: Optional[Callable] = None
        
        self.logger.info(f"Auto-scaler initialized: min={self.config.min_instances}, max={self.config.max_instances}")
    
    def _setup_default_rules(self) -> None:
        """Setup default scaling rules."""
        default_rules = [
            ScalingRule(
                name="cpu_scale_up",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_threshold=self.config.scale_up_threshold,
                direction=ScalingDirection.UP,
                evaluation_periods=2
            ),
            ScalingRule(
                name="cpu_scale_down",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_threshold=self.config.scale_down_threshold,
                direction=ScalingDirection.DOWN,
                evaluation_periods=5,
                cooldown_seconds=600.0  # Longer cooldown for scale down
            ),
            ScalingRule(
                name="response_time_scale_up",
                trigger=ScalingTrigger.RESPONSE_TIME,
                metric_threshold=self.config.target_response_time_ms,
                direction=ScalingDirection.UP,
                evaluation_periods=3
            ),
            ScalingRule(
                name="error_rate_scale_up",
                trigger=ScalingTrigger.ERROR_RATE,
                metric_threshold=5.0,  # 5% error rate
                direction=ScalingDirection.UP,
                evaluation_periods=2,
                scale_amount=2  # Scale more aggressively on errors
            )
        ]
        
        for rule in default_rules:
            self.scaling_rules[rule.name] = rule
    
    def add_scaling_rule(self, rule: ScalingRule) -> None:
        """Add a custom scaling rule."""
        with self._lock:
            self.scaling_rules[rule.name] = rule
            self.logger.info(f"Added scaling rule: {rule.name}")
    
    def remove_scaling_rule(self, rule_name: str) -> None:
        """Remove a scaling rule."""
        with self._lock:
            if rule_name in self.scaling_rules:
                del self.scaling_rules[rule_name]
                self.logger.info(f"Removed scaling rule: {rule_name}")
    
    def set_instance_management_callbacks(self,
                                        creator: Optional[Callable] = None,
                                        destroyer: Optional[Callable] = None) -> None:
        """
        Set callbacks for instance creation and destruction.
        
        Args:
            creator: Function that creates new scanner instances
            destroyer: Function that destroys scanner instances
        """
        self.instance_creator = creator
        self.instance_destroyer = destroyer
        self.logger.info("Instance management callbacks configured")
    
    async def start_monitoring(self) -> None:
        """Start the auto-scaling monitoring loop."""
        if self._is_running:
            self.logger.warning("Auto-scaler monitoring is already running")
            return
        
        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Auto-scaler monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the auto-scaling monitoring loop."""
        self._is_running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Auto-scaler monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for auto-scaling decisions."""
        while self._is_running:
            try:
                await self._collect_metrics()
                await self._evaluate_scaling_rules()
                await self._perform_predictive_scaling()
                await self._cleanup_old_events()
                
                # Sleep for monitoring interval
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in auto-scaler monitoring loop: {e}")
                record_error_metrics("autoscaler_error", "scaling", str(e))
                await asyncio.sleep(60.0)  # Back off on error
    
    async def _collect_metrics(self) -> None:
        """Collect current system metrics for scaling decisions."""
        try:
            # Get load balancer stats
            lb_stats = self.load_balancer.get_stats()
            current_time = time.time()
            
            # Calculate metrics
            total_instances = lb_stats['total_instances']
            healthy_instances = lb_stats['healthy_instances']
            
            # Calculate average response time across instances
            response_times = []
            error_counts = []
            total_requests = 0
            
            for instance_stats in lb_stats['instances'].values():
                if instance_stats['avg_response_time'] > 0:
                    response_times.append(instance_stats['avg_response_time'] * 1000)  # Convert to ms
                error_counts.append(instance_stats['failed_requests'])
                total_requests += instance_stats['total_requests']
            
            avg_response_time = statistics.mean(response_times) if response_times else 0.0
            total_errors = sum(error_counts)
            error_rate = (total_errors / max(total_requests, 1)) * 100
            
            # Get system metrics (simplified)
            cpu_utilization = self._estimate_cpu_utilization(lb_stats)
            memory_utilization = self._estimate_memory_utilization(lb_stats)
            queue_length = self._estimate_queue_length(lb_stats)
            
            # Store metrics with timestamp
            with self._lock:
                self.metric_history['cpu_utilization'].append((current_time, cpu_utilization))
                self.metric_history['memory_utilization'].append((current_time, memory_utilization))
                self.metric_history['response_time'].append((current_time, avg_response_time))
                self.metric_history['error_rate'].append((current_time, error_rate))
                self.metric_history['queue_length'].append((current_time, queue_length))
                self.metric_history['instance_count'].append((current_time, healthy_instances))
            
            self.logger.debug(f"Metrics collected - CPU: {cpu_utilization:.1f}%, "
                            f"Mem: {memory_utilization:.1f}%, RT: {avg_response_time:.1f}ms, "
                            f"Errors: {error_rate:.1f}%, Instances: {healthy_instances}")
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
    
    def _estimate_cpu_utilization(self, lb_stats: Dict[str, Any]) -> float:
        """Estimate CPU utilization based on load metrics."""
        # Simplified estimation based on load scores
        load_scores = []
        for instance_stats in lb_stats['instances'].values():
            if instance_stats['health_status'] == 'healthy':
                load_scores.append(instance_stats['load_score'])
        
        if not load_scores:
            return 0.0
        
        # Convert load score to estimated CPU percentage
        avg_load = statistics.mean(load_scores)
        estimated_cpu = min(100.0, max(0.0, (avg_load / 1000.0) * 100.0))
        
        return estimated_cpu
    
    def _estimate_memory_utilization(self, lb_stats: Dict[str, Any]) -> float:
        """Estimate memory utilization based on active connections."""
        total_connections = sum(
            instance_stats['active_connections']
            for instance_stats in lb_stats['instances'].values()
        )
        
        # Rough estimation: each connection uses some memory
        max_connections = len(lb_stats['instances']) * 50  # Assume max 50 per instance
        memory_usage = (total_connections / max(max_connections, 1)) * 100.0
        
        return min(100.0, memory_usage)
    
    def _estimate_queue_length(self, lb_stats: Dict[str, Any]) -> float:
        """Estimate queue length based on active connections and response times."""
        total_connections = sum(
            instance_stats['active_connections']
            for instance_stats in lb_stats['instances'].values()
        )
        
        # Simple estimation - could be more sophisticated
        return float(total_connections)
    
    async def _evaluate_scaling_rules(self) -> None:
        """Evaluate all scaling rules and trigger scaling actions."""
        current_time = time.time()
        
        for rule_name, rule in self.scaling_rules.items():
            if not rule.enabled:
                continue
            
            try:
                should_scale, current_value = self._should_rule_trigger(rule, current_time)
                
                if should_scale:
                    # Check cooldown
                    if self._is_in_cooldown(rule, current_time):
                        self.logger.debug(f"Scaling rule {rule_name} triggered but in cooldown")
                        continue
                    
                    # Execute scaling action
                    await self._execute_scaling_action(rule, current_value, current_time)
            
            except Exception as e:
                self.logger.error(f"Error evaluating scaling rule {rule_name}: {e}")
    
    def _should_rule_trigger(self, rule: ScalingRule, current_time: float) -> tuple[bool, float]:
        """
        Check if a scaling rule should trigger.
        
        Returns:
            Tuple of (should_trigger, current_metric_value)
        """
        # Get recent metric values for evaluation
        metric_key = rule.trigger.value
        if metric_key not in self.metric_history:
            return False, 0.0
        
        recent_values = []
        cutoff_time = current_time - self.config.evaluation_window_seconds
        
        with self._lock:
            for timestamp, value in self.metric_history[metric_key]:
                if timestamp >= cutoff_time:
                    recent_values.append(value)
        
        if len(recent_values) < rule.evaluation_periods:
            return False, 0.0
        
        # Take the most recent values for evaluation
        eval_values = recent_values[-rule.evaluation_periods:]
        current_value = eval_values[-1] if eval_values else 0.0
        
        # Check if all evaluation values exceed threshold
        if rule.direction == ScalingDirection.UP:
            trigger = all(val >= rule.metric_threshold for val in eval_values)
        else:
            trigger = all(val <= rule.metric_threshold for val in eval_values)
        
        return trigger, current_value
    
    def _is_in_cooldown(self, rule: ScalingRule, current_time: float) -> bool:
        """Check if rule is in cooldown period."""
        # Find most recent scaling event for this rule
        with self._lock:
            for event in reversed(self.scaling_events):
                if event.rule_name == rule.name:
                    if current_time - event.timestamp < rule.cooldown_seconds:
                        return True
                    break
        
        return False
    
    async def _execute_scaling_action(self, rule: ScalingRule, metric_value: float, current_time: float) -> None:
        """Execute the scaling action for a triggered rule."""
        try:
            # Get current instance count
            lb_stats = self.load_balancer.get_stats()
            current_instances = lb_stats['healthy_instances']
            
            # Calculate new instance count
            if rule.direction == ScalingDirection.UP:
                new_instances = min(
                    self.config.max_instances,
                    current_instances + rule.scale_amount
                )
            else:
                new_instances = max(
                    self.config.min_instances,
                    current_instances - rule.scale_amount
                )
            
            if new_instances == current_instances:
                self.logger.debug(f"Scaling rule {rule.name} triggered but at capacity limits")
                return
            
            # Execute scaling
            success = await self._scale_instances(current_instances, new_instances)
            
            if success:
                # Record scaling event
                event = ScalingEvent(
                    timestamp=current_time,
                    rule_name=rule.name,
                    direction=rule.direction,
                    old_capacity=current_instances,
                    new_capacity=new_instances,
                    trigger_value=metric_value,
                    reason=f"{rule.trigger.value} {rule.direction.value} threshold exceeded"
                )
                
                with self._lock:
                    self.scaling_events.append(event)
                
                self.logger.info(
                    f"Scaling action executed: {rule.name} - "
                    f"{current_instances} -> {new_instances} instances "
                    f"(trigger: {metric_value:.2f})"
                )
            else:
                self.logger.warning(f"Failed to execute scaling action for rule: {rule.name}")
            
        except Exception as e:
            self.logger.error(f"Error executing scaling action for rule {rule.name}: {e}")
            record_error_metrics("scaling_action_error", "autoscaler", str(e))
    
    async def _scale_instances(self, current_count: int, target_count: int) -> bool:
        """
        Scale instances to target count.
        
        Args:
            current_count: Current instance count
            target_count: Target instance count
            
        Returns:
            True if scaling was successful
        """
        try:
            if target_count > current_count:
                # Scale up - create new instances
                instances_to_create = target_count - current_count
                
                if self.instance_creator:
                    for i in range(instances_to_create):
                        instance_id = f"autoscaled_{int(time.time())}_{i}"
                        new_instance = await self._create_instance(instance_id)
                        if new_instance:
                            self.load_balancer.add_instance(new_instance)
                        else:
                            self.logger.error(f"Failed to create instance: {instance_id}")
                            return False
                else:
                    self.logger.warning("No instance creator callback configured")
                    return False
                    
            elif target_count < current_count:
                # Scale down - remove instances
                instances_to_remove = current_count - target_count
                
                # Get least utilized instances for removal
                instances_to_destroy = self._select_instances_for_removal(instances_to_remove)
                
                for instance_id in instances_to_destroy:
                    if self.instance_destroyer:
                        success = await self._destroy_instance(instance_id)
                        if success:
                            self.load_balancer.remove_instance(instance_id)
                        else:
                            self.logger.error(f"Failed to destroy instance: {instance_id}")
                            return False
                    else:
                        # Just disable the instance if no destroyer callback
                        self.load_balancer.disable_instance(instance_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scaling instances: {e}")
            return False
    
    async def _create_instance(self, instance_id: str) -> Optional[ScannerInstance]:
        """Create a new scanner instance."""
        if self.instance_creator:
            try:
                return await self.instance_creator(instance_id)
            except Exception as e:
                self.logger.error(f"Instance creation failed for {instance_id}: {e}")
                return None
        return None
    
    async def _destroy_instance(self, instance_id: str) -> bool:
        """Destroy a scanner instance."""
        if self.instance_destroyer:
            try:
                await self.instance_destroyer(instance_id)
                return True
            except Exception as e:
                self.logger.error(f"Instance destruction failed for {instance_id}: {e}")
                return False
        return False
    
    def _select_instances_for_removal(self, count: int) -> List[str]:
        """Select instances for removal based on utilization."""
        lb_stats = self.load_balancer.get_stats()
        
        # Sort instances by load score (ascending - remove least loaded first)
        instances_by_load = []
        for instance_id, stats in lb_stats['instances'].items():
            if stats['enabled'] and stats['health_status'] != 'maintenance':
                instances_by_load.append((instance_id, stats['load_score']))
        
        instances_by_load.sort(key=lambda x: x[1])
        
        # Select the least loaded instances for removal
        return [instance_id for instance_id, _ in instances_by_load[:count]]
    
    async def _perform_predictive_scaling(self) -> None:
        """Perform predictive scaling based on historical patterns."""
        # Simplified predictive scaling implementation
        # In production, this could use machine learning models
        
        try:
            current_time = time.time()
            
            # Analyze workload patterns from the last few days
            self._analyze_workload_patterns(current_time)
            
            # Predict future load and pre-scale if needed
            predicted_load = self._predict_future_load(current_time)
            
            if predicted_load > self.config.scale_up_threshold * 1.2:  # 20% buffer
                # Consider pre-emptive scaling up
                lb_stats = self.load_balancer.get_stats()
                current_instances = lb_stats['healthy_instances']
                
                if current_instances < self.config.max_instances:
                    self.logger.info(f"Predictive scaling: high load predicted ({predicted_load:.1f}%)")
                    # Could trigger a predictive scaling action here
            
        except Exception as e:
            self.logger.error(f"Error in predictive scaling: {e}")
    
    def _analyze_workload_patterns(self, current_time: float) -> None:
        """Analyze historical workload patterns."""
        # Extract hourly patterns from metric history
        hour_of_day = int((current_time % (24 * 3600)) / 3600)
        
        with self._lock:
            cpu_values = []
            for timestamp, cpu in self.metric_history['cpu_utilization']:
                if timestamp > current_time - 24 * 3600:  # Last 24 hours
                    value_hour = int((timestamp % (24 * 3600)) / 3600)
                    if value_hour == hour_of_day:
                        cpu_values.append(cpu)
            
            if cpu_values:
                pattern_key = f"hour_{hour_of_day}"
                if pattern_key not in self.workload_patterns:
                    self.workload_patterns[pattern_key] = []
                
                avg_cpu = statistics.mean(cpu_values)
                self.workload_patterns[pattern_key].append(avg_cpu)
                
                # Keep only recent patterns
                if len(self.workload_patterns[pattern_key]) > 7:  # One week
                    self.workload_patterns[pattern_key].pop(0)
    
    def _predict_future_load(self, current_time: float) -> float:
        """Predict future load based on patterns."""
        # Simple prediction based on same hour historical data
        future_hour = int(((current_time + 3600) % (24 * 3600)) / 3600)  # Next hour
        pattern_key = f"hour_{future_hour}"
        
        if pattern_key in self.workload_patterns and self.workload_patterns[pattern_key]:
            return statistics.mean(self.workload_patterns[pattern_key])
        
        # Default to current load if no pattern data
        with self._lock:
            if self.metric_history['cpu_utilization']:
                return self.metric_history['cpu_utilization'][-1][1]
        
        return 50.0  # Default assumption
    
    async def _cleanup_old_events(self) -> None:
        """Clean up old scaling events and metric history."""
        current_time = time.time()
        cutoff_time = current_time - (7 * 24 * 3600)  # Keep 7 days
        
        with self._lock:
            # Clean up metric history
            for metric_name, history in self.metric_history.items():
                while history and history[0][0] < cutoff_time:
                    history.popleft()
            
            # Scaling events are limited by deque maxlen, so no cleanup needed
    
    def get_scaling_stats(self) -> Dict[str, Any]:
        """Get comprehensive auto-scaler statistics."""
        with self._lock:
            current_time = time.time()
            
            # Recent scaling events
            recent_events = [
                {
                    'timestamp': event.timestamp,
                    'rule_name': event.rule_name,
                    'direction': event.direction.value,
                    'old_capacity': event.old_capacity,
                    'new_capacity': event.new_capacity,
                    'trigger_value': event.trigger_value,
                    'reason': event.reason
                }
                for event in self.scaling_events
                if current_time - event.timestamp < 24 * 3600  # Last 24 hours
            ]
            
            # Current metrics
            current_metrics = {}
            for metric_name, history in self.metric_history.items():
                if history:
                    current_metrics[metric_name] = history[-1][1]
                else:
                    current_metrics[metric_name] = 0.0
            
            # Rule status
            rule_status = {}
            for rule_name, rule in self.scaling_rules.items():
                rule_status[rule_name] = {
                    'enabled': rule.enabled,
                    'trigger': rule.trigger.value,
                    'threshold': rule.metric_threshold,
                    'direction': rule.direction.value,
                    'in_cooldown': self._is_in_cooldown(rule, current_time)
                }
            
            return {
                'config': {
                    'min_instances': self.config.min_instances,
                    'max_instances': self.config.max_instances,
                    'target_cpu_utilization': self.config.target_cpu_utilization,
                    'target_response_time_ms': self.config.target_response_time_ms
                },
                'current_metrics': current_metrics,
                'recent_scaling_events': recent_events,
                'total_scaling_events': len(self.scaling_events),
                'scaling_rules': rule_status,
                'is_monitoring': self._is_running,
                'workload_patterns': dict(self.workload_patterns),
                'timestamp': current_time
            }
    
    def force_scale(self, target_instances: int, reason: str = "Manual scaling") -> bool:
        """
        Manually trigger scaling to a specific instance count.
        
        Args:
            target_instances: Target number of instances
            reason: Reason for manual scaling
            
        Returns:
            True if scaling was initiated successfully
        """
        if target_instances < self.config.min_instances or target_instances > self.config.max_instances:
            self.logger.error(f"Target instances {target_instances} outside allowed range")
            return False
        
        try:
            lb_stats = self.load_balancer.get_stats()
            current_instances = lb_stats['healthy_instances']
            
            if current_instances == target_instances:
                self.logger.info("Already at target instance count")
                return True
            
            # Create manual scaling event
            event = ScalingEvent(
                timestamp=time.time(),
                rule_name="manual_scaling",
                direction=ScalingDirection.UP if target_instances > current_instances else ScalingDirection.DOWN,
                old_capacity=current_instances,
                new_capacity=target_instances,
                trigger_value=0.0,
                reason=reason
            )
            
            with self._lock:
                self.scaling_events.append(event)
            
            # Schedule scaling action
            asyncio.create_task(self._scale_instances(current_instances, target_instances))
            
            self.logger.info(f"Manual scaling initiated: {current_instances} -> {target_instances}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in manual scaling: {e}")
            return False