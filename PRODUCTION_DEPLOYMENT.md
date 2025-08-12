# 🚀 Agentic RedTeam Radar - Production Deployment Guide

## Overview

This document provides comprehensive guidance for deploying Agentic RedTeam Radar in production environments with enterprise-grade security, scalability, and reliability.

## 🏗️ Architecture Overview

### Generation 3: Production-Ready Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│  Scanner Nodes  │────│   Data Layer    │
│     (Nginx)     │    │  (Auto-Scaling) │    │ (Redis/Postgres)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│   Monitoring    │──────────────┘
                        │ (Prometheus)    │
                        └─────────────────┘
```

### Key Features

✅ **Generation 1 (Simple)**: Core functionality working
✅ **Generation 2 (Robust)**: Enhanced error handling, validation, monitoring
✅ **Generation 3 (Optimized)**: Auto-scaling, performance optimization, production deployment

## 📋 Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Kubernetes 1.24+ (for K8s deployment)
- 4GB+ RAM available
- 20GB+ disk space
- SSL certificates (for HTTPS)

## 🐳 Docker Deployment

### Quick Start

```bash
# Clone and navigate to deployment directory
cd deployment/production

# Start all services
docker-compose up -d

# Check health
curl http://localhost/health
```

### Configuration

1. **Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **SSL Certificates**:
   ```bash
   mkdir ssl
   # Add your cert.pem and key.pem files
   ```

3. **Custom Configuration**:
   ```bash
   # Edit docker-compose.yml for your requirements
   # Adjust resource limits, replica counts, etc.
   ```

### Scaling

```bash
# Scale scanner instances
docker-compose up -d --scale agentic-redteam-scanner=5

# Check status
docker-compose ps
```

## ☸️ Kubernetes Deployment

### Setup

```bash
# Apply the deployment
kubectl apply -f kubernetes.yml

# Check status
kubectl get pods -n agentic-redteam

# Watch auto-scaling
kubectl get hpa -n agentic-redteam -w
```

### Configuration

1. **Update Secrets**:
   ```bash
   # Base64 encode your values
   echo -n "your-db-password" | base64
   
   # Update kubernetes.yml with encoded values
   ```

2. **Configure Ingress**:
   ```yaml
   # Update ingress host in kubernetes.yml
   - host: your-domain.com
   ```

3. **Resource Limits**:
   ```yaml
   # Adjust based on your cluster capacity
   resources:
     limits:
       memory: "4Gi"
       cpu: "2000m"
   ```

## 🔧 Configuration Reference

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RADAR_MAX_CONCURRENCY` | 10 | Maximum concurrent patterns |
| `RADAR_MAX_AGENT_CONCURRENCY` | 5 | Maximum concurrent agents |
| `RADAR_TIMEOUT` | 60 | Default timeout (seconds) |
| `RADAR_LOG_LEVEL` | INFO | Logging level |
| `RADAR_DATABASE_URL` | sqlite:// | Database connection |
| `RADAR_CACHE_BACKEND` | memory | Cache backend (memory/redis) |

### Performance Tuning

```yaml
# High-performance configuration
environment:
  - RADAR_MAX_CONCURRENCY=20
  - RADAR_MAX_AGENT_CONCURRENCY=10
  - RADAR_TIMEOUT=120
  - RADAR_CACHE_BACKEND=redis
  - RADAR_OPTIMIZATION_ENABLED=true
```

### Security Configuration

```yaml
# Security-focused settings
environment:
  - RADAR_SECURITY_INPUT_SANITIZATION=true
  - RADAR_SECURITY_MAX_PAYLOAD_SIZE=10000
  - RADAR_SECURITY_AUDIT_LOGGING=true
  - RADAR_RATE_LIMIT_ENABLED=true
```

## 📊 Monitoring & Observability

### Metrics

Access Prometheus metrics at:
- http://localhost:9090 (Prometheus)
- http://localhost:3000 (Grafana)

### Key Metrics to Monitor

```promql
# Scanner performance
rate(radar_scans_total[5m])
histogram_quantile(0.95, rate(radar_scan_duration_seconds_bucket[5m]))

# Resource utilization
rate(radar_cpu_usage_percent[5m])
radar_memory_usage_bytes

# Error rates
rate(radar_errors_total[5m])
radar_circuit_breaker_open_total
```

### Alerts

```yaml
# Sample Prometheus alert rules
groups:
- name: radar-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(radar_errors_total[5m]) > 0.1
    for: 2m
    annotations:
      summary: "High error rate detected"
      
  - alert: ScannerDown
    expr: up{job="radar-scanner"} == 0
    for: 1m
    annotations:
      summary: "Scanner instance is down"
```

### Logging

Logs are collected via Fluentd and can be shipped to:
- Elasticsearch
- CloudWatch
- Splunk
- Other log aggregation systems

