"""
Telemetry and metrics collection for Agentic RedTeam Radar.

Provides Prometheus metrics, performance monitoring, and observability features.
"""

import time
try:
    import psutil
except ImportError:
    psutil = None
from typing import Dict, Any, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

from ..utils.logger import setup_logger


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class TelemetryCollector:
    """Collects and manages telemetry data."""
    
    def __init__(self):
        """Initialize telemetry collector."""
        self.logger = setup_logger("agentic_redteam.telemetry")
        self._lock = Lock()
        
        # Metrics storage
        self._scan_metrics = deque(maxlen=1000)
        self._performance_metrics = deque(maxlen=1000) 
        self._error_metrics = deque(maxlen=500)
        self._system_metrics = deque(maxlen=100)
        
        # Counters
        self._scan_counter = 0
        self._error_counter = 0
        self._vulnerability_counter = 0
        
        # Histograms (simplified)
        self._scan_duration_buckets = defaultdict(int)
        self._pattern_execution_buckets = defaultdict(int)
        
        self.logger.info("Telemetry collector initialized")
    
    def record_scan_start(self, agent_name: str, pattern_count: int) -> None:
        """Record start of a security scan."""
        with self._lock:
            self._scan_counter += 1
            
            metric = MetricPoint(
                timestamp=time.time(),
                value=1.0,
                labels={
                    'agent_name': agent_name,
                    'pattern_count': str(pattern_count),
                    'event': 'scan_start'
                }
            )
            self._scan_metrics.append(metric)
            
            self.logger.debug(f"Recorded scan start for agent: {agent_name}")
    
    def record_scan_complete(self, agent_name: str, duration: float, 
                           vulnerability_count: int, pattern_count: int) -> None:
        """Record completion of a security scan."""
        with self._lock:
            self._vulnerability_counter += vulnerability_count
            
            # Record scan completion
            metric = MetricPoint(
                timestamp=time.time(),
                value=duration,
                labels={
                    'agent_name': agent_name,
                    'vulnerability_count': str(vulnerability_count),
                    'pattern_count': str(pattern_count),
                    'event': 'scan_complete'
                }
            )
            self._scan_metrics.append(metric)
            
            # Update duration histogram buckets
            self._update_histogram_bucket(self._scan_duration_buckets, duration)
            
            self.logger.debug(f"Recorded scan completion: {agent_name}, {duration:.2f}s, {vulnerability_count} vulns")
    
    def record_error(self, error_type: str, component: str, details: str = "") -> None:
        """Record an error occurrence."""
        with self._lock:
            self._error_counter += 1
            
            metric = MetricPoint(
                timestamp=time.time(),
                value=1.0,
                labels={
                    'error_type': error_type,
                    'component': component,
                    'details': details[:100]  # Truncate long details
                }
            )
            self._error_metrics.append(metric)
            
            self.logger.debug(f"Recorded error: {error_type} in {component}")
    
    def record_pattern_execution(self, pattern_name: str, duration: float, 
                                success: bool, vulnerabilities_found: int) -> None:
        """Record execution of an attack pattern."""
        with self._lock:
            metric = MetricPoint(
                timestamp=time.time(),
                value=duration,
                labels={
                    'pattern_name': pattern_name,
                    'success': str(success).lower(),
                    'vulnerabilities_found': str(vulnerabilities_found)
                }
            )
            self._performance_metrics.append(metric)
            
            # Update pattern execution histogram
            self._update_histogram_bucket(self._pattern_execution_buckets, duration)
    
    def record_system_metrics(self) -> None:
        """Record current system resource usage."""
        if not psutil:
            # Fallback metrics when psutil is not available
            with self._lock:
                system_metric = MetricPoint(
                    timestamp=time.time(),
                    value=0.0,
                    labels={
                        'cpu_percent': '0.0',
                        'memory_percent': '0.0', 
                        'memory_available_gb': '1.0',
                        'disk_free_gb': '10.0',
                        'status': 'psutil_unavailable'
                    }
                )
                self._system_metrics.append(system_metric)
            return
        
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            with self._lock:
                system_metric = MetricPoint(
                    timestamp=time.time(),
                    value=0.0,  # Composite metric
                    labels={
                        'cpu_percent': f"{cpu_percent:.1f}",
                        'memory_percent': f"{memory.percent:.1f}",
                        'memory_available_gb': f"{memory.available / (1024**3):.2f}",
                        'disk_free_gb': f"{disk.free / (1024**3):.2f}"
                    }
                )
                self._system_metrics.append(system_metric)
                
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
    
    def _update_histogram_bucket(self, buckets: Dict[str, int], value: float) -> None:
        """Update histogram buckets with new value."""
        # Simple histogram with predefined buckets
        histogram_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        
        for bucket in histogram_buckets:
            if value <= bucket:
                buckets[f"le_{bucket}"] += 1
        
        # +Inf bucket
        buckets["le_inf"] += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        with self._lock:
            current_time = time.time()
            
            # Recent scans (last hour)
            recent_scans = [
                m for m in self._scan_metrics 
                if current_time - m.timestamp < 3600 and m.labels.get('event') == 'scan_complete'
            ]
            
            # Calculate rates
            scan_rate = len(recent_scans) / 60 if recent_scans else 0  # per minute
            
            # Calculate average scan duration
            avg_duration = (
                sum(m.value for m in recent_scans) / len(recent_scans) 
                if recent_scans else 0
            )
            
            # Recent errors
            recent_errors = [
                m for m in self._error_metrics
                if current_time - m.timestamp < 3600
            ]
            
            return {
                'total_scans': self._scan_counter,
                'total_errors': self._error_counter,
                'total_vulnerabilities_found': self._vulnerability_counter,
                'scans_per_minute': scan_rate,
                'avg_scan_duration_seconds': avg_duration,
                'recent_errors_count': len(recent_errors),
                'scan_duration_histogram': dict(self._scan_duration_buckets),
                'pattern_execution_histogram': dict(self._pattern_execution_buckets),
                'last_system_metrics': self._system_metrics[-1].labels if self._system_metrics else {},
                'collection_timestamp': current_time
            }
    
    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus format metrics."""
        summary = self.get_metrics_summary()
        current_time = time.time()
        
        metrics_lines = [
            "# HELP radar_scans_total Total number of security scans performed",
            "# TYPE radar_scans_total counter",
            f'radar_scans_total {summary["total_scans"]} {int(current_time * 1000)}',
            "",
            "# HELP radar_errors_total Total number of errors encountered",
            "# TYPE radar_errors_total counter", 
            f'radar_errors_total {summary["total_errors"]} {int(current_time * 1000)}',
            "",
            "# HELP radar_vulnerabilities_total Total vulnerabilities found",
            "# TYPE radar_vulnerabilities_total counter",
            f'radar_vulnerabilities_total {summary["total_vulnerabilities_found"]} {int(current_time * 1000)}',
            "",
            "# HELP radar_scan_duration_seconds Histogram of scan durations",
            "# TYPE radar_scan_duration_seconds histogram"
        ]
        
        # Add histogram buckets
        for bucket, count in summary["scan_duration_histogram"].items():
            if bucket.startswith("le_"):
                bucket_value = bucket[3:] if bucket != "le_inf" else "+Inf"
                metrics_lines.append(f'radar_scan_duration_seconds_bucket{{le="{bucket_value}"}} {count}')
        
        metrics_lines.extend([
            "",
            "# HELP radar_scans_per_minute Current scan rate",
            "# TYPE radar_scans_per_minute gauge",
            f'radar_scans_per_minute {summary["scans_per_minute"]:.2f} {int(current_time * 1000)}'
        ])
        
        return "\n".join(metrics_lines)


# Global telemetry collector instance
_telemetry_collector = None
_collector_lock = Lock()


def get_telemetry_collector() -> TelemetryCollector:
    """Get or create global telemetry collector instance."""
    global _telemetry_collector
    
    if _telemetry_collector is None:
        with _collector_lock:
            if _telemetry_collector is None:
                _telemetry_collector = TelemetryCollector()
    
    return _telemetry_collector


def record_scan_metrics(agent_name: str, duration: float, vulnerability_count: int, 
                       pattern_count: int) -> None:
    """Convenience function to record scan metrics."""
    collector = get_telemetry_collector()
    collector.record_scan_complete(agent_name, duration, vulnerability_count, pattern_count)


def record_error_metrics(error_type: str, component: str, details: str = "") -> None:
    """Convenience function to record error metrics."""
    collector = get_telemetry_collector()
    collector.record_error(error_type, component, details)


def get_prometheus_metrics() -> Dict[str, Any]:
    """Get Prometheus metrics in JSON format."""
    collector = get_telemetry_collector()
    
    # Record current system metrics
    collector.record_system_metrics()
    
    # Return both prometheus format and summary
    return {
        'metrics_text': collector.get_prometheus_metrics(),
        'summary': collector.get_metrics_summary(),
        'format': 'prometheus'
    }


# Aliases for scanner compatibility
def get_metrics_collector() -> TelemetryCollector:
    """Get metrics collector instance (alias for get_telemetry_collector)."""
    return get_telemetry_collector()


class PerformanceMonitor:
    """Performance monitoring wrapper for compatibility."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.logger = setup_logger("agentic_redteam.performance_monitor")
        self.collector = get_telemetry_collector()
        self._alert_handlers = []
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'metrics_active': True
        }
    
    def add_alert_handler(self, handler):
        """Add alert handler."""
        self._alert_handlers.append(handler)
    
    def check_performance_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check performance thresholds and trigger alerts."""
        # Simple threshold checking
        if metrics.get('avg_scan_duration_seconds', 0) > 10.0:
            for handler in self._alert_handlers:
                try:
                    handler('performance_degradation', {
                        'metric': 'avg_scan_duration',
                        'value': metrics['avg_scan_duration_seconds'],
                        'threshold': 10.0
                    })
                except Exception as e:
                    self.logger.error(f"Alert handler error: {e}")


# Global performance monitor instance
_performance_monitor = None
_monitor_lock = Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _performance_monitor
    
    if _performance_monitor is None:
        with _monitor_lock:
            if _performance_monitor is None:
                _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor