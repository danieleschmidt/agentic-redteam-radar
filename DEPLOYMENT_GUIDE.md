# 🚀 Deployment Guide - Agentic RedTeam Radar

**Production Deployment Guide**  
**Version**: 1.0.0  
**Last Updated**: 2025-08-05

---

## 🌍 Global-First Deployment Architecture

Agentic RedTeam Radar is designed for **global-first deployment** with multi-region support, compliance with international data protection laws, and enterprise-grade scalability.

### Deployment Options

| Platform | Use Case | Complexity | Scalability |
|----------|----------|------------|-------------|
| **Docker Compose** | Development, Small Production | Low | Medium |
| **Kubernetes** | Enterprise Production | Medium | High |
| **Cloud Managed** | Serverless/Managed | Low | Very High |
| **Hybrid Cloud** | Multi-Cloud Strategy | High | Very High |

---

## 🐳 Docker Deployment

### Quick Start with Docker Compose

#### 1. Prerequisites
```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo pip install docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### 2. Environment Setup
```bash
# Clone repository
git clone https://github.com/terragonlabs/agentic-redteam-radar.git
cd agentic-redteam-radar

# Create environment file
cp .env.example .env.prod

# Configure environment variables
export DB_PASSWORD="your-secure-db-password"
export REDIS_PASSWORD="your-secure-redis-password"
export GRAFANA_PASSWORD="your-secure-grafana-password"
export JWT_SECRET="your-jwt-secret-key"
```

#### 3. Production Deployment
```bash
# Start production stack
docker-compose -f deployment/docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f deployment/docker-compose.prod.yml ps

# Check health
curl http://localhost:8000/health
```

#### 4. SSL/TLS Setup
```bash
# Generate SSL certificates (Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d radar.yourdomain.com

# Configure Nginx SSL
cp deployment/nginx/ssl.conf.example deployment/nginx/conf.d/ssl.conf
# Edit ssl.conf with your certificate paths

# Restart Nginx
docker-compose -f deployment/docker-compose.prod.yml restart nginx
```

---

## ☸️ Kubernetes Deployment

### Enterprise Kubernetes Deployment

#### 1. Prerequisites
```bash
# Kubernetes cluster (1.20+)
kubectl version --client

# Helm (for package management)
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Verify cluster access
kubectl cluster-info
```

#### 2. Namespace and RBAC Setup
```bash
# Create namespace
kubectl apply -f deployment/kubernetes/radar-deployment.yaml

# Verify namespace
kubectl get namespace agentic-redteam
```

#### 3. Secrets Configuration
```bash
# Create secrets (base64 encoded)
DB_PASSWORD_B64=$(echo -n "your-db-password" | base64)
REDIS_PASSWORD_B64=$(echo -n "your-redis-password" | base64)
JWT_SECRET_B64=$(echo -n "your-jwt-secret" | base64)

# Update secrets in deployment YAML
sed -i "s/cGFzc3dvcmQxMjM=/$DB_PASSWORD_B64/g" deployment/kubernetes/radar-deployment.yaml
sed -i "s/cmVkaXNwYXNzd29yZA==/$REDIS_PASSWORD_B64/g" deployment/kubernetes/radar-deployment.yaml
sed -i "s/and0c2VjcmV0a2V5Zm9ycmFkYXI=/$JWT_SECRET_B64/g" deployment/kubernetes/radar-deployment.yaml
```

#### 4. Deploy Application
```bash
# Deploy all components
kubectl apply -f deployment/kubernetes/radar-deployment.yaml

# Check deployment status
kubectl get pods -n agentic-redteam
kubectl get services -n agentic-redteam
kubectl get ingress -n agentic-redteam

# View logs
kubectl logs -f deployment/radar-app -n agentic-redteam
```

#### 5. Configure Ingress
```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Configure Let's Encrypt issuer
kubectl apply -f deployment/kubernetes/cert-issuer.yaml
```

---

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### 1. EKS Cluster Setup
```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create EKS cluster
eksctl create cluster \
  --name radar-cluster \
  --region us-west-2 \
  --nodegroup-name radar-nodes \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed
