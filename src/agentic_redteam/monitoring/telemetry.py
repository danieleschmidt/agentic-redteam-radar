"""
Advanced telemetry and monitoring for Agentic RedTeam Radar.

Provides comprehensive metrics collection, monitoring, and alerting
for production deployments with OpenTelemetry integration.
"""

import time
import threading
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from contextlib import contextmanager
import json
import uuid

try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

from ..utils.logger import get_logger


@dataclass
class MetricPoint:
    """Individual metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp,
            'tags': self.tags,
            'unit': self.unit
        }


@dataclass
class ScanMetrics:
    """Comprehensive metrics for a security scan."""
    scan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Execution metrics
    patterns_executed: int = 0
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    
    # Vulnerability metrics
    vulnerabilities_found: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    
    # Performance metrics
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    concurrent_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Resource metrics
    cpu_usage_start: float = 0.0
    cpu_usage_end: float = 0.0
    memory_usage_start: float = 0.0
    memory_usage_end: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def finalize(self):
        """Finalize metrics collection."""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Calculate scan duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.successful_tests / self.total_tests
    
    @property
    def throughput(self) -> float:
        """Calculate tests per second."""
        duration = self.duration
        if duration == 0:
            return 0.0
        return self.total_tests / duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'scan_id': self.scan_id,
            'agent_name': self.agent_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'patterns_executed': self.patterns_executed,
            'total_tests': self.total_tests,
            'successful_tests': self.successful_tests,
            'failed_tests': self.failed_tests,
            'success_rate': self.success_rate,
            'throughput': self.throughput,
            'vulnerabilities_found': self.vulnerabilities_found,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'avg_response_time': self.avg_response_time,
            'max_response_time': self.max_response_time,
            'min_response_time': self.min_response_time if self.min_response_time != float('inf') else 0.0,
            'concurrent_requests': self.concurrent_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cpu_usage_delta': self.cpu_usage_end - self.cpu_usage_start,
            'memory_usage_delta': self.memory_usage_end - self.memory_usage_start,
            'custom_metrics': self.custom_metrics
        }


class MetricsCollector:
    """
    High-performance metrics collector with buffering and aggregation.
    
    Collects metrics from scanning operations and provides
    efficient storage and retrieval mechanisms.
    """
    
    def __init__(self, buffer_size: int = 10000, flush_interval: float = 60.0):
        """
        Initialize metrics collector.
        
        Args:
            buffer_size: Maximum number of metrics to buffer
            flush_interval: Interval to flush metrics (seconds)
        """
        self.logger = get_logger(__name__)
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Metric storage
        self.metrics_buffer = deque(maxlen=buffer_size)
        self.scan_metrics = {}
        self.aggregated_metrics = defaultdict(list)
        
        # Threading
        self.buffer_lock = threading.Lock()
        self.flush_timer = None
        self._stop_event = threading.Event()
        
        # Handlers
        self.metric_handlers: List[Callable] = []
        
        # Start background flushing
        self._start_flush_timer()
        
        self.logger.info(f"Metrics collector initialized (buffer: {buffer_size}, flush: {flush_interval}s)")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, unit: str = ""):
        """
        Record a metric point.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
            unit: Optional unit of measurement
        """
        metric = MetricPoint(
            name=name,
            value=value,
            tags=tags or {},
            unit=unit
        )
        
        with self.buffer_lock:
            self.metrics_buffer.append(metric)
        
        # Trigger immediate flush if buffer is full
        if len(self.metrics_buffer) >= self.buffer_size * 0.9:  # 90% full
            self._flush_metrics_async()
    
    def start_scan_metrics(self, agent_name: str) -> str:
        """
        Start metrics collection for a scan.
        
        Args:
            agent_name: Name of the agent being scanned
            
        Returns:
            Scan ID for tracking
        """
        scan_metrics = ScanMetrics(agent_name=agent_name)
        
        # Initialize system metrics
        try:
            import psutil
            scan_metrics.cpu_usage_start = psutil.cpu_percent()
            scan_metrics.memory_usage_start = psutil.virtual_memory().percent
        except ImportError:
            pass
        
        self.scan_metrics[scan_metrics.scan_id] = scan_metrics
        
        self.logger.debug(f"Started scan metrics: {scan_metrics.scan_id}")
        return scan_metrics.scan_id
    
    def update_scan_metrics(self, scan_id: str, **kwargs):
        """
        Update scan metrics.
        
        Args:
            scan_id: Scan identifier
            **kwargs: Metric updates
        """
        if scan_id not in self.scan_metrics:
            self.logger.warning(f"Unknown scan ID: {scan_id}")
            return
        
        scan_metrics = self.scan_metrics[scan_id]
        
        for key, value in kwargs.items():
            if hasattr(scan_metrics, key):
                setattr(scan_metrics, key, value)
            else:
                scan_metrics.custom_metrics[key] = value
    
    def finalize_scan_metrics(self, scan_id: str) -> Optional[ScanMetrics]:
        """
        Finalize and retrieve scan metrics.
        
        Args:
            scan_id: Scan identifier
            
        Returns:
            Finalized scan metrics
        """
        if scan_id not in self.scan_metrics:
            self.logger.warning(f"Unknown scan ID: {scan_id}")
            return None
        
        scan_metrics = self.scan_metrics[scan_id]
        
        # Finalize system metrics
        try:
            import psutil
            scan_metrics.cpu_usage_end = psutil.cpu_percent()
            scan_metrics.memory_usage_end = psutil.virtual_memory().percent
        except ImportError:
            pass
        
        scan_metrics.finalize()
        
        # Record aggregated metrics
        self.record_metric("scan_duration", scan_metrics.duration, {"agent": scan_metrics.agent_name}, "seconds")
        self.record_metric("scan_throughput", scan_metrics.throughput, {"agent": scan_metrics.agent_name}, "tests/sec")
        self.record_metric("vulnerabilities_found", scan_metrics.vulnerabilities_found, {"agent": scan_metrics.agent_name})
        
        self.logger.info(f"Finalized scan metrics: {scan_id} ({scan_metrics.duration:.2f}s)")
        return scan_metrics
    
    def add_handler(self, handler: Callable[[List[MetricPoint]], None]):
        """
        Add a metric handler.
        
        Args:
            handler: Function to process metrics
        """
        self.metric_handlers.append(handler)
        self.logger.debug(f"Added metric handler: {handler.__name__}")
    
    def get_metrics_summary(self, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get metrics summary for the specified time window.
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            Metrics summary
        """
        cutoff_time = time.time() - (window_minutes * 60)
        
        # Filter recent metrics
        with self.buffer_lock:
            recent_metrics = [m for m in self.metrics_buffer if m.timestamp >= cutoff_time]
        
        # Group by metric name
        grouped_metrics = defaultdict(list)
        for metric in recent_metrics:
            grouped_metrics[metric.name].append(metric.value)
        
        # Calculate summary statistics
        summary = {}
        for name, values in grouped_metrics.items():
            if values:
                summary[name] = {
                    'count': len(values),
                    'sum': sum(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[-1] if values else 0
                }
        
        return {
            'window_minutes': window_minutes,
            'total_metrics': len(recent_metrics),
            'metrics': summary,
            'active_scans': len(self.scan_metrics)
        }
    
    def _flush_metrics_async(self):
        """Flush metrics asynchronously."""
        def flush_worker():
            try:
                self._flush_metrics()
            except Exception as e:
                self.logger.error(f"Error flushing metrics: {e}")
        
        threading.Thread(target=flush_worker, daemon=True).start()
    
    def _flush_metrics(self):
        """Flush buffered metrics to handlers."""
        if not self.metric_handlers:
            return
        
        # Get metrics to flush
        with self.buffer_lock:
            if not self.metrics_buffer:
                return
            
            metrics_to_flush = list(self.metrics_buffer)
            self.metrics_buffer.clear()
        
        # Send to handlers
        for handler in self.metric_handlers:
            try:
                handler(metrics_to_flush)
            except Exception as e:
                self.logger.error(f"Error in metric handler {handler.__name__}: {e}")
        
        self.logger.debug(f"Flushed {len(metrics_to_flush)} metrics")
    
    def _start_flush_timer(self):
        """Start periodic metric flushing."""
        def flush_periodically():
            while not self._stop_event.wait(self.flush_interval):
                self._flush_metrics()
        
        self.flush_timer = threading.Thread(target=flush_periodically, daemon=True)
        self.flush_timer.start()
    
    def shutdown(self):
        """Shutdown metrics collector."""
        self.logger.info("Shutting down metrics collector")
        
        # Stop periodic flushing
        self._stop_event.set()
        if self.flush_timer:
            self.flush_timer.join(timeout=5)
        
        # Final flush
        self._flush_metrics()


class OpenTelemetryIntegration:
    """
    OpenTelemetry integration for enterprise monitoring.
    
    Provides integration with OpenTelemetry for distributed tracing
    and metrics export to monitoring systems.
    """
    
    def __init__(self, endpoint: Optional[str] = None, service_name: str = "agentic-redteam-radar"):
        """
        Initialize OpenTelemetry integration.
        
        Args:
            endpoint: OTLP endpoint URL
            service_name: Service name for telemetry
        """
        self.logger = get_logger(__name__)
        self.service_name = service_name
        self.endpoint = endpoint
        self.enabled = OTEL_AVAILABLE and endpoint is not None
        
        if not OTEL_AVAILABLE:
            self.logger.warning("OpenTelemetry not available - install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
            return
        
        if not endpoint:
            self.logger.info("No OTLP endpoint configured - OpenTelemetry disabled")
            return
        
        try:
            # Configure tracing
            trace.set_tracer_provider(TracerProvider())
            tracer_provider = trace.get_tracer_provider()
            
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            span_processor = trace.BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            self.tracer = trace.get_tracer(service_name)
            
            # Configure metrics
            metrics.set_meter_provider(MeterProvider())
            meter_provider = metrics.get_meter_provider()
            
            self.meter = meter_provider.get_meter(service_name)
            
            # Create metric instruments
            self.scan_duration_histogram = self.meter.create_histogram(
                name="scan_duration_seconds",
                description="Duration of security scans",
                unit="s"
            )
            
            self.vulnerability_counter = self.meter.create_counter(
                name="vulnerabilities_found_total",
                description="Total vulnerabilities found"
            )
            
            self.test_counter = self.meter.create_counter(
                name="tests_executed_total",
                description="Total tests executed"
            )
            
            self.logger.info(f"OpenTelemetry initialized with endpoint: {endpoint}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry: {e}")
            self.enabled = False
    
    @contextmanager
    def trace_scan(self, agent_name: str, patterns: List[str]):
        """
        Create a trace span for a security scan.
        
        Args:
            agent_name: Name of the agent being scanned
            patterns: List of attack patterns
        """
        if not self.enabled:
            yield None
            return
        
        with self.tracer.start_as_current_span("security_scan") as span:
            # Set span attributes
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("scan.patterns", ",".join(patterns))
            span.set_attribute("scan.pattern_count", len(patterns))
            
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def record_scan_metrics(self, scan_metrics: ScanMetrics):
        """
        Record scan metrics to OpenTelemetry.
        
        Args:
            scan_metrics: Scan metrics to record
        """
        if not self.enabled:
            return
        
        try:
            # Record duration
            self.scan_duration_histogram.record(
                scan_metrics.duration,
                {"agent.name": scan_metrics.agent_name}
            )
            
            # Record vulnerabilities
            self.vulnerability_counter.add(
                scan_metrics.vulnerabilities_found,
                {"agent.name": scan_metrics.agent_name}
            )
            
            # Record tests
            self.test_counter.add(
                scan_metrics.total_tests,
                {"agent.name": scan_metrics.agent_name}
            )
            
            self.logger.debug(f"Recorded OpenTelemetry metrics for scan: {scan_metrics.scan_id}")
            
        except Exception as e:
            self.logger.error(f"Error recording OpenTelemetry metrics: {e}")


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Provides real-time performance monitoring, alerting, and
    optimization recommendations for production deployments.
    """
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize performance monitor.
        
        Args:
            metrics_collector: Optional metrics collector instance
        """
        self.logger = get_logger(__name__)
        self.metrics_collector = metrics_collector or MetricsCollector()
        
        # Performance thresholds
        self.thresholds = {
            'max_scan_duration': 300.0,      # 5 minutes
            'min_success_rate': 0.95,        # 95%
            'max_memory_usage': 0.85,        # 85%
            'max_cpu_usage': 0.90,           # 90%
            'min_throughput': 1.0,           # 1 test/sec
            'max_error_rate': 0.05           # 5%
        }
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        # Monitoring state
        self.monitoring_active = True
        self.alert_cooldown = {}  # Alert cooldown tracking
        self.cooldown_period = 300  # 5 minutes
        
        self.logger.info("Performance monitor initialized")
    
    def add_alert_handler(self, handler: Callable[[str, Dict[str, Any]], None]):
        """
        Add an alert handler.
        
        Args:
            handler: Function to handle alerts
        """
        self.alert_handlers.append(handler)
        self.logger.debug(f"Added alert handler: {handler.__name__}")
    
    def check_performance_thresholds(self, scan_metrics: ScanMetrics):
        """
        Check performance metrics against thresholds.
        
        Args:
            scan_metrics: Scan metrics to check
        """
        if not self.monitoring_active:
            return
        
        alerts = []
        
        # Check scan duration
        if scan_metrics.duration > self.thresholds['max_scan_duration']:
            alerts.append({
                'type': 'performance_degradation',
                'metric': 'scan_duration',
                'value': scan_metrics.duration,
                'threshold': self.thresholds['max_scan_duration'],
                'agent': scan_metrics.agent_name
            })
        
        # Check success rate
        if scan_metrics.success_rate < self.thresholds['min_success_rate']:
            alerts.append({
                'type': 'quality_degradation',
                'metric': 'success_rate',
                'value': scan_metrics.success_rate,
                'threshold': self.thresholds['min_success_rate'],
                'agent': scan_metrics.agent_name
            })
        
        # Check throughput
        if scan_metrics.throughput < self.thresholds['min_throughput']:
            alerts.append({
                'type': 'performance_degradation',
                'metric': 'throughput',
                'value': scan_metrics.throughput,
                'threshold': self.thresholds['min_throughput'],
                'agent': scan_metrics.agent_name
            })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert to registered handlers."""
        alert_key = f"{alert['type']}_{alert['metric']}"
        current_time = time.time()
        
        # Check cooldown
        if alert_key in self.alert_cooldown:
            if current_time - self.alert_cooldown[alert_key] < self.cooldown_period:
                return  # Still in cooldown
        
        # Update cooldown
        self.alert_cooldown[alert_key] = current_time
        
        # Send to handlers
        for handler in self.alert_handlers:
            try:
                handler(alert['type'], alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler {handler.__name__}: {e}")
        
        self.logger.warning(f"Performance alert: {alert}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Health status dictionary
        """
        try:
            # Get system metrics
            import psutil
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get recent metrics
            recent_metrics = self.metrics_collector.get_metrics_summary(30)  # Last 30 minutes
            
            # Determine health status
            health_issues = []
            
            if cpu_percent > self.thresholds['max_cpu_usage'] * 100:
                health_issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory.percent > self.thresholds['max_memory_usage'] * 100:
                health_issues.append(f"High memory usage: {memory.percent:.1f}%")
            
            if disk.percent > 90:
                health_issues.append(f"High disk usage: {disk.percent:.1f}%")
            
            status = "healthy" if not health_issues else "degraded" if len(health_issues) < 3 else "unhealthy"
            
            return {
                'status': status,
                'timestamp': time.time(),
                'issues': health_issues,
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'active_scans': recent_metrics.get('active_scans', 0)
                },
                'metrics_summary': recent_metrics,
                'thresholds': self.thresholds
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {
                'status': 'unknown',
                'timestamp': time.time(),
                'error': str(e)
            }


# Global instances
_metrics_collector: Optional[MetricsCollector] = None
_performance_monitor: Optional[PerformanceMonitor] = None
_otel_integration: Optional[OpenTelemetryIntegration] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(get_metrics_collector())
    return _performance_monitor


def get_otel_integration(endpoint: Optional[str] = None) -> OpenTelemetryIntegration:
    """Get global OpenTelemetry integration instance."""
    global _otel_integration
    if _otel_integration is None:
        _otel_integration = OpenTelemetryIntegration(endpoint)
    return _otel_integration