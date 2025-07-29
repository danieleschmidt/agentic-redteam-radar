# Observability Framework

This document outlines the comprehensive observability strategy for the Agentic RedTeam Radar project, including monitoring, logging, metrics, tracing, and alerting configurations.

## Framework Overview

Our observability framework follows the three pillars of observability:

1. **Metrics**: Quantitative measurements of system behavior
2. **Logs**: Detailed records of events and transactions
3. **Traces**: Request flow through distributed systems

Additionally, we implement:
- **Alerting**: Proactive notification of issues
- **Dashboards**: Visual representation of system health
- **SLI/SLO Monitoring**: Service level indicator and objective tracking

## Metrics Collection

### Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'radar-production'
    environment: 'production'

rule_files:
  - "rules/*.yml"

scrape_configs:
  # Application metrics
  - job_name: 'radar-scanner'
    static_configs:
      - targets: ['radar-scanner:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
    params:
      format: ['prometheus']

  # Node exporter for system metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # PostgreSQL metrics
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis metrics
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Kubernetes metrics (if applicable)
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# Storage configuration
storage:
  tsdb:
    retention.time: 30d
    retention.size: 50GB
    path: /prometheus/data
```

### Application Metrics

```python
# src/agentic_redteam/monitoring/metrics.py
"""
Application metrics collection using Prometheus client.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
from typing import Dict, Any
import time
import functools
import logging

logger = logging.getLogger(__name__)

# Define metrics
SCAN_REQUESTS_TOTAL = Counter(
    'radar_scan_requests_total',
    'Total number of scan requests',
    ['agent_type', 'pattern_type', 'status']
)

SCAN_DURATION_SECONDS = Histogram(
    'radar_scan_duration_seconds',
    'Time spent processing scan requests',
    ['agent_type', 'pattern_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

ACTIVE_SCANS = Gauge(
    'radar_active_scans',
    'Number of currently active scans',
    ['agent_type']
)

VULNERABILITIES_FOUND = Counter(
    'radar_vulnerabilities_found_total',
    'Total vulnerabilities found',
    ['severity', 'pattern_type', 'agent_type']
)

ATTACK_PATTERNS_EXECUTED = Counter(
    'radar_attack_patterns_executed_total',
    'Total attack patterns executed',
    ['pattern_type', 'status']
)

SYSTEM_INFO = Info(
    'radar_system_info',
    'System information'
)

# Performance metrics
MEMORY_USAGE_BYTES = Gauge(
    'radar_memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)

CPU_USAGE_PERCENT = Gauge(
    'radar_cpu_usage_percent',
    'CPU usage percentage',
    ['component']
)

DATABASE_CONNECTIONS = Gauge(
    'radar_database_connections',
    'Number of database connections',
    ['status']
)

API_REQUEST_DURATION = Histogram(
    'radar_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ERROR_RATE = Counter(
    'radar_errors_total',
    'Total errors by type',
    ['error_type', 'component']
)


class MetricsCollector:
    """Centralized metrics collection and management."""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self.server_started = False
    
    def start_metrics_server(self):
        """Start Prometheus metrics server."""
        if not self.server_started:
            try:
                start_http_server(self.port)
                self.server_started = True
                logger.info(f"Metrics server started on port {self.port}")
                
                # Set system info
                SYSTEM_INFO.info({
                    'version': self._get_version(),
                    'python_version': self._get_python_version(),
                    'build_time': self._get_build_time()
                })
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
    
    def _get_version(self) -> str:
        """Get application version."""
        try:
            from agentic_redteam import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def _get_python_version(self) -> str:
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_build_time(self) -> str:
        """Get build timestamp."""
        import os
        return os.environ.get('BUILD_TIME', 'unknown')
    
    def record_scan_request(self, agent_type: str, pattern_type: str, status: str):
        """Record a scan request."""
        SCAN_REQUESTS_TOTAL.labels(
            agent_type=agent_type,
            pattern_type=pattern_type,
            status=status
        ).inc()
    
    def record_vulnerability(self, severity: str, pattern_type: str, agent_type: str):
        """Record a found vulnerability."""
        VULNERABILITIES_FOUND.labels(
            severity=severity,
            pattern_type=pattern_type,
            agent_type=agent_type
        ).inc()
    
    def record_error(self, error_type: str, component: str):
        """Record an error."""
        ERROR_RATE.labels(
            error_type=error_type,
            component=component
        ).inc()


def track_scan_duration(agent_type: str, pattern_type: str):
    """Decorator to track scan duration."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                ACTIVE_SCANS.labels(agent_type=agent_type).inc()
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                SCAN_DURATION_SECONDS.labels(
                    agent_type=agent_type,
                    pattern_type=pattern_type
                ).observe(duration)
                
                return result
            finally:
                ACTIVE_SCANS.labels(agent_type=agent_type).dec()
        
        return wrapper
    return decorator


def track_api_request(method: str, endpoint: str):
    """Decorator to track API request metrics."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = "unknown"
            
            try:
                result = func(*args, **kwargs)
                # Assume successful if no exception
                status_code = "200"
                return result
            except Exception as e:
                status_code = "500"
                raise
            finally:
                duration = time.time() - start_time
                API_REQUEST_DURATION.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)
        
        return wrapper
    return decorator


# Global metrics collector instance
metrics_collector = MetricsCollector()
```

### Custom Metrics Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "Agentic RedTeam Radar - Application Metrics",
    "tags": ["radar", "security", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Scan Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(radar_scan_requests_total[5m])",
            "legendFormat": "{{agent_type}} - {{pattern_type}} - {{status}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests per second"
          }
        ]
      },
      {
        "title": "Scan Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(radar_scan_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(radar_scan_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ],
        "yAxes": [
          {
            "label": "Duration (seconds)"
          }
        ]
      },
      {
        "title": "Active Scans",
        "type": "singlestat",
        "targets": [
          {
            "expr": "sum(radar_active_scans)"
          }
        ]
      },
      {
        "title": "Vulnerabilities Found",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(radar_vulnerabilities_found_total[1h])",
            "legendFormat": "{{severity}} - {{pattern_type}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(radar_errors_total[5m])",
            "legendFormat": "{{error_type}} - {{component}}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "radar_memory_usage_bytes",
            "legendFormat": "{{component}}"
          }
        ],
        "yAxes": [
          {
            "label": "Bytes"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

## Logging Framework

### Structured Logging Configuration

```python
# src/agentic_redteam/monitoring/logging_config.py
"""
Centralized logging configuration with structured logging support.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any
import traceback


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception information
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add security context if available
        if hasattr(record, 'security_context'):
            log_data['security'] = record.security_context
        
        return json.dumps(log_data, ensure_ascii=False)


class SecurityAuditFilter(logging.Filter):
    """Filter for security-related log messages."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter security audit messages."""
        security_keywords = [
            'authentication', 'authorization', 'vulnerability',
            'attack', 'injection', 'bypass', 'exploit'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            '()': StructuredFormatter
        },
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        }
    },
    'filters': {
        'security_audit': {
            '()': SecurityAuditFilter
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'structured',
            'stream': sys.stdout
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'structured',
            'filename': 'logs/radar.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'security_audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'structured',
            'filename': 'logs/security-audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'filters': ['security_audit'],
            'encoding': 'utf8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'structured',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        }
    },
    'loggers': {
        'agentic_redteam': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'agentic_redteam.security': {
            'level': 'INFO',
            'handlers': ['security_audit'],
            'propagate': True
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console', 'error_file']
    }
}


def setup_logging(config: Dict[str, Any] = None):
    """Set up application logging."""
    if config is None:
        config = LOGGING_CONFIG
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs('logs', exist_ok=True)
    
    logging.config.dictConfig(config)


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self):
        self.logger = logging.getLogger('agentic_redteam.security')
    
    def log_scan_started(self, agent_id: str, patterns: list, user: str = None):
        """Log scan initiation."""
        self.logger.info(
            "Security scan started",
            extra={
                'security_context': {
                    'event_type': 'scan_started',
                    'agent_id': agent_id,
                    'patterns': patterns,
                    'user': user,
                    'risk_level': 'low'
                }
            }
        )
    
    def log_vulnerability_found(self, vulnerability: dict, agent_id: str):
        """Log vulnerability discovery."""
        self.logger.warning(
            f"Vulnerability found: {vulnerability.get('name', 'Unknown')}",
            extra={
                'security_context': {
                    'event_type': 'vulnerability_found',
                    'agent_id': agent_id,
                    'vulnerability': vulnerability,
                    'risk_level': vulnerability.get('severity', 'unknown')
                }
            }
        )
    
    def log_attack_attempt(self, attack_type: str, payload: str, agent_id: str):
        """Log attack pattern execution."""
        self.logger.info(
            f"Attack pattern executed: {attack_type}",
            extra={
                'security_context': {
                    'event_type': 'attack_attempt',
                    'attack_type': attack_type,
                    'payload_hash': hash(payload),  # Don't log actual payload
                    'agent_id': agent_id,
                    'risk_level': 'medium'
                }
            }
        )
    
    def log_security_violation(self, violation_type: str, details: dict):
        """Log security policy violation."""
        self.logger.error(
            f"Security violation detected: {violation_type}",
            extra={
                'security_context': {
                    'event_type': 'security_violation',
                    'violation_type': violation_type,
                    'details': details,
                    'risk_level': 'high'
                }
            }
        )