```

#### 2. AWS Services Integration
```bash
# Install AWS Load Balancer Controller
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=radar-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Configure RDS for PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier radar-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username radar \
  --master-user-password your-secure-password \
  --allocated-storage 20
```

### Azure Deployment

#### 1. AKS Cluster Setup
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login and create resource group
az login
az group create --name radar-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group radar-rg \
  --name radar-aks \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group radar-rg --name radar-aks
```

#### 2. Azure Services Integration
```bash
# Install NGINX Ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Configure Azure Database for PostgreSQL
az postgres server create \
  --resource-group radar-rg \
  --name radar-postgres \
  --location eastus \
  --admin-user radar \
  --admin-password your-secure-password \
  --sku-name GP_Gen5_2
```

### Google Cloud Platform

#### 1. GKE Cluster Setup
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Create GKE cluster
gcloud container clusters create radar-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials radar-cluster --zone us-central1-a
```

---

## 🌍 Multi-Region Deployment

### Global Architecture

```mermaid
graph TB
    subgraph "US-East (Primary)"
        US1[Radar Cluster US-East]
        DB1[PostgreSQL Primary]
        CACHE1[Redis Cluster]
    end
    
    subgraph "EU-West (Secondary)"
        EU1[Radar Cluster EU-West]
        DB2[PostgreSQL Replica]
        CACHE2[Redis Cluster]
    end
    
    subgraph "Asia-Pacific"
        AP1[Radar Cluster AP-Southeast]
        DB3[PostgreSQL Replica]
        CACHE3[Redis Cluster]
    end
    
    LB[Global Load Balancer]
    
    LB --> US1
    LB --> EU1
    LB --> AP1
    
    DB1 --> DB2
    DB1 --> DB3
```

### Region Configuration

#### 1. Primary Region (US-East)
```yaml
# deployment/regions/us-east/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../../kubernetes/radar-deployment.yaml

patchesStrategicMerge:
- region-config.yaml

configMapGenerator:
- name: radar-config
  files:
  - radar.yaml=us-east-config.yaml
```

#### 2. Secondary Regions
```yaml
# deployment/regions/eu-west/region-config.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: radar-app
  namespace: agentic-redteam
spec:
  template:
    spec:
      containers:
      - name: radar
        env:
        - name: REGION
          value: "eu-west"
        - name: DATABASE_URL
          value: "postgresql://radar:password@eu-postgres:5432/radar_prod"
        - name: REDIS_URL
          value: "redis://eu-redis:6379/0"
```

### Global Load Balancer Setup

#### CloudFlare Configuration
```bash
# Install CloudFlare CLI
npm install -g cloudflare-cli

# Configure DNS records
cf dns create radar.terragonlabs.com CNAME us-east.radar.terragonlabs.com
cf dns create radar.terragonlabs.com CNAME eu-west.radar.terragonlabs.com
cf dns create radar.terragonlabs.com CNAME ap-southeast.radar.terragonlabs.com

# Enable load balancing
cf lb create radar.terragonlabs.com \
  --pool us-east:us-east.radar.terragonlabs.com \
  --pool eu-west:eu-west.radar.terragonlabs.com \
  --pool ap-southeast:ap-southeast.radar.terragonlabs.com
```

---

## 📊 Monitoring & Observability

### Prometheus & Grafana Setup

#### 1. Install Monitoring Stack
```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=your-secure-password
```

#### 2. Configure Service Monitoring
```yaml
# monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: radar-metrics
  namespace: agentic-redteam
spec:
  selector:
    matchLabels:
      app: radar-app
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

#### 3. Import Dashboards
```bash
# Import Grafana dashboards
kubectl apply -f monitoring/grafana/dashboards/

# Access Grafana
kubectl port-forward service/prometheus-grafana 3000:80 -n monitoring
# Open http://localhost:3000 (admin/your-secure-password)
```

### Logging with ELK Stack

#### 1. Install Elasticsearch
```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
```

#### 2. Install Kibana
```bash
helm install kibana elastic/kibana -n logging
```

#### 3. Configure Filebeat
```bash
helm install filebeat elastic/filebeat -n logging
```

---

## 🔒 Security Configuration

