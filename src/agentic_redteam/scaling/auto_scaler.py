"""
Intelligent auto-scaling system for dynamic resource management.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger


class ScalingDirection(Enum):
    """Scaling directions."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class ScalingTrigger(Enum):
    """Scaling triggers."""
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


@dataclass
class ScalingMetrics:
    """Current system metrics for scaling decisions."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    queue_length: int = 0
    avg_response_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    active_scans: int = 0
    pending_scans: int = 0
    timestamp: float = field(default_factory=time.time)
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScalingPolicy:
    """Configuration for scaling behavior."""
    name: str
    trigger: ScalingTrigger
    scale_up_threshold: float
    scale_down_threshold: float
    cooldown_period: float = 300.0  # 5 minutes
    min_instances: int = 1
    max_instances: int = 10
    scale_up_increment: int = 1
    scale_down_increment: int = 1
    enabled: bool = True


@dataclass
class ScalingEvent:
    """Record of a scaling event."""
    timestamp: float
    direction: ScalingDirection
    trigger: ScalingTrigger
    metric_value: float
    threshold: float
    old_instances: int
    new_instances: int
    reason: str


class AutoScaler:
    """
    Advanced auto-scaling system for dynamic resource management.
    
    Monitors system metrics and automatically scales resources up/down
    based on configurable policies and machine learning predictions.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.scaling.auto_scaler")
        
        # Configuration
        self.scaling_policies: List[ScalingPolicy] = []
        self.current_instances = 1
        self.target_instances = 1
        
        # State tracking
        self.metrics_history: List[ScalingMetrics] = []
        self.scaling_history: List[ScalingEvent] = []
        self.last_scale_time = 0.0
        self.max_history_size = 1000
        
        # Monitoring
        self._monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_interval = 30.0  # seconds
        
        # Callbacks
        self.scale_up_callback: Optional[Callable[[int], None]] = None
        self.scale_down_callback: Optional[Callable[[int], None]] = None
        self.metrics_provider: Optional[Callable[[], ScalingMetrics]] = None
        
        # Advanced features
        self.predictive_scaling = True
        self.learning_enabled = True
        self.burst_protection = True
        
        # Setup default policies
        self._setup_default_policies()
    
    def _setup_default_policies(self):
        """Setup default scaling policies."""
        # CPU-based scaling
        cpu_policy = ScalingPolicy(
            name="cpu_scaling",
            trigger=ScalingTrigger.CPU_UTILIZATION,
            scale_up_threshold=70.0,
            scale_down_threshold=30.0,
            cooldown_period=300.0,
            min_instances=1,
            max_instances=5
        )
        
        # Memory-based scaling
        memory_policy = ScalingPolicy(
            name="memory_scaling",
            trigger=ScalingTrigger.MEMORY_UTILIZATION,
            scale_up_threshold=80.0,
            scale_down_threshold=40.0,
            cooldown_period=300.0,
            min_instances=1,
            max_instances=5
        )
        
        # Queue length-based scaling
        queue_policy = ScalingPolicy(
            name="queue_scaling",
            trigger=ScalingTrigger.QUEUE_LENGTH,
            scale_up_threshold=10.0,  # 10 pending scans
            scale_down_threshold=2.0,   # 2 pending scans
            cooldown_period=180.0,   # Faster scaling for queue
            min_instances=1,
            max_instances=8
        )
        
        # Response time-based scaling
        response_policy = ScalingPolicy(
            name="response_time_scaling",
            trigger=ScalingTrigger.RESPONSE_TIME,
            scale_up_threshold=5.0,    # 5 seconds avg response time
            scale_down_threshold=1.0,   # 1 second avg response time
            cooldown_period=240.0,
            min_instances=1,
            max_instances=6
        )
        
        self.scaling_policies = [cpu_policy, memory_policy, queue_policy, response_policy]
        self.logger.info(f"Initialized with {len(self.scaling_policies)} scaling policies")
    
    def add_scaling_policy(self, policy: ScalingPolicy):
        """Add a custom scaling policy."""
        self.scaling_policies.append(policy)
        self.logger.info(f"Added scaling policy: {policy.name}")
    
    def set_callbacks(self, scale_up: Callable[[int], None] = None,
                     scale_down: Callable[[int], None] = None,
                     metrics_provider: Callable[[], ScalingMetrics] = None):
        """Set callback functions for scaling actions and metrics."""
        if scale_up:
            self.scale_up_callback = scale_up
        if scale_down:
            self.scale_down_callback = scale_down
        if metrics_provider:
            self.metrics_provider = metrics_provider
        
        self.logger.info("Scaling callbacks configured")
    
    async def start_monitoring(self):
        """Start automatic scaling monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Auto-scaling monitoring started")
    
    async def stop_monitoring(self):
        """Stop automatic scaling monitoring."""
        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Auto-scaling monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for auto-scaling decisions."""
        while self._monitoring:
            try:
                # Collect current metrics
                current_metrics = await self._collect_metrics()
                
                # Store in history
                self.metrics_history.append(current_metrics)
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history.pop(0)
                
                # Make scaling decisions
                await self._evaluate_scaling_decisions(current_metrics)
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in auto-scaling monitoring loop: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _collect_metrics(self) -> ScalingMetrics:
        """Collect current system metrics."""
        if self.metrics_provider:
            try:
                return self.metrics_provider()
            except Exception as e:
                self.logger.warning(f"Error collecting metrics from provider: {e}")
        
        # Default metrics collection
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Estimate other metrics (would be provided by actual system)
            return ScalingMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                queue_length=0,  # Would be actual queue length
                avg_response_time=0.0,  # Would be actual response time
                throughput=0.0,  # Would be actual throughput
                error_rate=0.0,  # Would be actual error rate
                active_scans=self.current_instances,
                pending_scans=0
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting default metrics: {e}")
            return ScalingMetrics()  # Return empty metrics on error
    
    async def _evaluate_scaling_decisions(self, current_metrics: ScalingMetrics):
        """Evaluate whether scaling is needed based on current metrics."""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_scale_time < min(p.cooldown_period for p in self.scaling_policies if p.enabled):
            return
        
        # Evaluate each policy
        scaling_recommendations = []
        
        for policy in self.scaling_policies:
            if not policy.enabled:
                continue
            
            recommendation = self._evaluate_policy(policy, current_metrics)
            if recommendation:
                scaling_recommendations.append(recommendation)
        
        # Apply most aggressive scaling recommendation
        if scaling_recommendations:
            # Sort by priority (scale up is higher priority than scale down)
            scaling_recommendations.sort(key=lambda x: (
                x['direction'] == ScalingDirection.UP,
                x['urgency_score']
            ), reverse=True)
            
            best_recommendation = scaling_recommendations[0]
            await self._execute_scaling(best_recommendation, current_metrics)
    
    def _evaluate_policy(self, policy: ScalingPolicy, metrics: ScalingMetrics) -> Optional[Dict]:
        """Evaluate a single scaling policy against current metrics."""
        # Get metric value based on trigger type
        if policy.trigger == ScalingTrigger.CPU_UTILIZATION:
            metric_value = metrics.cpu_percent
        elif policy.trigger == ScalingTrigger.MEMORY_UTILIZATION:
            metric_value = metrics.memory_percent
        elif policy.trigger == ScalingTrigger.QUEUE_LENGTH:
            metric_value = metrics.queue_length
        elif policy.trigger == ScalingTrigger.RESPONSE_TIME:
            metric_value = metrics.avg_response_time
        elif policy.trigger == ScalingTrigger.THROUGHPUT:
            metric_value = metrics.throughput
        elif policy.trigger == ScalingTrigger.ERROR_RATE:
            metric_value = metrics.error_rate
        else:
            return None  # Custom metrics not implemented yet
        
        # Determine scaling direction
        if metric_value >= policy.scale_up_threshold and self.current_instances < policy.max_instances:
            urgency = (metric_value - policy.scale_up_threshold) / policy.scale_up_threshold
            return {
                'policy': policy,
                'direction': ScalingDirection.UP,
                'metric_value': metric_value,
                'threshold': policy.scale_up_threshold,
                'urgency_score': urgency,
                'target_change': policy.scale_up_increment
            }
        elif metric_value <= policy.scale_down_threshold and self.current_instances > policy.min_instances:
            urgency = (policy.scale_down_threshold - metric_value) / policy.scale_down_threshold
            return {
                'policy': policy,
                'direction': ScalingDirection.DOWN,
                'metric_value': metric_value,
                'threshold': policy.scale_down_threshold,
                'urgency_score': urgency,
                'target_change': -policy.scale_down_increment
            }
        
        return None
    
    async def _execute_scaling(self, recommendation: Dict, current_metrics: ScalingMetrics):
        """Execute a scaling recommendation."""
        policy = recommendation['policy']
        direction = recommendation['direction']
        change = recommendation['target_change']
        
        old_instances = self.current_instances
        new_instances = max(
            policy.min_instances,
            min(policy.max_instances, old_instances + change)
        )
        
        if new_instances == old_instances:
            return  # No change needed
        
        # Create scaling event record
        event = ScalingEvent(
            timestamp=time.time(),
            direction=direction,
            trigger=policy.trigger,
            metric_value=recommendation['metric_value'],
            threshold=recommendation['threshold'],
            old_instances=old_instances,
            new_instances=new_instances,
            reason=f"{policy.name}: {policy.trigger.value} {direction.value} from {recommendation['metric_value']:.2f} (threshold: {recommendation['threshold']:.2f})"
        )
        
        # Execute scaling action
        try:
            if direction == ScalingDirection.UP and self.scale_up_callback:
                self.logger.info(f"Scaling UP: {old_instances} -> {new_instances} instances ({event.reason})")
                self.scale_up_callback(new_instances - old_instances)
            elif direction == ScalingDirection.DOWN and self.scale_down_callback:
                self.logger.info(f"Scaling DOWN: {old_instances} -> {new_instances} instances ({event.reason})")  
                self.scale_down_callback(old_instances - new_instances)
            
            # Update state
            self.current_instances = new_instances
            self.target_instances = new_instances
            self.last_scale_time = time.time()
            
            # Record event
            self.scaling_history.append(event)
            if len(self.scaling_history) > self.max_history_size:
                self.scaling_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error executing scaling action: {e}")
    
    def predict_scaling_needs(self, time_horizon_minutes: int = 30) -> Dict[str, Any]:
        """Predict future scaling needs using historical data."""
        if not self.predictive_scaling or len(self.metrics_history) < 10:
            return {"prediction": "insufficient_data", "confidence": 0.0}
        
        try:
            # Simple trend-based prediction
            recent_metrics = self.metrics_history[-10:]
            
            # Calculate trends for key metrics
            cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
            memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])
            queue_trend = self._calculate_trend([m.queue_length for m in recent_metrics])
            
            # Project future values
            current_cpu = recent_metrics[-1].cpu_percent
            current_memory = recent_metrics[-1].memory_percent
            current_queue = recent_metrics[-1].queue_length
            
            projected_cpu = current_cpu + (cpu_trend * time_horizon_minutes)
            projected_memory = current_memory + (memory_trend * time_horizon_minutes)
            projected_queue = current_queue + (queue_trend * time_horizon_minutes)
            
            # Determine likely scaling action
            scale_up_likely = (
                projected_cpu > 70 or 
                projected_memory > 80 or 
                projected_queue > 10
            )
            
            scale_down_likely = (
                projected_cpu < 30 and 
                projected_memory < 40 and 
                projected_queue < 2
            )
            
            prediction = "scale_up" if scale_up_likely else ("scale_down" if scale_down_likely else "stable")
            
            # Calculate confidence based on trend consistency
            trends_strength = abs(cpu_trend) + abs(memory_trend) + abs(queue_trend)
            confidence = min(1.0, trends_strength / 10.0)
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "projected_cpu": projected_cpu,
                "projected_memory": projected_memory,
                "projected_queue": projected_queue,
                "time_horizon_minutes": time_horizon_minutes
            }
            
        except Exception as e:
            self.logger.error(f"Error in predictive scaling: {e}")
            return {"prediction": "error", "confidence": 0.0, "error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope for a series of values."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x_values = list(range(n))
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current auto-scaling status and metrics."""
        recent_events = [
            {
                "timestamp": event.timestamp,
                "direction": event.direction.value,
                "trigger": event.trigger.value,
                "reason": event.reason,
                "instances_change": f"{event.old_instances} -> {event.new_instances}"
            }
            for event in self.scaling_history[-10:]  # Last 10 events
        ]
        
        active_policies = [
            {
                "name": policy.name,
                "trigger": policy.trigger.value,
                "scale_up_threshold": policy.scale_up_threshold,
                "scale_down_threshold": policy.scale_down_threshold,
                "min_instances": policy.min_instances,
                "max_instances": policy.max_instances,
                "enabled": policy.enabled
            }
            for policy in self.scaling_policies
        ]
        
        return {
            "current_instances": self.current_instances,
            "target_instances": self.target_instances,
            "monitoring_active": self._monitoring,
            "last_scale_time": self.last_scale_time,
            "total_scaling_events": len(self.scaling_history),
            "recent_events": recent_events,
            "active_policies": active_policies,
            "predictive_scaling_enabled": self.predictive_scaling,
            "learning_enabled": self.learning_enabled
        }