# Deployment Guide

## Overview

This guide covers deployment strategies for Agentic RedTeam Radar across different environments, from local development to production deployments.

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/terragonlabs/agentic-redteam-radar.git
cd agentic-redteam-radar

# Setup development environment
make dev-setup

# Start services
make up-dev
```

### Production Deployment

```bash
# Build and deploy
make build
make docker-build
make deploy-prod
```

## Deployment Options

### 1. Docker Compose (Recommended for Development)

#### Basic Setup

```bash
# Start core services
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start with logging
docker-compose --profile logging up -d
```

#### Environment Configuration

Create `.env` file:

```env
# Application
RADAR_LOG_LEVEL=INFO
RADAR_OUTPUT_DIR=/app/reports

# Database
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password

# Monitoring
GRAFANA_PASSWORD=admin_password

# API Keys (for testing)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 2. Kubernetes Deployment

#### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.0+

#### Deploy with Helm

```bash
# Add Helm repository
helm repo add radar-charts https://charts.terragonlabs.com
helm repo update

# Install
helm install agentic-radar radar-charts/agentic-redteam-radar \
  --set image.tag=latest \
  --set database.password=secure_password \
  --set monitoring.enabled=true
```

#### Custom Values

Create `values.yaml`:

```yaml
image:
  repository: agentic-redteam-radar
  tag: "0.1.0"
  pullPolicy: IfNotPresent

replicaCount: 3

service:
  type: LoadBalancer
  port: 8000

database:
  enabled: true
  password: "secure_password"
  persistence:
    size: 10Gi

redis:
  enabled: true
  auth:
    password: "redis_password"

monitoring:
  enabled: true
  prometheus:
    persistence:
      size: 5Gi
  grafana:
    adminPassword: "grafana_password"

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

Deploy:

```bash
helm install agentic-radar radar-charts/agentic-redteam-radar -f values.yaml
```

### 3. Cloud Deployments

#### AWS ECS

```json
{
  "family": "agentic-redteam-radar",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "radar",
      "image": "agentic-redteam-radar:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "RADAR_LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:radar/openai-key"
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
      - image: gcr.io/PROJECT_ID/agentic-redteam-radar:latest
        ports:
        - containerPort: 8000
        env:
        - name: RADAR_LOG_LEVEL
          value: INFO
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: radar-secrets
              key: openai-api-key
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
```

Deploy:

```bash
gcloud run deploy agentic-redteam-radar \
  --image gcr.io/PROJECT_ID/agentic-redteam-radar:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```yaml
apiVersion: 2021-07-01
location: eastus
name: agentic-redteam-radar
properties:
  containers:
  - name: radar
    properties:
      image: agentic-redteam-radar:latest
      ports:
      - port: 8000
        protocol: TCP
      environmentVariables:
      - name: RADAR_LOG_LEVEL
        value: INFO
      - name: OPENAI_API_KEY
        secureValue: your_openai_key
      resources:
        requests:
          cpu: 0.5
          memoryInGB: 1
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 8000
```

## Configuration Management

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RADAR_LOG_LEVEL` | No | `INFO` | Logging level |
| `RADAR_OUTPUT_DIR` | No | `/app/reports` | Report output directory |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key |
| `DATABASE_URL` | No | - | PostgreSQL connection string |
| `REDIS_URL` | No | - | Redis connection string |

### Configuration Files

#### radar-config.yaml

```yaml
scanner:
  concurrency: 5
  timeout: 30
  retry_attempts: 3

patterns:
  prompt_injection:
    enabled: true
    severity_threshold: medium
  
  info_disclosure:
    enabled: true
    max_attempts: 10

reporting:
  format: html
  include_payloads: false
  output_dir: ./reports

database:
  host: localhost
  port: 5432
  name: radar
  user: radar
  password: ${DATABASE_PASSWORD}

redis:
  host: localhost
  port: 6379
  password: ${REDIS_PASSWORD}

monitoring:
  enabled: true
  metrics_port: 9090
  health_check_port: 8080
```

## Security Considerations

### 1. Secret Management

#### Kubernetes Secrets

```bash
# Create secret for API keys
kubectl create secret generic radar-secrets \
  --from-literal=openai-api-key=your_key \
  --from-literal=anthropic-api-key=your_key

# Create secret for database
kubectl create secret generic radar-db-secret \
  --from-literal=password=your_db_password
```

#### Docker Secrets

```yaml
version: '3.8'
services:
  radar:
    image: agentic-redteam-radar:latest
    secrets:
      - openai_api_key
      - db_password
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  openai_api_key:
    external: true
  db_password:
    external: true
```

### 2. Network Security

#### Container Network

```yaml
networks:
  radar-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### Kubernetes Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: radar-network-policy
spec:
  podSelector:
    matchLabels:
      app: agentic-redteam-radar
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

### 3. RBAC Configuration

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: radar-role
rules:
- apiGroups: [""]
  resources: ["pods", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: radar-rolebinding
subjects:
- kind: ServiceAccount
  name: radar-serviceaccount
roleRef:
  kind: Role
  name: radar-role
  apiGroup: rbac.authorization.k8s.io
```

## Monitoring and Observability

### 1. Health Checks

#### HTTP Health Check

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 2. Logging Configuration

#### Structured Logging

```yaml
logging:
  level: INFO
  format: json
  output: stdout
  fields:
    service: agentic-redteam-radar
    version: 0.1.0
```

#### Log Aggregation

```yaml
# Fluentd configuration
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<match **>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name radar-logs
  type_name _doc
</match>
```

### 3. Metrics Collection

#### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'radar'
    static_configs:
      - targets: ['radar:9090']
    metrics_path: /metrics
    scrape_interval: 5s
```

## Performance Optimization

### 1. Resource Allocation

#### Production Settings

```yaml
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi
```

#### JVM/Python Settings

```env
# Python optimization
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Resource limits
RADAR_MAX_WORKERS=4
RADAR_MEMORY_LIMIT=1G
```

### 2. Database Optimization

#### PostgreSQL Configuration

```sql
-- Connection settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB

-- Performance settings
random_page_cost = 1.1
seq_page_cost = 1.0
default_statistics_target = 100
```

#### Connection Pooling

```yaml
database:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
```

### 3. Caching Strategy

#### Redis Configuration

```yaml
redis:
  maxmemory: 256mb
  maxmemory-policy: allkeys-lru
  timeout: 300
```

## Backup and Recovery

### 1. Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="radar"

# Create backup
pg_dump -h postgres -U radar $DB_NAME | gzip > $BACKUP_DIR/radar_$DATE.sql.gz

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "radar_*.sql.gz" -mtime +30 -delete
```

### 2. Volume Backup

```yaml
# Kubernetes CronJob for volume backup
apiVersion: batch/v1
kind: CronJob
metadata:
  name: radar-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres -U radar radar | gzip > /backup/radar_$(date +%Y%m%d).sql.gz
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: Never
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Scaling Strategies

### 1. Horizontal Scaling

#### Kubernetes HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: radar-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentic-redteam-radar
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

### 2. Vertical Scaling

#### VPA Configuration

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: radar-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentic-redteam-radar
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: radar
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

## Troubleshooting

### Common Issues

1. **API Rate Limiting**
   ```yaml
   # Increase timeout and retry settings
   scanner:
     timeout: 60
     retry_attempts: 5
     backoff_factor: 2
   ```

2. **Memory Issues**
   ```bash
   # Check memory usage
   kubectl top pods
   
   # Increase memory limits
   resources:
     limits:
       memory: 2Gi
   ```

3. **Database Connection Issues**
   ```bash
   # Check database connectivity
   kubectl exec -it radar-pod -- psql -h postgres -U radar -d radar -c "SELECT 1;"
   ```

### Debugging Commands

```bash
# View logs
kubectl logs -f deployment/agentic-redteam-radar

# Access container shell
kubectl exec -it deployment/agentic-redteam-radar -- bash

# Port forward for local access
kubectl port-forward service/agentic-redteam-radar 8000:8000

# Check resource usage
kubectl top pods -l app=agentic-redteam-radar
```

---

For more specific deployment scenarios or troubleshooting, please refer to the individual platform documentation or open an issue on GitHub.