### SSL/TLS Setup

#### 1. Certificate Management
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@terragonlabs.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

#### 2. Network Security
```bash
# Apply network policies
kubectl apply -f deployment/kubernetes/network-policies.yaml

# Configure Pod Security Standards
kubectl label namespace agentic-redteam \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### Secrets Management

#### 1. External Secrets Operator
```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Configure AWS Secrets Manager
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: agentic-redteam
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
EOF
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Deployment

#### 1. Workflow Configuration
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Login to Amazon ECR
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: agentic-redteam-radar
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Deploy to EKS
      run: |
        aws eks update-kubeconfig --region us-west-2 --name radar-cluster
        kubectl set image deployment/radar-app radar=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG -n agentic-redteam
        kubectl rollout status deployment/radar-app -n agentic-redteam
```

---

## 📋 Production Checklist

### Pre-Deployment
- [ ] **Environment Variables**: All secrets configured
- [ ] **SSL Certificates**: Valid certificates installed
- [ ] **Database**: Production database configured and backed up
- [ ] **Monitoring**: Prometheus and Grafana configured
- [ ] **Logging**: Log aggregation setup
- [ ] **Security**: Network policies and RBAC configured
- [ ] **Resources**: CPU/Memory limits configured
- [ ] **Scaling**: HPA and VPA configured
- [ ] **Backup**: Backup procedures tested

### Health Checks
```bash
# Application health
curl -f https://radar.yourdomain.com/health

# Database connectivity
kubectl exec -it deployment/radar-app -n agentic-redteam -- \
  python -c "from agentic_redteam.database import test_connection; test_connection()"

# Redis connectivity
kubectl exec -it deployment/redis -n agentic-redteam -- redis-cli ping

# Metrics endpoint
curl -f https://radar.yourdomain.com/metrics
```

### Post-Deployment
- [ ] **Functionality Test**: End-to-end testing
- [ ] **Performance Test**: Load testing
- [ ] **Security Test**: Vulnerability scanning
- [ ] **Monitoring Alerts**: Alert rules configured
- [ ] **Documentation**: Runbooks updated
- [ ] **Team Training**: Operations team trained

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Pod Startup Issues
```bash
# Check pod status
kubectl get pods -n agentic-redteam

# View pod logs
kubectl logs deployment/radar-app -n agentic-redteam

# Check events
kubectl get events -n agentic-redteam --sort-by='.lastTimestamp'
```

#### 2. Database Connection Issues
```bash
# Test database connection
kubectl exec -it deployment/radar-app -n agentic-redteam -- \
  psql $DATABASE_URL -c "SELECT 1"

# Check database logs
kubectl logs deployment/postgres -n agentic-redteam
```

#### 3. Performance Issues
```bash
# Check resource usage
kubectl top pods -n agentic-redteam

# View HPA status
kubectl get hpa -n agentic-redteam

# Check metrics
kubectl port-forward service/prometheus-server 9090:80 -n monitoring
# Open http://localhost:9090
```

### Emergency Procedures

#### 1. Rollback Deployment
```bash
# View rollout history
kubectl rollout history deployment/radar-app -n agentic-redteam

# Rollback to previous version
kubectl rollout undo deployment/radar-app -n agentic-redteam

# Rollback to specific revision
kubectl rollout undo deployment/radar-app --to-revision=2 -n agentic-redteam
```

#### 2. Scale Down/Up
```bash
# Emergency scale down
kubectl scale deployment/radar-app --replicas=0 -n agentic-redteam

# Scale back up
kubectl scale deployment/radar-app --replicas=3 -n agentic-redteam
```

---

## 📞 Support

### Production Support Contacts
- **Emergency**: +1-800-TERRAGON
- **Security Issues**: security@terragonlabs.com
- **Technical Support**: support@terragonlabs.com
- **DevOps Team**: devops@terragonlabs.com

### Documentation
- **API Documentation**: https://docs.radar.terragonlabs.com
- **Runbooks**: https://runbooks.radar.terragonlabs.com  
- **Status Page**: https://status.radar.terragonlabs.com

---

**© 2025 Terragon Labs. All rights reserved.**