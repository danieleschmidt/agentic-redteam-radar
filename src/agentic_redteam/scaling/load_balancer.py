"""
Advanced load balancing for distributed scanning operations.
"""

import asyncio
import time
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
from ..utils.logger import get_logger


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"  
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    ADAPTIVE = "adaptive"


@dataclass
class WorkerNode:
    """Represents a worker node in the load balancer."""
    id: str
    endpoint: str
    weight: float = 1.0
    max_connections: int = 100
    current_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: float = 0.0
    is_healthy: bool = True
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    queue_length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def load_score(self) -> float:
        """Calculate current load score (0.0 = no load, 1.0 = max load)."""
        connection_load = self.current_connections / max(self.max_connections, 1)
        cpu_load = self.cpu_usage / 100.0
        memory_load = self.memory_usage / 100.0
        queue_load = min(self.queue_length / 10.0, 1.0)  # Assume 10 is high queue
        
        return (connection_load + cpu_load + memory_load + queue_load) / 4.0


@dataclass  
class LoadBalancingResult:
    """Result of load balancing decision."""
    selected_node: Optional[WorkerNode]
    reason: str
    load_distribution: Dict[str, float]
    total_available_nodes: int
    selection_time_ms: float


class LoadBalancer:
    """
    Advanced load balancer with multiple strategies and health monitoring.
    
    Distributes scanning workload across multiple worker nodes with
    intelligent routing based on node health, capacity, and performance.
    """
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE):
        self.logger = get_logger("agentic_redteam.scaling.load_balancer")
        
        # Configuration
        self.strategy = strategy
        self.nodes: Dict[str, WorkerNode] = {}
        
        # State for different strategies
        self.round_robin_index = 0
        self.node_weights: Dict[str, float] = {}
        
        # Health monitoring
        self.health_check_interval = 30.0
        self.health_check_timeout = 5.0
        self.unhealthy_threshold = 3
        self.recovery_threshold = 2
        
        # Performance tracking
        self.request_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Adaptive learning
        self.adaptive_weights: Dict[str, float] = {}
        self.learning_rate = 0.1
        self.performance_window = 100  # Number of requests to consider for adaptation
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring = False
    
    def add_node(self, node_id: str, endpoint: str, weight: float = 1.0,
                max_connections: int = 100, metadata: Dict[str, Any] = None):
        """Add a worker node to the load balancer."""
        node = WorkerNode(
            id=node_id,
            endpoint=endpoint,
            weight=weight,
            max_connections=max_connections,
            metadata=metadata or {}
        )
        
        self.nodes[node_id] = node
        self.node_weights[node_id] = weight
        self.adaptive_weights[node_id] = weight
        
        self.logger.info(f"Added worker node: {node_id} ({endpoint}) with weight {weight}")
    
    def remove_node(self, node_id: str):
        """Remove a worker node from the load balancer."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            if node_id in self.node_weights:
                del self.node_weights[node_id]
            if node_id in self.adaptive_weights:
                del self.adaptive_weights[node_id]
            
            self.logger.info(f"Removed worker node: {node_id}")
    
    def update_node_stats(self, node_id: str, **stats):
        """Update node statistics."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Update provided statistics
        for key, value in stats.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        # Update adaptive weights based on performance
        if self.strategy == LoadBalancingStrategy.ADAPTIVE:
            self._update_adaptive_weights(node_id)
    
    def select_node(self, request_context: Dict[str, Any] = None) -> LoadBalancingResult:
        """
        Select the best worker node based on current strategy.
        
        Args:
            request_context: Additional context for routing decisions
            
        Returns:
            LoadBalancingResult with selected node and routing information
        """
        start_time = time.time()
        request_context = request_context or {}
        
        # Filter healthy nodes
        healthy_nodes = {
            node_id: node for node_id, node in self.nodes.items() 
            if node.is_healthy and node.current_connections < node.max_connections
        }
        
        if not healthy_nodes:
            return LoadBalancingResult(
                selected_node=None,
                reason="No healthy nodes available",
                load_distribution={},
                total_available_nodes=0,
                selection_time_ms=(time.time() - start_time) * 1000
            )
        
        # Select node based on strategy
        selected_node = None
        reason = ""
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            selected_node, reason = self._select_round_robin(healthy_nodes)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            selected_node, reason = self._select_least_connections(healthy_nodes)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            selected_node, reason = self._select_weighted_round_robin(healthy_nodes)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            selected_node, reason = self._select_ip_hash(healthy_nodes, request_context)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            selected_node, reason = self._select_least_response_time(healthy_nodes)
        elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            selected_node, reason = self._select_resource_based(healthy_nodes)
        elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
            selected_node, reason = self._select_adaptive(healthy_nodes)
        
        # Calculate load distribution
        load_distribution = {
            node_id: node.load_score for node_id, node in healthy_nodes.items()
        }
        
        # Record request
        if selected_node:
            selected_node.current_connections += 1
            selected_node.total_requests += 1
        
        selection_time_ms = (time.time() - start_time) * 1000
        
        return LoadBalancingResult(
            selected_node=selected_node,
            reason=reason,
            load_distribution=load_distribution,
            total_available_nodes=len(healthy_nodes),
            selection_time_ms=selection_time_ms
        )
    
    def _select_round_robin(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node using round-robin strategy."""
        node_ids = list(healthy_nodes.keys())
        selected_id = node_ids[self.round_robin_index % len(node_ids)]
        self.round_robin_index = (self.round_robin_index + 1) % len(node_ids)
        
        return healthy_nodes[selected_id], f"Round robin selection: {selected_id}"
    
    def _select_least_connections(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node with least active connections."""
        min_connections = min(node.current_connections for node in healthy_nodes.values())
        candidates = [
            node for node in healthy_nodes.values() 
            if node.current_connections == min_connections
        ]
        
        selected_node = random.choice(candidates)  # Random among equals
        return selected_node, f"Least connections: {selected_node.id} ({min_connections} connections)"
    
    def _select_weighted_round_robin(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node using weighted round-robin."""
        # Build weighted list
        weighted_nodes = []
        for node in healthy_nodes.values():
            weight = int(self.node_weights.get(node.id, 1.0) * 10)  # Scale weight
            weighted_nodes.extend([node] * weight)
        
        if not weighted_nodes:
            # Fallback to simple round robin
            return self._select_round_robin(healthy_nodes)
        
        selected_node = weighted_nodes[self.round_robin_index % len(weighted_nodes)]
        self.round_robin_index += 1
        
        return selected_node, f"Weighted round robin: {selected_node.id} (weight: {self.node_weights.get(selected_node.id, 1.0)})"
    
    def _select_ip_hash(self, healthy_nodes: Dict[str, WorkerNode], 
                       request_context: Dict[str, Any]) -> tuple:
        """Select node based on IP hash for session affinity."""
        client_ip = request_context.get('client_ip', 'unknown')
        
        # Create hash of client IP
        hash_value = hashlib.md5(client_ip.encode()).hexdigest()
        hash_int = int(hash_value, 16)
        
        # Select node based on hash
        node_ids = sorted(healthy_nodes.keys())  # Sort for consistency
        selected_id = node_ids[hash_int % len(node_ids)]
        
        return healthy_nodes[selected_id], f"IP hash: {selected_id} (client: {client_ip})"
    
    def _select_least_response_time(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node with lowest average response time."""
        min_response_time = min(node.avg_response_time for node in healthy_nodes.values())
        candidates = [
            node for node in healthy_nodes.values()
            if node.avg_response_time == min_response_time
        ]
        
        selected_node = random.choice(candidates)
        return selected_node, f"Least response time: {selected_node.id} ({min_response_time:.2f}ms)"
    
    def _select_resource_based(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node based on resource utilization."""
        min_load = min(node.load_score for node in healthy_nodes.values())
        candidates = [
            node for node in healthy_nodes.values()
            if node.load_score == min_load
        ]
        
        selected_node = random.choice(candidates)
        return selected_node, f"Resource-based: {selected_node.id} (load: {min_load:.2f})"
    
    def _select_adaptive(self, healthy_nodes: Dict[str, WorkerNode]) -> tuple:
        """Select node using adaptive strategy based on historical performance."""
        # Calculate adaptive scores
        node_scores = {}
        for node in healthy_nodes.values():
            # Base score on multiple factors
            success_rate = node.success_rate
            response_time_factor = 1.0 / (node.avg_response_time + 0.1)  # Favor faster nodes
            load_factor = 1.0 - node.load_score  # Favor less loaded nodes
            adaptive_weight = self.adaptive_weights.get(node.id, 1.0)
            
            # Combined adaptive score
            score = (success_rate * 0.3 + 
                    response_time_factor * 0.3 + 
                    load_factor * 0.2 + 
                    adaptive_weight * 0.2)
            
            node_scores[node.id] = score
        
        # Select node with highest adaptive score
        best_node_id = max(node_scores.keys(), key=lambda k: node_scores[k])
        selected_node = healthy_nodes[best_node_id]
        
        return selected_node, f"Adaptive: {selected_node.id} (score: {node_scores[best_node_id]:.3f})"
    
    def _update_adaptive_weights(self, node_id: str):
        """Update adaptive weights based on node performance."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Calculate performance score
        success_rate = node.success_rate
        response_time_score = min(1.0, 5.0 / (node.avg_response_time + 0.1))  # Scale response time
        load_score = 1.0 - node.load_score
        
        performance_score = (success_rate + response_time_score + load_score) / 3.0
        
        # Update adaptive weight using exponential moving average
        current_weight = self.adaptive_weights.get(node_id, 1.0)
        new_weight = (1 - self.learning_rate) * current_weight + self.learning_rate * performance_score
        
        self.adaptive_weights[node_id] = max(0.1, min(2.0, new_weight))  # Clamp between 0.1 and 2.0
    
    def complete_request(self, node_id: str, success: bool, response_time_ms: float):
        """Record completion of a request."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Update connection count
        node.current_connections = max(0, node.current_connections - 1)
        
        # Update success/failure counts
        if success:
            node.successful_requests += 1
        else:
            node.failed_requests += 1
        
        # Update response time (exponential moving average)
        alpha = 0.2  # Smoothing factor
        if node.avg_response_time == 0:
            node.avg_response_time = response_time_ms
        else:
            node.avg_response_time = (1 - alpha) * node.avg_response_time + alpha * response_time_ms
        
        # Record in history
        request_record = {
            'timestamp': time.time(),
            'node_id': node_id,
            'success': success,
            'response_time_ms': response_time_ms,
            'strategy': self.strategy.value
        }
        
        self.request_history.append(request_record)
        if len(self.request_history) > self.max_history_size:
            self.request_history.pop(0)
        
        # Update adaptive weights
        if self.strategy == LoadBalancingStrategy.ADAPTIVE:
            self._update_adaptive_weights(node_id)
    
    async def start_health_monitoring(self):
        """Start health monitoring for all nodes."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._health_monitoring_loop())
        self.logger.info("Load balancer health monitoring started")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Load balancer health monitoring stopped")
    
    async def _health_monitoring_loop(self):
        """Health monitoring loop for all nodes."""
        while self._monitoring:
            try:
                for node_id, node in self.nodes.items():
                    await self._check_node_health(node)
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_node_health(self, node: WorkerNode):
        """Check health of a single node."""
        try:
            # Simple health check (would be replaced with actual endpoint check)
            current_time = time.time()
            
            # For now, consider node healthy if:
            # 1. Success rate > 80%
            # 2. Average response time < 10 seconds  
            # 3. Load score < 0.9
            
            is_healthy = (
                node.success_rate > 0.8 and
                node.avg_response_time < 10000 and  # 10 seconds in milliseconds
                node.load_score < 0.9
            )
            
            # Update health status
            previous_health = node.is_healthy
            node.is_healthy = is_healthy
            node.last_health_check = current_time
            
            # Log health changes
            if previous_health != is_healthy:
                status = "healthy" if is_healthy else "unhealthy"
                self.logger.info(f"Node {node.id} is now {status}")
                
        except Exception as e:
            self.logger.error(f"Health check failed for node {node.id}: {e}")
            node.is_healthy = False
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics."""
        node_stats = {}
        for node_id, node in self.nodes.items():
            node_stats[node_id] = {
                'endpoint': node.endpoint,
                'weight': node.weight,
                'is_healthy': node.is_healthy,
                'current_connections': node.current_connections,
                'max_connections': node.max_connections,
                'total_requests': node.total_requests,
                'success_rate': node.success_rate,
                'avg_response_time_ms': node.avg_response_time,
                'load_score': node.load_score,
                'cpu_usage': node.cpu_usage,
                'memory_usage': node.memory_usage,
                'adaptive_weight': self.adaptive_weights.get(node_id, 1.0)
            }
        
        # Recent performance metrics
        recent_requests = [r for r in self.request_history if time.time() - r['timestamp'] < 3600]  # Last hour
        
        total_recent = len(recent_requests)
        successful_recent = len([r for r in recent_requests if r['success']])
        
        return {
            'strategy': self.strategy.value,
            'total_nodes': len(self.nodes),
            'healthy_nodes': len([n for n in self.nodes.values() if n.is_healthy]),
            'monitoring_active': self._monitoring,
            'node_stats': node_stats,
            'recent_performance': {
                'total_requests': total_recent,
                'success_rate': successful_recent / max(total_recent, 1),
                'avg_response_time_ms': sum(r['response_time_ms'] for r in recent_requests) / max(total_recent, 1)
            },
            'request_history_size': len(self.request_history)
        }