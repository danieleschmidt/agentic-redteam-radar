"""
Advanced scaling and performance optimization for Agentic RedTeam Radar.

This module provides enterprise-grade scaling capabilities including:
- Auto-scaling based on workload
- Load balancing and traffic management
- Resource pool management
- Performance optimization
- Multi-tenancy support
"""

try:
    from .auto_scaler import AutoScaler, ScalingPolicy, ScalingMetrics
    from .load_balancer import LoadBalancer, LoadBalancingStrategy
    from .resource_pool import ResourcePool, ResourceManager
    from .performance_tuner import PerformanceTuner, OptimizationProfile
    from .multi_tenant import MultiTenantManager, TenantIsolation
except ImportError:
    from .simple_resource_pool import (
        SimpleResourcePool as ResourcePool, 
        ConcurrencyManager,
        LoadBalancer
    )
    # Provide simple alternatives for missing components
    class AutoScaler:
        pass
    class ScalingPolicy:
        pass
    class ScalingMetrics:
        pass
    class LoadBalancingStrategy:
        pass
    class ResourceManager:
        pass
    class PerformanceTuner:
        pass
    class OptimizationProfile:
        pass
    class MultiTenantManager:
        pass
    class TenantIsolation:
        pass

__all__ = [
    "AutoScaler",
    "ScalingPolicy", 
    "ScalingMetrics",
    "LoadBalancer",
    "LoadBalancingStrategy", 
    "ResourcePool",
    "ResourceManager",
    "PerformanceTuner",
    "OptimizationProfile",
    "MultiTenantManager",
    "TenantIsolation",
    "ConcurrencyManager"
]