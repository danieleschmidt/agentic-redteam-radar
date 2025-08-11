"""
Advanced performance tuning and optimization system.
"""

import asyncio
import time
import psutil
import gc
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger


class OptimizationLevel(Enum):
    """Performance optimization levels."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


class OptimizationCategory(Enum):
    """Categories of optimizations."""
    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    NETWORK = "network"
    CACHING = "caching"
    CONCURRENCY = "concurrency"
    ALGORITHM = "algorithm"


@dataclass
class OptimizationProfile:
    """Configuration profile for performance tuning."""
    name: str
    level: OptimizationLevel
    enabled_categories: List[OptimizationCategory]
    memory_limit_mb: int = 1024
    cpu_limit_percent: float = 80.0
    max_concurrency: int = 10
    cache_size_mb: int = 256
    io_buffer_size: int = 65536
    network_timeout: float = 30.0
    gc_threshold: tuple = (700, 10, 10)
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read: int = 0
    disk_io_write: int = 0
    network_io_sent: int = 0
    network_io_recv: int = 0
    active_threads: int = 0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class OptimizationResult:
    """Result of an optimization operation."""
    optimization_name: str
    category: OptimizationCategory
    applied: bool
    before_metrics: PerformanceMetrics
    after_metrics: Optional[PerformanceMetrics] = None
    improvement_percent: float = 0.0
    description: str = ""
    warnings: List[str] = field(default_factory=list)


class PerformanceTuner:
    """
    Advanced performance tuning system for optimal resource utilization.
    
    Continuously monitors system performance and applies intelligent
    optimizations to improve throughput, reduce latency, and optimize
    resource usage.
    """
    
    def __init__(self):
        self.logger = get_logger("agentic_redteam.scaling.performance_tuner")
        
        # Configuration
        self.current_profile: Optional[OptimizationProfile] = None
        self.optimization_history: List[OptimizationResult] = []
        self.max_history_size = 500
        
        # Monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.monitoring_interval = 10.0  # seconds
        self._monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Optimization state
        self.applied_optimizations: Dict[str, Any] = {}
        self.optimization_callbacks: Dict[str, Callable] = {}
        
        # Performance baselines
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        self.performance_targets: Dict[str, float] = {
            'max_cpu_percent': 70.0,
            'max_memory_percent': 80.0,
            'min_throughput_rps': 10.0,
            'max_response_time_ms': 2000.0,
            'max_error_rate': 0.05
        }
        
        # Setup default profiles
        self._setup_default_profiles()
        
        # Auto-optimization settings
        self.auto_optimization_enabled = True
        self.optimization_threshold = 0.1  # 10% performance degradation
        
    def _setup_default_profiles(self):
        """Setup default optimization profiles."""
        self.profiles = {
            'conservative': OptimizationProfile(
                name="conservative",
                level=OptimizationLevel.CONSERVATIVE,
                enabled_categories=[
                    OptimizationCategory.MEMORY,
                    OptimizationCategory.CACHING
                ],
                memory_limit_mb=512,
                cpu_limit_percent=60.0,
                max_concurrency=5,
                cache_size_mb=128
            ),
            
            'balanced': OptimizationProfile(
                name="balanced",
                level=OptimizationLevel.BALANCED,
                enabled_categories=[
                    OptimizationCategory.MEMORY,
                    OptimizationCategory.CPU,
                    OptimizationCategory.CACHING,
                    OptimizationCategory.CONCURRENCY
                ],
                memory_limit_mb=1024,
                cpu_limit_percent=75.0,
                max_concurrency=8,
                cache_size_mb=256
            ),
            
            'aggressive': OptimizationProfile(
                name="aggressive",
                level=OptimizationLevel.AGGRESSIVE,
                enabled_categories=list(OptimizationCategory),
                memory_limit_mb=2048,
                cpu_limit_percent=85.0,
                max_concurrency=12,
                cache_size_mb=512
            ),
            
            'maximum': OptimizationProfile(
                name="maximum",
                level=OptimizationLevel.MAXIMUM,
                enabled_categories=list(OptimizationCategory),
                memory_limit_mb=4096,
                cpu_limit_percent=95.0,
                max_concurrency=20,
                cache_size_mb=1024,
                custom_settings={
                    'aggressive_gc': True,
                    'preemptive_caching': True,
                    'connection_pooling': True
                }
            )
        }
        
        self.logger.info(f"Initialized with {len(self.profiles)} optimization profiles")
    
    def apply_profile(self, profile_name: str) -> bool:
        """Apply a performance optimization profile."""
        if profile_name not in self.profiles:
            self.logger.error(f"Unknown optimization profile: {profile_name}")
            return False
        
        profile = self.profiles[profile_name]
        self.current_profile = profile
        
        # Record baseline before applying optimizations
        if not self.baseline_metrics:
            self.baseline_metrics = self._collect_current_metrics()
        
        # Apply optimizations based on profile
        optimization_results = []
        
        for category in profile.enabled_categories:
            results = self._apply_category_optimizations(category, profile)
            optimization_results.extend(results)
        
        # Record optimization results
        for result in optimization_results:
            self.optimization_history.append(result)
            if len(self.optimization_history) > self.max_history_size:
                self.optimization_history.pop(0)
        
        successful_optimizations = len([r for r in optimization_results if r.applied])
        self.logger.info(f"Applied profile '{profile_name}': {successful_optimizations}/{len(optimization_results)} optimizations successful")
        
        return True
    
    def _apply_category_optimizations(self, category: OptimizationCategory, 
                                    profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply optimizations for a specific category."""
        results = []
        
        if category == OptimizationCategory.MEMORY:
            results.extend(self._optimize_memory(profile))
        elif category == OptimizationCategory.CPU:
            results.extend(self._optimize_cpu(profile))
        elif category == OptimizationCategory.IO:
            results.extend(self._optimize_io(profile))
        elif category == OptimizationCategory.NETWORK:
            results.extend(self._optimize_network(profile))
        elif category == OptimizationCategory.CACHING:
            results.extend(self._optimize_caching(profile))
        elif category == OptimizationCategory.CONCURRENCY:
            results.extend(self._optimize_concurrency(profile))
        elif category == OptimizationCategory.ALGORITHM:
            results.extend(self._optimize_algorithms(profile))
        
        return results
    
    def _optimize_memory(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply memory optimizations."""
        results = []
        
        # Garbage collection tuning
        before_metrics = self._collect_current_metrics()
        
        try:
            # Adjust garbage collection thresholds
            old_thresholds = gc.get_threshold()
            gc.set_threshold(*profile.gc_threshold)
            
            # Force garbage collection
            collected = gc.collect()
            
            after_metrics = self._collect_current_metrics()
            
            memory_improvement = (before_metrics.memory_mb - after_metrics.memory_mb) / before_metrics.memory_mb * 100
            
            result = OptimizationResult(
                optimization_name="gc_tuning",
                category=OptimizationCategory.MEMORY,
                applied=True,
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                improvement_percent=memory_improvement,
                description=f"Adjusted GC thresholds and collected {collected} objects"
            )
            
            self.applied_optimizations['gc_threshold'] = profile.gc_threshold
            results.append(result)
            
        except Exception as e:
            result = OptimizationResult(
                optimization_name="gc_tuning",
                category=OptimizationCategory.MEMORY,
                applied=False,
                before_metrics=before_metrics,
                description=f"Failed to apply GC tuning: {e}",
                warnings=[str(e)]
            )
            results.append(result)
        
        # Memory limit enforcement
        try:
            # Set soft memory limit (not enforced at OS level, just tracked)
            self.applied_optimizations['memory_limit_mb'] = profile.memory_limit_mb
            
            result = OptimizationResult(
                optimization_name="memory_limit",
                category=OptimizationCategory.MEMORY,
                applied=True,
                before_metrics=before_metrics,
                description=f"Set memory limit to {profile.memory_limit_mb}MB"
            )
            results.append(result)
            
        except Exception as e:
            result = OptimizationResult(
                optimization_name="memory_limit",
                category=OptimizationCategory.MEMORY,
                applied=False,
                before_metrics=before_metrics,
                description=f"Failed to set memory limit: {e}",
                warnings=[str(e)]
            )
            results.append(result)
        
        return results
    
    def _optimize_cpu(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply CPU optimizations."""
        results = []
        before_metrics = self._collect_current_metrics()
        
        try:
            # CPU affinity optimization (if supported)
            import os
            if hasattr(os, 'sched_setaffinity'):
                # Use all available CPUs
                cpu_count = psutil.cpu_count()
                available_cpus = list(range(cpu_count))
                os.sched_setaffinity(0, available_cpus)
                
                result = OptimizationResult(
                    optimization_name="cpu_affinity",
                    category=OptimizationCategory.CPU,
                    applied=True,
                    before_metrics=before_metrics,
                    description=f"Set CPU affinity to use all {cpu_count} CPUs"
                )
                
                self.applied_optimizations['cpu_affinity'] = available_cpus
            else:
                result = OptimizationResult(
                    optimization_name="cpu_affinity",
                    category=OptimizationCategory.CPU,
                    applied=False,
                    before_metrics=before_metrics,
                    description="CPU affinity not supported on this platform",
                    warnings=["CPU affinity optimization skipped"]
                )
            
            results.append(result)
            
        except Exception as e:
            result = OptimizationResult(
                optimization_name="cpu_affinity",
                category=OptimizationCategory.CPU,
                applied=False,
                before_metrics=before_metrics,
                description=f"Failed to set CPU affinity: {e}",
                warnings=[str(e)]
            )
            results.append(result)
        
        return results
    
    def _optimize_io(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply I/O optimizations."""
        results = []
        before_metrics = self._collect_current_metrics()
        
        # I/O buffer size optimization
        result = OptimizationResult(
            optimization_name="io_buffer_size",
            category=OptimizationCategory.IO,
            applied=True,
            before_metrics=before_metrics,
            description=f"Set I/O buffer size to {profile.io_buffer_size} bytes"
        )
        
        self.applied_optimizations['io_buffer_size'] = profile.io_buffer_size
        results.append(result)
        
        return results
    
    def _optimize_network(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply network optimizations."""
        results = []
        before_metrics = self._collect_current_metrics()
        
        # Network timeout optimization
        result = OptimizationResult(
            optimization_name="network_timeout",
            category=OptimizationCategory.NETWORK,
            applied=True,
            before_metrics=before_metrics,
            description=f"Set network timeout to {profile.network_timeout}s"
        )
        
        self.applied_optimizations['network_timeout'] = profile.network_timeout
        results.append(result)
        
        return results
    
    def _optimize_caching(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply caching optimizations."""
        results = []
        before_metrics = self._collect_current_metrics()
        
        # Cache size optimization
        result = OptimizationResult(
            optimization_name="cache_size",
            category=OptimizationCategory.CACHING,
            applied=True,
            before_metrics=before_metrics,
            description=f"Set cache size to {profile.cache_size_mb}MB"
        )
        
        self.applied_optimizations['cache_size_mb'] = profile.cache_size_mb
        results.append(result)
        
        # Preemptive caching if enabled
        if profile.custom_settings.get('preemptive_caching', False):
            result = OptimizationResult(
                optimization_name="preemptive_caching",
                category=OptimizationCategory.CACHING,
                applied=True,
                before_metrics=before_metrics,
                description="Enabled preemptive caching for frequently accessed data"
            )
            
            self.applied_optimizations['preemptive_caching'] = True
            results.append(result)
        
        return results
    
    def _optimize_concurrency(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply concurrency optimizations.""" 
        results = []
        before_metrics = self._collect_current_metrics()
        
        # Concurrency limit optimization
        result = OptimizationResult(
            optimization_name="max_concurrency",
            category=OptimizationCategory.CONCURRENCY,
            applied=True,
            before_metrics=before_metrics,
            description=f"Set maximum concurrency to {profile.max_concurrency}"
        )
        
        self.applied_optimizations['max_concurrency'] = profile.max_concurrency
        results.append(result)
        
        # Connection pooling if enabled
        if profile.custom_settings.get('connection_pooling', False):
            result = OptimizationResult(
                optimization_name="connection_pooling",
                category=OptimizationCategory.CONCURRENCY,
                applied=True,
                before_metrics=before_metrics,
                description="Enabled connection pooling for improved resource utilization"
            )
            
            self.applied_optimizations['connection_pooling'] = True
            results.append(result)
        
        return results
    
    def _optimize_algorithms(self, profile: OptimizationProfile) -> List[OptimizationResult]:
        """Apply algorithmic optimizations."""
        results = []
        before_metrics = self._collect_current_metrics()
        
        # Example algorithmic optimization - enable fast path optimizations
        result = OptimizationResult(
            optimization_name="algorithm_fast_path",
            category=OptimizationCategory.ALGORITHM,
            applied=True,
            before_metrics=before_metrics,
            description="Enabled fast-path algorithmic optimizations"
        )
        
        self.applied_optimizations['algorithm_fast_path'] = True
        results.append(result)
        
        return results
    
    def _collect_current_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_io_read = disk_io.read_bytes if disk_io else 0
            disk_io_write = disk_io.write_bytes if disk_io else 0
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_io_sent = network_io.bytes_sent if network_io else 0
            network_io_recv = network_io.bytes_recv if network_io else 0
            
            # Process info
            active_threads = psutil.Process().num_threads()
            
            # Garbage collection info
            gc_collections = {}
            for i in range(3):
                gc_collections[i] = gc.get_count()[i]
            
            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read=disk_io_read,
                disk_io_write=disk_io_write,
                network_io_sent=network_io_sent,
                network_io_recv=network_io_recv,
                active_threads=active_threads,
                gc_collections=gc_collections
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {e}")
            return PerformanceMetrics()
    
    async def start_monitoring(self):
        """Start performance monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Performance monitoring loop."""
        while self._monitoring:
            try:
                # Collect metrics
                current_metrics = self._collect_current_metrics()
                
                # Store metrics
                self.metrics_history.append(current_metrics)
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history.pop(0)
                
                # Check for auto-optimization opportunities
                if self.auto_optimization_enabled:
                    await self._check_auto_optimization(current_metrics)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_auto_optimization(self, current_metrics: PerformanceMetrics):
        """Check if automatic optimization should be triggered."""
        if not self.baseline_metrics:
            return
        
        # Check if performance has degraded significantly
        performance_degraded = False
        reasons = []
        
        # CPU degradation
        if (current_metrics.cpu_percent > self.performance_targets['max_cpu_percent'] and
            current_metrics.cpu_percent > self.baseline_metrics.cpu_percent * (1 + self.optimization_threshold)):
            performance_degraded = True
            reasons.append("CPU usage degraded")
        
        # Memory degradation  
        if (current_metrics.memory_percent > self.performance_targets['max_memory_percent'] and
            current_metrics.memory_percent > self.baseline_metrics.memory_percent * (1 + self.optimization_threshold)):
            performance_degraded = True
            reasons.append("Memory usage degraded")
        
        # Trigger optimization if needed
        if performance_degraded:
            self.logger.info(f"Auto-optimization triggered: {', '.join(reasons)}")
            
            # Apply more aggressive profile
            if self.current_profile and self.current_profile.level != OptimizationLevel.MAXIMUM:
                next_level = self._get_next_optimization_level(self.current_profile.level)
                next_profile_name = self._get_profile_name_by_level(next_level)
                
                if next_profile_name:
                    self.logger.info(f"Escalating to {next_profile_name} optimization profile")
                    self.apply_profile(next_profile_name)
    
    def _get_next_optimization_level(self, current_level: OptimizationLevel) -> OptimizationLevel:
        """Get the next more aggressive optimization level."""
        level_progression = [
            OptimizationLevel.CONSERVATIVE,
            OptimizationLevel.BALANCED,
            OptimizationLevel.AGGRESSIVE,
            OptimizationLevel.MAXIMUM
        ]
        
        try:
            current_index = level_progression.index(current_level)
            if current_index < len(level_progression) - 1:
                return level_progression[current_index + 1]
        except ValueError:
            pass
        
        return OptimizationLevel.MAXIMUM
    
    def _get_profile_name_by_level(self, level: OptimizationLevel) -> Optional[str]:
        """Get profile name by optimization level."""
        for name, profile in self.profiles.items():
            if profile.level == level:
                return name
        return None
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        current_metrics = self._collect_current_metrics()
        
        # Calculate performance trends
        if len(self.metrics_history) >= 2:
            cpu_trend = self._calculate_trend([m.cpu_percent for m in self.metrics_history[-10:]])
            memory_trend = self._calculate_trend([m.memory_mb for m in self.metrics_history[-10:]])
        else:
            cpu_trend = 0.0
            memory_trend = 0.0
        
        # Optimization effectiveness
        successful_optimizations = len([r for r in self.optimization_history if r.applied])
        total_optimizations = len(self.optimization_history)
        
        return {
            'current_profile': self.current_profile.name if self.current_profile else None,
            'current_metrics': {
                'cpu_percent': current_metrics.cpu_percent,
                'memory_mb': current_metrics.memory_mb,
                'memory_percent': current_metrics.memory_percent,
                'active_threads': current_metrics.active_threads
            },
            'performance_trends': {
                'cpu_trend': cpu_trend,
                'memory_trend': memory_trend
            },
            'applied_optimizations': self.applied_optimizations.copy(),
            'optimization_effectiveness': {
                'successful_optimizations': successful_optimizations,
                'total_optimizations': total_optimizations,
                'success_rate': successful_optimizations / max(total_optimizations, 1)
            },
            'auto_optimization_enabled': self.auto_optimization_enabled,
            'monitoring_active': self._monitoring,
            'metrics_history_size': len(self.metrics_history)
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend for a series of values."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend
        return (values[-1] - values[0]) / len(values)