## 🔒 Security Considerations

### Network Security

```yaml
# Network policies (Kubernetes)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: radar-security
spec:
  podSelector:
    matchLabels:
      app: agentic-redteam-scanner
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: allowed-namespace
```

### RBAC

```yaml
# Service account with minimal permissions
apiVersion: v1
kind: ServiceAccount
metadata:
  name: radar-service-account
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: radar-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
```

### Secrets Management

```bash
# Use external secret management
kubectl create secret generic radar-secrets \
  --from-literal=database-password="$(vault kv get -field=password secret/radar/db)"
```

## 🚀 Performance Optimization

### Auto-Scaling Configuration

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: radar-hpa
spec:
  minReplicas: 3
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
```

### Resource Optimization

```yaml
# Optimized resource allocation
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Cache Configuration

```yaml
# Redis cache optimization
command: 
  - redis-server
  - --maxmemory 2gb
  - --maxmemory-policy allkeys-lru
  - --save 900 1
  - --appendonly yes
```

## 🔄 Backup & Recovery

### Database Backup

```bash
# Automated PostgreSQL backup
kubectl create cronjob postgres-backup \
  --image=postgres:15-alpine \
  --schedule="0 2 * * *" \
  -- pg_dump -h postgres -U radar radar_db > /backup/$(date +%Y%m%d).sql
```

### Volume Snapshots

```yaml
# Kubernetes volume snapshots
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: radar-data-snapshot
spec:
  source:
    persistentVolumeClaimName: postgres-pvc
```

## 📈 Capacity Planning

### Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Scanner (min) | 1 core | 2GB | 1GB |
| Scanner (prod) | 2 cores | 4GB | 5GB |
| PostgreSQL | 1 core | 2GB | 20GB |
| Redis | 0.5 core | 1GB | 10GB |
| Nginx | 0.2 core | 256MB | 1GB |

### Scaling Guidelines

- **Low volume** (< 100 scans/day): 1-2 scanner instances
- **Medium volume** (100-1000 scans/day): 3-5 scanner instances  
- **High volume** (1000+ scans/day): 5-20 scanner instances with auto-scaling

## 🛠️ Troubleshooting

### Common Issues

1. **High Memory Usage**:
   ```bash
   # Check memory consumption
   kubectl top pods -n agentic-redteam
   
   # Tune JVM if needed
   environment:
     - JAVA_OPTS="-Xmx2g -XX:+UseG1GC"
   ```

2. **Slow Scan Performance**:
   ```bash
   # Check resource limits
   kubectl describe pod scanner-pod
   
   # Increase concurrency
   environment:
     - RADAR_MAX_CONCURRENCY=15
   ```

3. **Database Connection Issues**:
   ```bash
   # Check database connectivity
   kubectl exec -it scanner-pod -- pg_isready -h postgres
   
   # Verify connection string
   kubectl logs scanner-pod | grep database
   ```

### Health Checks

```bash
# Manual health check
curl -f http://localhost:8080/health

# Kubernetes health check
kubectl get pods -n agentic-redteam
kubectl describe pod scanner-pod
```

### Log Analysis

```bash
# View scanner logs
kubectl logs -f deployment/agentic-redteam-scanner

# Search for errors
kubectl logs deployment/agentic-redteam-scanner | grep ERROR

# Export logs for analysis
kubectl logs deployment/agentic-redteam-scanner --since=1h > scanner-logs.txt
```

## 🔧 Maintenance

### Regular Tasks

1. **Update Images**:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

2. **Database Maintenance**:
   ```sql
   -- PostgreSQL maintenance
   VACUUM ANALYZE;
   REINDEX DATABASE radar_db;
   ```

3. **Cache Cleanup**:
   ```bash
   # Redis cache cleanup
   kubectl exec redis-pod -- redis-cli FLUSHDB
   ```

### Security Updates

```bash
# Update base images
docker build --pull --no-cache -t agentic-redteam:latest .

# Apply security patches
kubectl set image deployment/agentic-redteam-scanner scanner=agentic-redteam:latest
```

## 📞 Support

For production support and enterprise features:

- 📧 Email: support@terragonlabs.com
- 📖 Documentation: [Advanced Configuration Guide]
- 🐛 Issues: [GitHub Issues](https://github.com/terragonlabs/agentic-redteam/issues)
- 💬 Community: [Discord Server]

## ⚖️ License & Compliance

This deployment guide is provided for defensive security testing purposes. Ensure compliance with:

- Your organization's security policies
- Applicable data protection regulations (GDPR, CCPA, etc.)
- Industry-specific compliance requirements (SOX, HIPAA, etc.)

**Note**: This framework is designed for authorized security testing only. Users are responsible for ensuring appropriate authorization before testing any AI agents or systems.