# Global security logger instance
security_logger = SecurityLogger()
```

## Distributed Tracing

### OpenTelemetry Configuration

```python
# src/agentic_redteam/monitoring/tracing.py
"""
Distributed tracing configuration using OpenTelemetry.
"""

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
import functools
import logging

logger = logging.getLogger(__name__)


def setup_tracing(service_name: str = "agentic-redteam-radar", 
                  jaeger_endpoint: str = "http://jaeger:14268/api/traces"):
    """Set up distributed tracing with Jaeger."""
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": "production"
    })
    
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        endpoint=jaeger_endpoint,
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Instrument common libraries
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()
    
    logger.info(f"Tracing initialized for service: {service_name}")


def trace_function(operation_name: str = None):
    """Decorator to trace function execution."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
        
        return wrapper
    return decorator


class TracingContext:
    """Context manager for custom tracing spans."""
    
    def __init__(self, operation_name: str, **attributes):
        self.operation_name = operation_name
        self.attributes = attributes
        self.tracer = trace.get_tracer(__name__)
        self.span = None
    
    def __enter__(self):
        self.span = self.tracer.start_span(self.operation_name)
        
        # Add custom attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.span.set_attribute("error", True)
            self.span.set_attribute("error.type", exc_type.__name__)
            self.span.set_attribute("error.message", str(exc_val))
        
        self.span.end()
```

## Alerting Configuration

### AlertManager Configuration

```yaml
# monitoring/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@agentic-redteam.org'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 5s
      repeat_interval: 5m
    
    - match:
        severity: warning
      receiver: 'warning-alerts'
      repeat_interval: 30m
    
    - match:
        alertname: SecurityViolation
      receiver: 'security-team'
      group_wait: 1s
      repeat_interval: 1m

receivers:
  - name: 'default'
    email_configs:
      - to: 'devops@agentic-redteam.org'
        subject: '[RADAR] Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Labels: {{ range .Labels.SortedPairs }}{{ .Name }}: {{ .Value }}{{ end }}
          {{ end }}

  - name: 'critical-alerts'
    email_configs:
      - to: 'critical-alerts@agentic-redteam.org'
        subject: '[CRITICAL] RADAR Alert: {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#critical-alerts'
        text: 'CRITICAL: {{ .CommonAnnotations.summary }}'

  - name: 'warning-alerts'
    email_configs:
      - to: 'warnings@agentic-redteam.org'
        subject: '[WARNING] RADAR Alert: {{ .GroupLabels.alertname }}'

  - name: 'security-team'
    email_configs:
      - to: 'security@agentic-redteam.org'
        subject: '[SECURITY] RADAR Alert: {{ .GroupLabels.alertname }}'
    pagerduty_configs:
      - routing_key: 'YOUR_PAGERDUTY_ROUTING_KEY'
        description: 'Security alert: {{ .CommonAnnotations.summary }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
```

### Alert Rules

```yaml
# monitoring/prometheus/rules/radar-alerts.yml
groups:
  - name: radar-application
    rules:
      - alert: HighErrorRate
        expr: rate(radar_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: ScanDurationHigh
        expr: histogram_quantile(0.95, rate(radar_scan_duration_seconds_bucket[5m])) > 300
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Scan duration is high"
          description: "95th percentile scan duration is {{ $value }}s"

      - alert: CriticalVulnerabilityFound
        expr: increase(radar_vulnerabilities_found_total{severity="critical"}[1m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Critical vulnerability detected"
          description: "A critical vulnerability has been found"

      - alert: SecurityViolation
        expr: increase(radar_errors_total{error_type="security_violation"}[1m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Security violation detected"
          description: "A security policy violation has occurred"

      - alert: ServiceDown
        expr: up{job="radar-scanner"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Radar Scanner service is down"
          description: "The Radar Scanner service has been down for more than 1 minute"

      - alert: HighMemoryUsage
        expr: radar_memory_usage_bytes > 1000000000  # 1GB
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizeBytes }}"

      - alert: DatabaseConnectionsFull
        expr: radar_database_connections{status="active"} > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly full"
          description: "Active database connections: {{ $value }}"

  - name: radar-infrastructure
    rules:
      - alert: HighCPUUsage
        expr: radar_cpu_usage_percent > 80
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"

      - alert: DiskSpaceLow
        expr: (1 - node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low"
          description: "Disk usage is above 90%"

      - alert: TooManyRestarts
        expr: increase(kube_pod_container_status_restarts_total[1h]) > 5
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Pod restarting frequently"
          description: "Pod {{ $labels.pod }} has restarted {{ $value }} times in the last hour"
```

## Service Level Objectives (SLOs)

### SLI/SLO Configuration

```yaml
# monitoring/slo/radar-slos.yml
slos:
  - name: scan-availability
    description: "Percentage of successful scan requests"
    sli:
      expression: |
        sum(rate(radar_scan_requests_total{status="success"}[5m])) /
        sum(rate(radar_scan_requests_total[5m]))
    objectives:
      - target: 0.999  # 99.9% availability
        window: 30d
      - target: 0.995  # 99.5% availability
        window: 7d

  - name: scan-latency
    description: "95th percentile scan response time"
    sli:
      expression: |
        histogram_quantile(0.95, 
          sum(rate(radar_scan_duration_seconds_bucket[5m])) by (le)
        )
    objectives:
      - target: 30  # 30 seconds
        window: 30d
      - target: 10  # 10 seconds
        window: 7d

  - name: vulnerability-detection-accuracy
    description: "Ratio of confirmed vulnerabilities to total detections"
    sli:
      expression: |
        sum(rate(radar_vulnerabilities_found_total{confirmed="true"}[5m])) /
        sum(rate(radar_vulnerabilities_found_total[5m]))
    objectives:
      - target: 0.90  # 90% accuracy
        window: 30d

error_budgets:
  - slo: scan-availability
    budget_percent: 0.1  # 0.1% error budget
    alerting:
      burn_rate_threshold: 2.0
      window: 1h

  - slo: scan-latency
    budget_percent: 5.0  # 5% can exceed target
    alerting:
      burn_rate_threshold: 3.0
      window: 30m
```

## Health Checks

### Application Health Endpoints

```python
# src/agentic_redteam/monitoring/health.py
"""
Health check endpoints for monitoring and load balancing.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import psutil
import time
from datetime import datetime

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float


class DetailedHealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    checks: Dict[str, Any]
    system: Dict[str, Any]


class HealthChecker:
    """Centralized health checking functionality."""
    
    def __init__(self):
        self.start_time = time.time()
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # Simulate database check
            await asyncio.sleep(0.01)  # Simulate DB query
            return {
                "status": "healthy",
                "response_time_ms": 10,
                "connections": 5
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            # Simulate Redis check
            await asyncio.sleep(0.005)  # Simulate Redis ping
            return {
                "status": "healthy",
                "response_time_ms": 5
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API dependencies."""
        apis = {
            "openai": {"status": "unknown"},
            "anthropic": {"status": "unknown"}
        }
        
        # In real implementation, would check actual API connectivity
        for api_name in apis:
            try:
                # Simulate API check
                await asyncio.sleep(0.02)
                apis[api_name] = {
                    "status": "healthy",
                    "response_time_ms": 20
                }
            except Exception as e:
                apis[api_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return apis
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "used_percent": psutil.virtual_memory().percent,
                "available_mb": psutil.virtual_memory().available // (1024 * 1024)
            },
            "disk": {
                "used_percent": psutil.disk_usage('/').percent,
                "free_gb": psutil.disk_usage('/').free // (1024 * 1024 * 1024)
            }
        }
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time


health_checker = HealthChecker()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint."""
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="0.1.0",
        uptime_seconds=health_checker.get_uptime()
    )


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """Detailed health check with dependency status."""
    
    # Run all health checks concurrently
    db_check, redis_check, api_checks = await asyncio.gather(
        health_checker.check_database(),
        health_checker.check_redis(),
        health_checker.check_external_apis()
    )
    
    # Determine overall status
    checks = {
        "database": db_check,
        "redis": redis_check,
        "external_apis": api_checks
    }
    
    # Overall status is unhealthy if any critical check fails
    overall_status = "healthy"
    if (db_check.get("status") != "healthy" or 
        redis_check.get("status") != "healthy"):
        overall_status = "unhealthy"
    
    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="0.1.0",
        uptime_seconds=health_checker.get_uptime(),
        checks=checks,
        system=health_checker.get_system_metrics()
    )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    # Check if application is ready to serve traffic
    db_check = await health_checker.check_database()
    
    if db_check.get("status") != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready - database unavailable"
        )
    
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple check that the application is running
    return {"status": "alive"}
```

This comprehensive observability framework provides enterprise-grade monitoring, logging, and alerting capabilities for the Agentic RedTeam Radar project, ensuring high visibility into system performance and security events.