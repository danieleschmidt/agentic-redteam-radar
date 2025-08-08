"""
Performance optimization module for Agentic RedTeam Radar.

Provides comprehensive performance monitoring, optimization,
and scalability features for high-throughput operation.
"""

try:
    from .optimizer import (
        PerformanceProfiler,
        PerformanceOptimizer,
        profile_performance,
        get_performance_optimizer
    )
    OPTIMIZER_AVAILABLE = True
except ImportError:
    # Fallback implementations when psutil is not available
    class PerformanceProfiler:
        def profile_function(self, func):
            return func
    
    class PerformanceOptimizer:
        def get_performance_report(self):
            return {'status': 'optimizer_unavailable'}
    
    def profile_performance(func):
        return func
    
    def get_performance_optimizer():
        return PerformanceOptimizer()
    
    OPTIMIZER_AVAILABLE = False

__all__ = [
    "PerformanceProfiler",
    "PerformanceOptimizer",
    "profile_performance",
    "get_performance_optimizer",
    "OPTIMIZER_AVAILABLE"
]