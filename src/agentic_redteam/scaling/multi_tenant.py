"""
Multi-tenancy support for scalable operations.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger


class TenantPriority(Enum):
    """Tenant priority levels."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    PREMIUM = "premium"


class IsolationLevel(Enum):
    """Resource isolation levels."""
    SHARED = "shared"
    QUOTA = "quota"
    DEDICATED = "dedicated"


@dataclass
class TenantQuota:
    """Resource quotas for a tenant."""
    max_concurrent_scans: int = 5
    max_cpu_percent: float = 20.0
    max_memory_mb: int = 512
    max_requests_per_minute: int = 60
    max_storage_mb: int = 1024
    priority: TenantPriority = TenantPriority.NORMAL


@dataclass
class TenantUsage:
    """Current resource usage for a tenant."""
    current_scans: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    requests_last_minute: int = 0
    storage_mb: float = 0.0
    total_requests: int = 0
    last_activity: float = field(default_factory=time.time)


@dataclass
class TenantIsolation:
    """Isolation configuration for a tenant."""
    level: IsolationLevel
    dedicated_resources: Dict[str, Any] = field(default_factory=dict)
    allowed_features: Set[str] = field(default_factory=set)
    security_policies: Dict[str, Any] = field(default_factory=dict)


class MultiTenantManager:
    """
    Advanced multi-tenancy manager for scalable SaaS operations.
    
    Provides tenant isolation, resource quotas, usage tracking,
    and fair resource allocation across multiple tenants.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.scaling.multi_tenant")
        
        # Tenant management
        self.tenants: Dict[str, Dict[str, Any]] = {}
        self.tenant_quotas: Dict[str, TenantQuota] = {}
        self.tenant_usage: Dict[str, TenantUsage] = {}
        self.tenant_isolation: Dict[str, TenantIsolation] = {}
        
        # Resource allocation
        self.resource_locks: Dict[str, asyncio.Semaphore] = {}
        self.global_resources = {
            'max_concurrent_scans': 50,
            'total_cpu_percent': 80.0,
            'total_memory_mb': 4096
        }
        
        # Usage tracking
        self.request_history: Dict[str, List[float]] = {}
        self.usage_history: Dict[str, List[TenantUsage]] = {}
        self.max_history_size = 1000
        
        # Monitoring
        self._monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_interval = 60.0  # 1 minute
        
        # Fair scheduling
        self.tenant_queue: List[str] = []  # Round-robin queue
        self.tenant_weights: Dict[str, float] = {}  # Weighted fair queuing
    
    def create_tenant(self, tenant_id: str, quota: TenantQuota = None,
                     isolation: TenantIsolation = None, metadata: Dict[str, Any] = None) -> bool:
        """Create a new tenant with specified quotas and isolation."""
        if tenant_id in self.tenants:
            self.logger.warning(f"Tenant '{tenant_id}' already exists")
            return False
        
        # Set default quota and isolation
        if quota is None:
            quota = TenantQuota()
        if isolation is None:
            isolation = TenantIsolation(level=IsolationLevel.SHARED)
        
        # Initialize tenant
        self.tenants[tenant_id] = {
            'created_at': time.time(),
            'metadata': metadata or {},
            'active': True
        }
        
        self.tenant_quotas[tenant_id] = quota
        self.tenant_usage[tenant_id] = TenantUsage()
        self.tenant_isolation[tenant_id] = isolation
        
        # Initialize resource tracking
        self.request_history[tenant_id] = []
        self.usage_history[tenant_id] = []
        
        # Create resource locks based on isolation level
        if isolation.level == IsolationLevel.DEDICATED:
            self.resource_locks[tenant_id] = asyncio.Semaphore(quota.max_concurrent_scans)
        
        # Set tenant weight for fair scheduling
        self.tenant_weights[tenant_id] = self._calculate_tenant_weight(quota.priority)
        
        self.logger.info(f"Created tenant '{tenant_id}' with {quota.priority.value} priority and {isolation.level.value} isolation")
        return True
    
    def _calculate_tenant_weight(self, priority: TenantPriority) -> float:
        """Calculate tenant weight for fair scheduling."""
        weights = {
            TenantPriority.LOW: 0.5,
            TenantPriority.NORMAL: 1.0,
            TenantPriority.HIGH: 2.0,
            TenantPriority.PREMIUM: 4.0
        }
        return weights.get(priority, 1.0)
    
    async def check_resource_availability(self, tenant_id: str, 
                                        resource_request: Dict[str, Any]) -> Dict[str, bool]:
        """Check if tenant can acquire requested resources."""
        if tenant_id not in self.tenants:
            return {"allowed": False, "reason": "Tenant not found"}
        
        if not self.tenants[tenant_id]['active']:
            return {"allowed": False, "reason": "Tenant inactive"}
        
        quota = self.tenant_quotas[tenant_id]
        current_usage = self.tenant_usage[tenant_id]
        
        # Check individual limits
        checks = {}
        
        # Concurrent scans
        requested_scans = resource_request.get('concurrent_scans', 1)
        if current_usage.current_scans + requested_scans > quota.max_concurrent_scans:
            checks['concurrent_scans'] = False
        else:
            checks['concurrent_scans'] = True
        
        # CPU usage
        requested_cpu = resource_request.get('cpu_percent', 5.0)
        if current_usage.cpu_percent + requested_cpu > quota.max_cpu_percent:
            checks['cpu_usage'] = False
        else:
            checks['cpu_usage'] = True
        
        # Memory usage  
        requested_memory = resource_request.get('memory_mb', 100)
        if current_usage.memory_mb + requested_memory > quota.max_memory_mb:
            checks['memory_usage'] = False
        else:
            checks['memory_usage'] = True
        
        # Rate limiting
        if self._check_rate_limit(tenant_id, quota.max_requests_per_minute):
            checks['rate_limit'] = True
        else:
            checks['rate_limit'] = False
        
        all_passed = all(checks.values())
        
        return {
            "allowed": all_passed,
            "details": checks,
            "quota": {
                "max_concurrent_scans": quota.max_concurrent_scans,
                "max_cpu_percent": quota.max_cpu_percent,
                "max_memory_mb": quota.max_memory_mb,
                "max_requests_per_minute": quota.max_requests_per_minute
            },
            "current_usage": {
                "current_scans": current_usage.current_scans,
                "cpu_percent": current_usage.cpu_percent,
                "memory_mb": current_usage.memory_mb,
                "requests_last_minute": current_usage.requests_last_minute
            }
        }
    
    def _check_rate_limit(self, tenant_id: str, max_requests_per_minute: int) -> bool:
        """Check if tenant is within rate limit."""
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        history = self.request_history[tenant_id]
        self.request_history[tenant_id] = [
            timestamp for timestamp in history 
            if current_time - timestamp < 60
        ]
        
        # Check current rate
        return len(self.request_history[tenant_id]) < max_requests_per_minute
    
    async def allocate_resources(self, tenant_id: str, 
                               resource_request: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate resources to a tenant."""
        # Check availability first
        availability = await self.check_resource_availability(tenant_id, resource_request)
        
        if not availability['allowed']:
            return {
                'success': False,
                'reason': 'Resource quota exceeded',
                'details': availability['details']
            }
        
        # Update usage
        current_usage = self.tenant_usage[tenant_id]
        current_usage.current_scans += resource_request.get('concurrent_scans', 1)
        current_usage.cpu_percent += resource_request.get('cpu_percent', 5.0)
        current_usage.memory_mb += resource_request.get('memory_mb', 100)
        current_usage.total_requests += 1
        current_usage.last_activity = time.time()
        
        # Record request for rate limiting
        self.request_history[tenant_id].append(time.time())
        
        # Record usage history
        usage_snapshot = TenantUsage(
            current_scans=current_usage.current_scans,
            cpu_percent=current_usage.cpu_percent,
            memory_mb=current_usage.memory_mb,
            total_requests=current_usage.total_requests,
            last_activity=current_usage.last_activity
        )
        
        self.usage_history[tenant_id].append(usage_snapshot)
        if len(self.usage_history[tenant_id]) > self.max_history_size:
            self.usage_history[tenant_id].pop(0)
        
        self.logger.debug(f"Allocated resources to tenant '{tenant_id}': {resource_request}")
        
        return {
            'success': True,
            'allocated_resources': resource_request,
            'current_usage': {
                'current_scans': current_usage.current_scans,
                'cpu_percent': current_usage.cpu_percent,
                'memory_mb': current_usage.memory_mb
            }
        }
    
    async def deallocate_resources(self, tenant_id: str, 
                                 resource_release: Dict[str, Any]) -> Dict[str, Any]:
        """Deallocate resources from a tenant."""
        if tenant_id not in self.tenant_usage:
            return {'success': False, 'reason': 'Tenant not found'}
        
        # Update usage
        current_usage = self.tenant_usage[tenant_id]
        current_usage.current_scans = max(0, current_usage.current_scans - resource_release.get('concurrent_scans', 1))
        current_usage.cpu_percent = max(0.0, current_usage.cpu_percent - resource_release.get('cpu_percent', 5.0))
        current_usage.memory_mb = max(0.0, current_usage.memory_mb - resource_release.get('memory_mb', 100))
        current_usage.last_activity = time.time()
        
        self.logger.debug(f"Deallocated resources from tenant '{tenant_id}': {resource_release}")
        
        return {
            'success': True,
            'deallocated_resources': resource_release,
            'current_usage': {
                'current_scans': current_usage.current_scans,
                'cpu_percent': current_usage.cpu_percent,
                'memory_mb': current_usage.memory_mb
            }
        }
    
    def update_tenant_quota(self, tenant_id: str, new_quota: TenantQuota) -> bool:
        """Update tenant resource quota."""
        if tenant_id not in self.tenants:
            return False
        
        old_quota = self.tenant_quotas[tenant_id]
        self.tenant_quotas[tenant_id] = new_quota
        
        # Update tenant weight
        self.tenant_weights[tenant_id] = self._calculate_tenant_weight(new_quota.priority)
        
        self.logger.info(f"Updated quota for tenant '{tenant_id}': {old_quota.priority.value} -> {new_quota.priority.value}")
        return True
    
    def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant (stop resource allocation)."""
        if tenant_id not in self.tenants:
            return False
        
        self.tenants[tenant_id]['active'] = False
        self.tenants[tenant_id]['suspended_reason'] = reason
        self.tenants[tenant_id]['suspended_at'] = time.time()
        
        self.logger.warning(f"Suspended tenant '{tenant_id}': {reason}")
        return True
    
    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        if tenant_id not in self.tenants:
            return False
        
        self.tenants[tenant_id]['active'] = True
        if 'suspended_reason' in self.tenants[tenant_id]:
            del self.tenants[tenant_id]['suspended_reason']
        if 'suspended_at' in self.tenants[tenant_id]:
            del self.tenants[tenant_id]['suspended_at']
        
        self.logger.info(f"Activated tenant '{tenant_id}'")
        return True
    
    def get_tenant_usage(self, tenant_id: str, hours: int = 24) -> Optional[Dict[str, Any]]:
        """Get tenant usage statistics for specified time period."""
        if tenant_id not in self.tenants:
            return None
        
        current_usage = self.tenant_usage[tenant_id]
        quota = self.tenant_quotas[tenant_id]
        
        # Calculate usage over time period
        cutoff_time = time.time() - (hours * 3600)
        recent_usage = [
            usage for usage in self.usage_history[tenant_id]
            if usage.last_activity > cutoff_time
        ]
        
        # Usage statistics
        if recent_usage:
            avg_scans = sum(u.current_scans for u in recent_usage) / len(recent_usage)
            avg_cpu = sum(u.cpu_percent for u in recent_usage) / len(recent_usage)
            avg_memory = sum(u.memory_mb for u in recent_usage) / len(recent_usage)
            peak_scans = max(u.current_scans for u in recent_usage)
            peak_cpu = max(u.cpu_percent for u in recent_usage)
            peak_memory = max(u.memory_mb for u in recent_usage)
        else:
            avg_scans = avg_cpu = avg_memory = 0.0
            peak_scans = peak_cpu = peak_memory = 0.0
        
        return {
            'tenant_id': tenant_id,
            'time_period_hours': hours,
            'current_usage': {
                'current_scans': current_usage.current_scans,
                'cpu_percent': current_usage.cpu_percent,
                'memory_mb': current_usage.memory_mb,
                'total_requests': current_usage.total_requests,
                'last_activity': current_usage.last_activity
            },
            'quota_limits': {
                'max_concurrent_scans': quota.max_concurrent_scans,
                'max_cpu_percent': quota.max_cpu_percent,
                'max_memory_mb': quota.max_memory_mb,
                'max_requests_per_minute': quota.max_requests_per_minute
            },
            'usage_statistics': {
                'avg_concurrent_scans': avg_scans,
                'avg_cpu_percent': avg_cpu,
                'avg_memory_mb': avg_memory,
                'peak_concurrent_scans': peak_scans,
                'peak_cpu_percent': peak_cpu,
                'peak_memory_mb': peak_memory
            },
            'utilization_rates': {
                'scans_utilization': current_usage.current_scans / quota.max_concurrent_scans,
                'cpu_utilization': current_usage.cpu_percent / quota.max_cpu_percent,
                'memory_utilization': current_usage.memory_mb / quota.max_memory_mb
            },
            'priority': quota.priority.value,
            'isolation_level': self.tenant_isolation[tenant_id].level.value
        }
    
    async def start_monitoring(self):
        """Start tenant monitoring and cleanup."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Multi-tenant monitoring started")
    
    async def stop_monitoring(self):
        """Stop tenant monitoring."""
        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Multi-tenant monitoring stopped")
    
    async def _monitoring_loop(self):
        """Monitor tenant usage and enforce policies."""
        while self._monitoring:
            try:
                # Clean up old request history
                current_time = time.time()
                for tenant_id in self.request_history:
                    self.request_history[tenant_id] = [
                        timestamp for timestamp in self.request_history[tenant_id]
                        if current_time - timestamp < 60
                    ]
                    
                    # Update requests last minute count
                    self.tenant_usage[tenant_id].requests_last_minute = len(self.request_history[tenant_id])
                
                # Check for quota violations and idle tenants
                await self._check_tenant_violations()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in multi-tenant monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_tenant_violations(self):
        """Check for tenant quota violations."""
        current_time = time.time()
        
        for tenant_id, usage in self.tenant_usage.items():
            if not self.tenants[tenant_id]['active']:
                continue
            
            quota = self.tenant_quotas[tenant_id]
            
            # Check for quota violations
            violations = []
            
            if usage.current_scans > quota.max_concurrent_scans:
                violations.append(f"Concurrent scans: {usage.current_scans} > {quota.max_concurrent_scans}")
            
            if usage.cpu_percent > quota.max_cpu_percent:
                violations.append(f"CPU usage: {usage.cpu_percent:.1f}% > {quota.max_cpu_percent:.1f}%")
            
            if usage.memory_mb > quota.max_memory_mb:
                violations.append(f"Memory usage: {usage.memory_mb:.1f}MB > {quota.max_memory_mb}MB")
            
            if violations:
                self.logger.warning(f"Tenant '{tenant_id}' quota violations: {'; '.join(violations)}")
                
                # For now, just log violations. In production, might take enforcement actions
                # like throttling or temporary suspension
            
            # Check for idle tenants (no activity in last hour)
            if current_time - usage.last_activity > 3600:  # 1 hour
                self.logger.debug(f"Tenant '{tenant_id}' is idle (no activity in last hour)")
    
    def get_global_tenant_stats(self) -> Dict[str, Any]:
        """Get global statistics across all tenants."""
        active_tenants = len([t for t in self.tenants.values() if t['active']])
        total_tenants = len(self.tenants)
        
        # Aggregate usage
        total_scans = sum(usage.current_scans for usage in self.tenant_usage.values())
        total_cpu = sum(usage.cpu_percent for usage in self.tenant_usage.values())
        total_memory = sum(usage.memory_mb for usage in self.tenant_usage.values())
        total_requests = sum(usage.total_requests for usage in self.tenant_usage.values())
        
        # Priority distribution
        priority_counts = {}
        for quota in self.tenant_quotas.values():
            priority = quota.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Isolation level distribution
        isolation_counts = {}
        for isolation in self.tenant_isolation.values():
            level = isolation.level.value
            isolation_counts[level] = isolation_counts.get(level, 0) + 1
        
        return {
            'tenant_summary': {
                'total_tenants': total_tenants,
                'active_tenants': active_tenants,
                'suspended_tenants': total_tenants - active_tenants
            },
            'resource_usage': {
                'total_concurrent_scans': total_scans,
                'total_cpu_percent': total_cpu,
                'total_memory_mb': total_memory,
                'total_requests': total_requests
            },
            'capacity_utilization': {
                'scans_utilization': total_scans / self.global_resources['max_concurrent_scans'],
                'cpu_utilization': total_cpu / self.global_resources['total_cpu_percent'],
                'memory_utilization': total_memory / self.global_resources['total_memory_mb']
            },
            'tenant_distribution': {
                'by_priority': priority_counts,
                'by_isolation_level': isolation_counts
            },
            'monitoring_active': self._monitoring
        }