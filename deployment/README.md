# Agentic RedTeam Radar - Production Deployment Guide

This directory contains production-ready deployment configurations for the Agentic RedTeam Radar security testing framework.

## 🚀 Quick Start

### Docker Compose Production Setup

1. **Prepare environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy the stack:**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Verify deployment:**
   ```bash
   curl -k https://localhost/health
   ```

### Kubernetes Production Setup

1. **Create namespace and secrets:**
   ```bash
   kubectl apply -f kubernetes/radar-production.yaml
   ```

2. **Update secrets:**
   ```bash
   kubectl create secret generic radar-secrets \
     --from-literal=openai-api-key=your-key \
     --from-literal=anthropic-api-key=your-key \
     -n agentic-redteam
   ```

3. **Deploy application:**
   ```bash
   kubectl apply -f kubernetes/radar-production.yaml
   ```

## 📋 Architecture Overview

### Components

- **Agentic RedTeam Radar**: Main security testing application (2 replicas)
- **Nginx**: Load balancer and SSL termination
- **PostgreSQL**: Primary database with persistence
- **Redis**: Caching layer for performance
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization and dashboards
- **Fluentd**: Log aggregation and forwarding

### Network Architecture

```
Internet → Nginx (SSL) → Radar App (2x) → PostgreSQL + Redis
                    ↓
              Monitoring Stack (Prometheus/Grafana)
```

## 🔒 Security Features

### Container Security
- **Non-root users**: All containers run as non-privileged users
- **Read-only filesystems**: Containers use read-only root filesystems
- **No new privileges**: Prevents privilege escalation
- **Minimal attack surface**: Alpine/slim base images
- **Security scanning**: Trivy integration for vulnerability scanning

### Network Security
- **Network isolation**: Dedicated Docker network with firewall rules
- **SSL/TLS encryption**: All external traffic encrypted
- **Rate limiting**: API and scan endpoint protection
- **Internal authentication**: Service-to-service auth

### Application Security
- **Input validation**: Comprehensive sanitization
- **SQL injection protection**: Parameterized queries
- **XSS protection**: Security headers and CSP
- **CSRF protection**: Token-based protection
- **Audit logging**: Complete activity tracking

## 📊 Monitoring & Observability

### Metrics Available
- **Application performance**: Response times, throughput, errors
- **Security scan results**: Vulnerability counts, patterns executed
- **Infrastructure health**: CPU, memory, disk, network
- **Business metrics**: Scans per hour, agent coverage

### Dashboards
- **Executive Dashboard**: High-level security posture
- **Operational Dashboard**: System health and performance
- **Security Dashboard**: Vulnerability trends and alerts
- **Infrastructure Dashboard**: Resource utilization

### Alerting Rules
- High error rates (>5%)
- Long response times (>5s p95)
- Resource exhaustion (>80% CPU/Memory)
- Failed security scans
- Anomalous vulnerability patterns

## 🔧 Configuration

### Environment Variables

#### Application Configuration
```bash
RADAR_LOG_LEVEL=INFO
RADAR_MAX_CONCURRENCY=10
RADAR_MAX_AGENT_CONCURRENCY=5
RADAR_TIMEOUT=30
RADAR_DATABASE_URL=postgresql://user:pass@host:5432/db
RADAR_CACHE_BACKEND=redis
RADAR_CACHE_URL=redis://host:6379/0
```

#### Security Configuration
```bash
RADAR_ENABLE_INPUT_SANITIZATION=true
RADAR_MAX_PAYLOAD_SIZE=10000
RADAR_AUDIT_LOGGING=true
```

#### Performance Configuration
```bash
RADAR_RATE_LIMIT_REQUESTS_PER_MINUTE=60
RADAR_RATE_LIMIT_BURST=10
RADAR_CACHE_TTL=3600
```

### Resource Requirements

#### Minimum (Development)
- **CPU**: 2 vCPUs
- **Memory**: 4 GB RAM
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps

#### Recommended (Production)
- **CPU**: 8 vCPUs
- **Memory**: 16 GB RAM
- **Storage**: 100 GB SSD
- **Network**: 1 Gbps

#### Enterprise (High-Scale)
- **CPU**: 16+ vCPUs
- **Memory**: 32+ GB RAM
- **Storage**: 500+ GB SSD
- **Network**: 10+ Gbps

## 🚀 Scaling

### Horizontal Scaling
```bash
# Docker Compose
docker-compose -f docker-compose.production.yml up -d --scale radar-app-1=4

# Kubernetes
kubectl scale deployment agentic-redteam-radar --replicas=10 -n agentic-redteam
```

### Performance Tuning
1. **Database optimization**: Connection pooling, query optimization
2. **Cache sizing**: Redis memory allocation based on workload
3. **Worker processes**: Match CPU cores for optimal performance
4. **Load balancing**: Tune Nginx upstream configuration

## 🔍 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs radar-app-1

# Verify configuration
docker-compose -f docker-compose.production.yml config
```

#### High Memory Usage
```bash
# Monitor resource usage
docker stats

# Check for memory leaks
kubectl top pods -n agentic-redteam
```

#### Database Connection Issues
```bash
# Test database connectivity
docker-compose -f docker-compose.production.yml exec postgres psql -U radar -d radar_db -c "SELECT 1;"

# Check connection pool
curl -s http://localhost:9090/metrics | grep db_connections
```

### Performance Issues
```bash
# Check response times
curl -w "@curl-format.txt" -s -o /dev/null https://localhost/health

# Monitor queue depths
docker-compose -f docker-compose.production.yml exec redis redis-cli info stats
```

## 📱 Health Checks

### Application Health
- **Endpoint**: `GET /health`
- **Expected**: HTTP 200 with `{"status": "healthy"}`
- **Timeout**: 10 seconds

### Readiness Check
- **Endpoint**: `GET /ready`
- **Expected**: HTTP 200 with service dependencies
- **Timeout**: 5 seconds

### Liveness Check
- **Internal**: Application heartbeat every 30 seconds
- **External**: Load balancer health check every 10 seconds

## 🔄 Backup & Recovery

### Database Backup
```bash
# Automated daily backup
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U radar radar_db > backup-$(date +%Y%m%d).sql

# Restore from backup
docker-compose -f docker-compose.production.yml exec -T postgres psql -U radar radar_db < backup-20240101.sql
```

### Application Data
```bash
# Backup reports and logs
docker run --rm -v radar_reports:/data -v $(pwd):/backup alpine tar czf /backup/reports-backup.tar.gz /data

# Restore reports
docker run --rm -v radar_reports:/data -v $(pwd):/backup alpine tar xzf /backup/reports-backup.tar.gz -C /
```

## 🔧 Maintenance

### Updates
```bash
# Update application image
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d --no-deps radar-app-1 radar-app-2

# Update system packages
docker-compose -f docker-compose.production.yml build --no-cache
```

### Log Rotation
```bash
# Rotate application logs
docker-compose -f docker-compose.production.yml exec fluentd logrotate /etc/logrotate.conf

# Clean old Docker logs
docker system prune -f --volumes --filter "until=720h"
```

## 📞 Support

### Monitoring Access
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/password from .env)
- **Application Logs**: `docker-compose logs -f`

### Emergency Contacts
- **Infrastructure**: ops-team@company.com
- **Security**: security-team@company.com
- **Development**: dev-team@company.com

### Documentation Links
- [Application Architecture](../docs/ARCHITECTURE.md)
- [Security Guide](../SECURITY.md)
- [Performance Tuning](../docs/performance/benchmarking-and-profiling.md)
- [Monitoring Setup](../docs/monitoring/observability-framework.md)