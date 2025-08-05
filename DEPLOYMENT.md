# 🚀 Agentic RedTeam Radar - Production Deployment Guide

## Overview

This guide covers enterprise-grade deployment of Agentic RedTeam Radar with advanced features including performance optimization, monitoring, auto-scaling, and global compliance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Load      │    │    API      │    │  Scanner    │     │
│  │  Balancer   │───▶│  Gateway    │───▶│   Engine    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                           │                     │            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Monitoring  │    │    Cache    │    │  Database   │     │
│  │   Stack     │    │   (Redis)   │    │(PostgreSQL)│     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Basic Installation

```bash
# Clone repository
git clone https://github.com/your-org/agentic-redteam-radar
cd agentic-redteam-radar

# Install dependencies
pip install -e .

# Install optional dependencies for production
pip install redis psycopg2-binary opentelemetry-api opentelemetry-sdk

# Run basic example
python examples/basic_example.py
```

### 2. Production Dependencies

```bash
# Core dependencies
pip install agentic-redteam-radar[production]

# Or install manually:
pip install \
    redis>=4.0.0 \
    psycopg2-binary>=2.9.0 \
    opentelemetry-api>=1.20.0 \
    opentelemetry-sdk>=1.20.0 \
    opentelemetry-exporter-otlp>=1.20.0 \
    prometheus-client>=0.16.0 \
    uvicorn[standard]>=0.24.0 \
    psutil>=5.9.0
```

## Environment Configuration

### 1. Environment Variables

Create a `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/radar_db

# Cache Configuration  
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RATE_LIMIT=100

# Monitoring Configuration
OTEL_ENDPOINT=http://jaeger:14250
PROMETHEUS_PORT=9090
ENABLE_METRICS=true

# Security Configuration
JWT_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://your-frontend.com,https://admin.your-domain.com
TRUSTED_HOSTS=your-domain.com,api.your-domain.com

# Performance Configuration
MAX_CONCURRENCY=8
CACHE_TTL=3600
OPTIMIZATION_ENABLED=true

# Global Configuration
DEFAULT_TIMEZONE=UTC
ENABLE_I18N=true
LOG_LEVEL=INFO
```

### 2. Configuration Files

Create `config/production.yaml`:

```yaml
scanner:
  max_concurrency: 8
  max_payloads_per_pattern: 20
  timeout: 120
  retry_attempts: 3
  enabled_patterns:
    - prompt_injection
    - info_disclosure  
    - policy_bypass
    - chain_of_thought
  
cache:
  backend: redis
  url: ${REDIS_URL}
  ttl: 3600
  max_size: 100000

database:
  url: ${DATABASE_URL}
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30

monitoring:
  enabled: true
  otel_endpoint: ${OTEL_ENDPOINT}
  metrics_interval: 60
  health_check_interval: 30
  
  thresholds:
    max_scan_duration: 300
    min_success_rate: 0.95
    max_memory_usage: 0.85
    max_cpu_usage: 0.90

security:
  sanitize_output: true
  rate_limiting: true
  authentication: true
  audit_logging: true
  
performance:
  optimization_enabled: true
  adaptive_scaling: true
  memory_optimization: true
  connection_pooling: true
```

## Deployment Options

### 1. Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/radar
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: radar
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  db_data:
  redis_data:
  grafana_data:
```

Build and deploy:

```bash
docker-compose up -d
```

### 2. Kubernetes Deployment

Create Kubernetes manifests:

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agentic-redteam

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: radar-config
  namespace: agentic-redteam
data:
  production.yaml: |
    # Your production config here

---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: radar-api
  namespace: agentic-redteam
spec:
  replicas: 3
  selector:
    matchLabels:
      app: radar-api
  template:
    metadata:
      labels:
        app: radar-api
    spec:
      containers:
      - name: api
        image: your-registry/agentic-redteam-radar:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: radar-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: radar-api-service
  namespace: agentic-redteam
spec:
  selector:
    app: radar-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: radar-api-hpa
  namespace: agentic-redteam
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: radar-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Deploy:

```bash
kubectl apply -f k8s/
```

### 3. Cloud Deployments

#### AWS ECS/Fargate

```json
{
  "family": "agentic-redteam-radar",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "radar-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/agentic-redteam-radar:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/radar"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/agentic-redteam-radar",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Google Cloud Run

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: agentic-redteam-radar
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 80
      containers:
      - image: gcr.io/project-id/agentic-redteam-radar
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://user:pass@/radar?host=/cloudsql/project:region:instance"
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
```

## Performance Optimization

### 1. Configuration Tuning

```python
# High-performance configuration
config = RadarConfig()
config.max_concurrency = 16  # Adjust based on resources
config.max_payloads_per_pattern = 25
config.timeout = 60
config.retry_attempts = 2
config.cache_results = True
config.cache_ttl = 7200  # 2 hours

# Enable all optimization strategies
config.enable_batch_processing = True
config.enable_connection_pooling = True
config.enable_memory_optimization = True
config.enable_adaptive_scheduling = True
```

### 2. Database Optimization

```sql
-- PostgreSQL optimizations
-- Create indexes for common queries
CREATE INDEX idx_vulnerabilities_severity ON vulnerabilities(severity);
CREATE INDEX idx_scan_sessions_created_at ON scan_sessions(created_at);
CREATE INDEX idx_scan_sessions_status ON scan_sessions(status);

-- Partition large tables
CREATE TABLE scan_sessions_2024 PARTITION OF scan_sessions
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Configure connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

### 3. Redis Configuration

```conf
# redis.conf optimizations
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Network optimizations
tcp-keepalive 300
timeout 0
tcp-backlog 511
```

## Monitoring & Observability

### 1. Metrics Collection

```python
from agentic_redteam.monitoring.telemetry import get_metrics_collector

# Initialize metrics
metrics = get_metrics_collector()

# Add custom metric handlers
def prometheus_handler(metric_points):
    for point in metric_points:
        prometheus_client.Counter(point.name).inc(point.value)

metrics.add_handler(prometheus_handler)
```

### 2. Health Checks

The API provides several health check endpoints:

- `/health` - Basic health status
- `/health/detailed` - Comprehensive system status
- `/metrics` - Prometheus metrics endpoint
- `/status` - Application status and version

### 3. Logging Configuration

```python
# Configure structured logging
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'radar.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        'agentic_redteam': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## Security Configuration

### 1. Authentication & Authorization

```python
# Configure JWT authentication
from agentic_redteam.api.middleware import JWTAuthMiddleware

app.add_middleware(
    JWTAuthMiddleware,
    secret_key=os.getenv("JWT_SECRET_KEY"),
    algorithm="HS256",
    excluded_paths=["/health", "/metrics"]
)
```

### 2. Network Security

```nginx
# nginx.conf security headers
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Rate limiting
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://radar-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Database Security

```yaml
# PostgreSQL security configuration
ssl: true
ssl_cert_file: 'server.crt'
ssl_key_file: 'server.key'
ssl_ca_file: 'ca.crt'

# Connection encryption
sslmode: require
sslcert: client.crt
sslkey: client.key
sslrootcert: ca.crt
```

## Scaling & Load Balancing

### 1. Horizontal Scaling

```python
# Configure for horizontal scaling
from agentic_redteam.performance.optimizer import AdaptiveResourceManager

# Initialize with cluster-aware settings
resource_manager = AdaptiveResourceManager(
    max_workers=32,
    enable_cluster_coordination=True,
    cluster_nodes=['node1:8000', 'node2:8000', 'node3:8000']
)
```

### 2. Load Balancer Configuration

```nginx
upstream radar_backend {
    least_conn;
    server radar-api-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server radar-api-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server radar-api-3:8000 weight=1 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name api.your-domain.com;
    
    location / {
        proxy_pass http://radar_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 3. Auto-scaling Policies

```yaml
# Kubernetes HPA with custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: radar-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: radar-api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: scan_queue_length
      target:
        type: AverageValue
        averageValue: "5"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Maintenance & Operations

### 1. Backup Strategy

```bash
#!/bin/bash
# backup.sh - Database backup script

# PostgreSQL backup
pg_dump $DATABASE_URL | gzip > backups/radar_$(date +%Y%m%d_%H%M%S).sql.gz

# Redis backup
redis-cli --rdb backups/redis_$(date +%Y%m%d_%H%M%S).rdb

# Clean old backups (keep 30 days)
find backups/ -name "*.gz" -mtime +30 -delete
find backups/ -name "*.rdb" -mtime +30 -delete
```

### 2. Log Rotation

```conf
# /etc/logrotate.d/radar
/var/log/radar/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 radar radar
    postrotate
        systemctl reload radar-api
    endscript
}
```

### 3. Monitoring Alerts

```yaml
# prometheus/alerts.yml
groups:
- name: radar.rules
  rules:
  - alert: HighErrorRate
    expr: rate(radar_requests_failed_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: High error rate detected
      
  - alert: ScanDurationHigh
    expr: radar_scan_duration_seconds > 300
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: Scan duration exceeding threshold
      
  - alert: MemoryUsageHigh
    expr: radar_memory_usage_percent > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High memory usage detected
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Enable memory optimization: `config.enable_memory_optimization = True`
   - Reduce batch sizes: `config.max_payloads_per_pattern = 10`
   - Increase memory limits in container/pod specs

2. **Slow Scan Performance**
   - Increase concurrency: `config.max_concurrency = 16`
   - Enable caching: `config.cache_results = True`
   - Check database query performance

3. **Connection Pool Exhaustion**
   - Increase pool size: `database.pool_size = 50`
   - Reduce connection timeout: `database.pool_timeout = 10`
   - Monitor connection usage

4. **Cache Issues**
   - Check Redis connectivity and memory
   - Verify cache configuration
   - Monitor cache hit/miss ratios

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('agentic_redteam').setLevel(logging.DEBUG)

# Enable performance profiling
config.enable_profiling = True
config.profile_output_dir = '/tmp/profiles'
```

## Support

- **Documentation**: [https://docs.your-domain.com/radar](https://docs.your-domain.com/radar)
- **Issues**: [https://github.com/your-org/agentic-redteam-radar/issues](https://github.com/your-org/agentic-redteam-radar/issues)
- **Support**: [support@your-domain.com](mailto:support@your-domain.com)
- **Community**: [https://discord.gg/your-discord](https://discord.gg/your-discord)

---

*This deployment guide covers enterprise-grade production deployment. For development and testing, see the [Quick Start Guide](README.md#quick-start).*