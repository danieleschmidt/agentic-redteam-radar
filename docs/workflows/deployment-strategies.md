# Advanced Deployment Strategies

This document outlines enterprise-grade deployment strategies for the Agentic RedTeam Radar security testing framework, including blue-green deployments, canary releases, and progressive delivery approaches.

## Overview

Advanced deployment strategies ensure reliable, safe, and efficient delivery of security testing tools while minimizing risk and downtime. This document provides templates and guidance for implementing sophisticated deployment patterns.

## Blue-Green Deployment Strategy

### Infrastructure Setup

Blue-green deployment maintains two identical production environments, switching between them during deployments.

#### Environment Configuration

```yaml
# infrastructure/environments/production-blue.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: radar-config-blue
  namespace: security-tools
data:
  environment: "production-blue"
  database_url: "postgresql://radar-blue-db:5432/radar"
  redis_url: "redis://radar-blue-cache:6379"
  log_level: "INFO"
  max_concurrent_scans: "100"
  
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: radar-scanner-blue
  namespace: security-tools
  labels:
    app: radar-scanner
    environment: blue
    version: "{{ .Values.version }}"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: radar-scanner
      environment: blue
  template:
    metadata:
      labels:
        app: radar-scanner
        environment: blue
        version: "{{ .Values.version }}"
    spec:
      containers:
      - name: radar-scanner
        image: "agentic-redteam-radar:{{ .Values.version }}"
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production-blue"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: radar-secrets-blue
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
```

#### Blue-Green Deployment Workflow

```yaml
# .github/workflows/blue-green-deploy.yml
name: Blue-Green Deployment
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true
      target_environment:
        description: 'Target environment (blue/green)'
        required: true
        type: choice
        options:
          - blue
          - green

env:
  KUBECTL_VERSION: '1.28.0'
  HELM_VERSION: '3.12.0'

jobs:
  prepare-deployment:
    name: Prepare Deployment
    runs-on: ubuntu-latest
    outputs:
      current_environment: ${{ steps.detect.outputs.current_environment }}
      target_environment: ${{ steps.detect.outputs.target_environment }}
      
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: ${{ env.KUBECTL_VERSION }}
      
      - name: Configure kubeconfig
        run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Detect current active environment
        id: detect
        run: |
          # Check which environment is currently receiving traffic
          CURRENT=$(kubectl get service radar-scanner-active -o jsonpath='{.spec.selector.environment}' || echo "none")
          TARGET="${{ github.event.inputs.target_environment }}"
          
          echo "current_environment=${CURRENT}" >> $GITHUB_OUTPUT
          echo "target_environment=${TARGET}" >> $GITHUB_OUTPUT
          
          echo "Current active environment: ${CURRENT}"
          echo "Target deployment environment: ${TARGET}"

  deploy-inactive:
    name: Deploy to Inactive Environment
    runs-on: ubuntu-latest
    needs: prepare-deployment
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup tools
        run: |
          # Install kubectl
          curl -LO "https://dl.k8s.io/release/v${{ env.KUBECTL_VERSION }}/bin/linux/amd64/kubectl"
          chmod +x kubectl && sudo mv kubectl /usr/local/bin/
          
          # Install helm
          curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
          chmod 700 get_helm.sh && ./get_helm.sh --version v${{ env.HELM_VERSION }}
          
          # Configure kubeconfig
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Deploy to target environment
        run: |
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          VERSION="${{ github.event.inputs.version }}"
          
          # Deploy using Helm
          helm upgrade --install radar-scanner-${TARGET_ENV} \
            ./helm/radar-scanner \
            --namespace security-tools \
            --set environment=${TARGET_ENV} \
            --set image.tag=${VERSION} \
            --set replicaCount=3 \
            --wait --timeout=10m
          
          echo "Deployed version ${VERSION} to ${TARGET_ENV} environment"
      
      - name: Verify deployment
        run: |
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          
          # Wait for rollout to complete
          kubectl rollout status deployment/radar-scanner-${TARGET_ENV} -n security-tools --timeout=300s
          
          # Verify pods are ready
          kubectl wait --for=condition=ready pod -l app=radar-scanner,environment=${TARGET_ENV} -n security-tools --timeout=300s
          
          echo "Deployment verification completed"

  smoke-tests:
    name: Run Smoke Tests
    runs-on: ubuntu-latest
    needs: [prepare-deployment, deploy-inactive]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install test dependencies
        run: |
          pip install requests pytest
      
      - name: Run smoke tests against inactive environment
        run: |
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          
          # Port forward to access inactive environment
          kubectl port-forward svc/radar-scanner-${TARGET_ENV} 8080:8000 -n security-tools &
          sleep 10
          
          # Run smoke tests
          python -m pytest tests/smoke/ \
            --base-url=http://localhost:8080 \
            --timeout=30 \
            -v
        timeout-minutes: 10

  switch-traffic:
    name: Switch Traffic
    runs-on: ubuntu-latest
    needs: [prepare-deployment, deploy-inactive, smoke-tests]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        run: |
          curl -LO "https://dl.k8s.io/release/v${{ env.KUBECTL_VERSION }}/bin/linux/amd64/kubectl"
          chmod +x kubectl && sudo mv kubectl /usr/local/bin/
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Switch active service
        run: |
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          CURRENT_ENV="${{ needs.prepare-deployment.outputs.current_environment }}"
          
          # Update active service to point to new environment
          kubectl patch service radar-scanner-active -n security-tools \
            -p '{"spec":{"selector":{"environment":"'${TARGET_ENV}'"}}}'
          
          echo "Switched traffic from ${CURRENT_ENV} to ${TARGET_ENV}"
      
      - name: Wait for traffic switch
        run: |
          # Wait a bit for DNS/load balancer updates
          sleep 30
          
          # Verify the switch worked
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          ACTIVE_ENV=$(kubectl get service radar-scanner-active -o jsonpath='{.spec.selector.environment}')
          
          if [[ "$ACTIVE_ENV" == "$TARGET_ENV" ]]; then
            echo "Traffic successfully switched to ${TARGET_ENV}"
          else
            echo "Traffic switch failed. Expected: ${TARGET_ENV}, Actual: ${ACTIVE_ENV}"
            exit 1
          fi

  post-deployment-tests:
    name: Post-Deployment Tests
    runs-on: ubuntu-latest
    needs: [prepare-deployment, switch-traffic]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install test dependencies
        run: |
          pip install -e .[test]
      
      - name: Run integration tests
        run: |
          # Run integration tests against live production
          pytest tests/integration/ \
            --base-url=${{ secrets.PRODUCTION_URL }} \
            --api-key=${{ secrets.PRODUCTION_API_KEY }} \
            --timeout=60 \
            -v
        timeout-minutes: 20

  cleanup-old-environment:
    name: Cleanup Old Environment
    runs-on: ubuntu-latest
    needs: [prepare-deployment, post-deployment-tests]
    if: needs.post-deployment-tests.result == 'success'
    
    steps:
      - name: Setup kubectl
        run: |
          curl -LO "https://dl.k8s.io/release/v${{ env.KUBECTL_VERSION }}/bin/linux/amd64/kubectl"
          chmod +x kubectl && sudo mv kubectl /usr/local/bin/
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Scale down old environment
        run: |
          CURRENT_ENV="${{ needs.prepare-deployment.outputs.current_environment }}"
          
          if [[ "$CURRENT_ENV" != "none" ]]; then
            # Scale down the old environment (but don't delete for rollback capability)
            kubectl scale deployment radar-scanner-${CURRENT_ENV} --replicas=1 -n security-tools
            echo "Scaled down old environment: ${CURRENT_ENV}"
          fi

  rollback:
    name: Rollback on Failure
    runs-on: ubuntu-latest
    needs: [prepare-deployment, deploy-inactive, smoke-tests, switch-traffic, post-deployment-tests]
    if: failure()
    
    steps:
      - name: Setup kubectl
        run: |
          curl -LO "https://dl.k8s.io/release/v${{ env.KUBECTL_VERSION }}/bin/linux/amd64/kubectl"
          chmod +x kubectl && sudo mv kubectl /usr/local/bin/
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Rollback traffic
        run: |
          CURRENT_ENV="${{ needs.prepare-deployment.outputs.current_environment }}"
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          
          if [[ "$CURRENT_ENV" != "none" ]]; then
            # Switch traffic back to previous environment
            kubectl patch service radar-scanner-active -n security-tools \
              -p '{"spec":{"selector":{"environment":"'${CURRENT_ENV}'"}}}'
            
            echo "Rolled back traffic to ${CURRENT_ENV}"
          fi
      
      - name: Scale down failed deployment
        run: |
          TARGET_ENV="${{ needs.prepare-deployment.outputs.target_environment }}"
          kubectl scale deployment radar-scanner-${TARGET_ENV} --replicas=0 -n security-tools
          echo "Scaled down failed deployment: ${TARGET_ENV}"
```

## Canary Deployment Strategy

### Canary Release Configuration

```yaml
# .github/workflows/canary-deploy.yml
name: Canary Deployment
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true
      canary_percentage:
        description: 'Percentage of traffic for canary (1-100)'
        required: true
        default: '10'

jobs:
  deploy-canary:
    name: Deploy Canary
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy canary version
        run: |
          VERSION="${{ github.event.inputs.version }}"
          PERCENTAGE="${{ github.event.inputs.canary_percentage }}"
          
          # Deploy canary using Argo Rollouts or similar
          cat <<EOF | kubectl apply -f -
          apiVersion: argoproj.io/v1alpha1
          kind: Rollout
          metadata:
            name: radar-scanner-rollout
            namespace: security-tools
          spec:
            replicas: 5
            strategy:
              canary:
                steps:
                - setWeight: ${PERCENTAGE}
                - pause: {duration: 10m}
                - setWeight: 50
                - pause: {duration: 10m}
                - setWeight: 100
                canaryService: radar-scanner-canary
                stableService: radar-scanner-stable
                analysis:
                  templates:
                  - templateName: success-rate
                  args:
                  - name: service-name
                    value: radar-scanner-canary
            selector:
              matchLabels:
                app: radar-scanner
            template:
              metadata:
                labels:
                  app: radar-scanner
              spec:
                containers:
                - name: radar-scanner
                  image: agentic-redteam-radar:${VERSION}
                  ports:
                  - containerPort: 8000
          EOF

  monitor-canary:
    name: Monitor Canary
    runs-on: ubuntu-latest
    needs: deploy-canary
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Monitor metrics
        run: |
          # Monitor canary metrics for 10 minutes
          for i in {1..60}; do
            # Get canary metrics
            ERROR_RATE=$(curl -s "${{ secrets.PROMETHEUS_URL }}/api/v1/query?query=rate(http_requests_total{job=\"radar-scanner-canary\",status=~\"5..\"}[5m])/rate(http_requests_total{job=\"radar-scanner-canary\"}[5m])" | jq -r '.data.result[0].value[1] // "0"')
            
            RESPONSE_TIME=$(curl -s "${{ secrets.PROMETHEUS_URL }}/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket{job=\"radar-scanner-canary\"}[5m]))" | jq -r '.data.result[0].value[1] // "0"')
            
            echo "Iteration $i: Error rate: $ERROR_RATE, 95th percentile response time: $RESPONSE_TIME"
            
            # Check thresholds
            if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
              echo "Error rate too high: $ERROR_RATE"
              exit 1
            fi
            
            if (( $(echo "$RESPONSE_TIME > 2.0" | bc -l) )); then
              echo "Response time too high: $RESPONSE_TIME"
              exit 1
            fi
            
            sleep 10
          done

  promote-canary:
    name: Promote Canary
    runs-on: ubuntu-latest
    needs: [deploy-canary, monitor-canary]
    
    steps:
      - name: Promote to stable
        run: |
          # Promote canary to stable
          kubectl argo rollouts promote radar-scanner-rollout -n security-tools
          
          # Wait for rollout to complete
          kubectl argo rollouts get rollout radar-scanner-rollout -n security-tools --watch
```

## Progressive Delivery Pipeline

### Feature Flag Integration

```yaml
# .github/workflows/progressive-delivery.yml
name: Progressive Delivery
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      feature_flags:
        description: 'Feature flags to enable (JSON)'
        required: false
        default: '{}'

jobs:
  deploy-with-flags:
    name: Deploy with Feature Flags
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy with feature flags
        run: |
          FEATURE_FLAGS='${{ github.event.inputs.feature_flags }}'
          if [[ -z "$FEATURE_FLAGS" ]]; then
            FEATURE_FLAGS='{
              "new_attack_patterns": {"enabled": false, "rollout": 0},
              "enhanced_reporting": {"enabled": true, "rollout": 10},
              "experimental_ml": {"enabled": false, "rollout": 0}
            }'
          fi
          
          # Deploy with feature flags
          helm upgrade radar-scanner ./helm/radar-scanner \
            --set featureFlags="$FEATURE_FLAGS" \
            --namespace security-tools

  gradual-rollout:
    name: Gradual Feature Rollout
    runs-on: ubuntu-latest
    needs: deploy-with-flags
    
    steps:
      - name: Increase rollout percentage
        run: |
          # Gradually increase feature rollout
          for percentage in 10 25 50 75 100; do
            echo "Rolling out to $percentage% of users"
            
            # Update feature flag rollout percentage
            curl -X PATCH "${{ secrets.FEATURE_FLAG_API }}/flags/enhanced_reporting" \
              -H "Authorization: Bearer ${{ secrets.FEATURE_FLAG_TOKEN }}" \
              -H "Content-Type: application/json" \
              -d "{\"rollout\": $percentage}"
            
            # Monitor for 5 minutes
            sleep 300
            
            # Check metrics before proceeding
            ERROR_RATE=$(curl -s "${{ secrets.PROMETHEUS_URL }}/api/v1/query?query=rate(errors_total[5m])" | jq -r '.data.result[0].value[1] // "0"')
            
            if (( $(echo "$ERROR_RATE > 0.02" | bc -l) )); then
              echo "Error rate too high, rolling back"
              curl -X PATCH "${{ secrets.FEATURE_FLAG_API }}/flags/enhanced_reporting" \
                -H "Authorization: Bearer ${{ secrets.FEATURE_FLAG_TOKEN }}" \
                -H "Content-Type: application/json" \
                -d "{\"rollout\": 0}"
              exit 1
            fi
          done
```

## Deployment Health Checks

### Health Check Implementation

```python
# scripts/deployment_health_check.py
#!/usr/bin/env python3
"""
Deployment health check script for production deployments.
"""

import requests
import time
import sys
import json
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def check_basic_health(self) -> bool:
        """Check basic application health."""
        try:
            response = self.session.get(
                f"{self.base_url}/health", 
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Basic health check failed: {e}")
            return False
    
    def check_readiness(self) -> bool:
        """Check application readiness."""
        try:
            response = self.session.get(
                f"{self.base_url}/ready", 
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return False
    
    def check_api_endpoints(self) -> Dict[str, bool]:
        """Check critical API endpoints."""
        endpoints = [
            "/api/v1/scan",
            "/api/v1/patterns",
            "/api/v1/agents",
            "/api/v1/reports"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    timeout=self.timeout
                )
                results[endpoint] = response.status_code in [200, 401, 403]
            except Exception as e:
                logger.error(f"Endpoint {endpoint} check failed: {e}")
                results[endpoint] = False
        
        return results
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check external dependencies."""
        try:
            response = self.session.get(
                f"{self.base_url}/health/dependencies",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"dependencies": False}
        except Exception as e:
            logger.error(f"Dependencies check failed: {e}")
            return {"dependencies": False}
    
    def run_comprehensive_check(self) -> bool:
        """Run comprehensive health check."""
        logger.info("Starting comprehensive health check...")
        
        # Basic checks
        if not self.check_basic_health():
            logger.error("Basic health check failed")
            return False
        
        if not self.check_readiness():
            logger.error("Readiness check failed")
            return False
        
        # API endpoint checks
        api_results = self.check_api_endpoints()
        failed_endpoints = [ep for ep, success in api_results.items() if not success]
        if failed_endpoints:
            logger.error(f"API endpoints failed: {failed_endpoints}")
            return False
        
        # Dependency checks
        dep_results = self.check_dependencies()
        failed_deps = [dep for dep, success in dep_results.items() if not success]
        if failed_deps:
            logger.error(f"Dependencies failed: {failed_deps}")
            return False
        
        logger.info("All health checks passed")
        return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python deployment_health_check.py <base_url>")
        sys.exit(1)
    
    base_url = sys.argv[1]
    checker = HealthChecker(base_url)
    
    # Wait for deployment to be ready
    max_retries = 30
    for attempt in range(max_retries):
        if checker.run_comprehensive_check():
            print("✅ Deployment health check passed")
            sys.exit(0)
        
        if attempt < max_retries - 1:
            logger.info(f"Health check failed, retrying in 10 seconds... (attempt {attempt + 1}/{max_retries})")
            time.sleep(10)
    
    print("❌ Deployment health check failed after all retries")
    sys.exit(1)

if __name__ == "__main__":
    main()
```

## Rollback Procedures

### Automated Rollback Workflow

```yaml
# .github/workflows/rollback.yml
name: Production Rollback
on:
  workflow_dispatch:
    inputs:
      rollback_type:
        description: 'Type of rollback'
        required: true
        type: choice
        options:
          - immediate
          - gradual
          - feature_flag
      target_version:
        description: 'Version to rollback to (optional)'
        required: false

jobs:
  immediate-rollback:
    name: Immediate Rollback
    runs-on: ubuntu-latest
    if: github.event.inputs.rollback_type == 'immediate'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        run: |
          curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"
          chmod +x kubectl && sudo mv kubectl /usr/local/bin/
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Rollback deployment
        run: |
          if [[ -n "${{ github.event.inputs.target_version }}" ]]; then
            TARGET_VERSION="${{ github.event.inputs.target_version }}"
            kubectl set image deployment/radar-scanner radar-scanner=agentic-redteam-radar:${TARGET_VERSION} -n security-tools
          else
            kubectl rollout undo deployment/radar-scanner -n security-tools
          fi
          
          kubectl rollout status deployment/radar-scanner -n security-tools --timeout=300s
      
      - name: Verify rollback
        run: |
          python scripts/deployment_health_check.py "${{ secrets.PRODUCTION_URL }}"

  gradual-rollback:
    name: Gradual Rollback
    runs-on: ubuntu-latest
    if: github.event.inputs.rollback_type == 'gradual'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Gradual traffic reduction
        run: |
          # Gradually reduce traffic to current version
          for percentage in 75 50 25 0; do
            echo "Reducing traffic to $percentage%"
            
            # Update canary weight
            kubectl patch rollout radar-scanner-rollout -n security-tools \
              --type='merge' -p="{\"spec\":{\"strategy\":{\"canary\":{\"steps\":[{\"setWeight\":$percentage}]}}}}"
            
            sleep 120  # Wait 2 minutes between steps
          done

  feature-flag-rollback:
    name: Feature Flag Rollback
    runs-on: ubuntu-latest
    if: github.event.inputs.rollback_type == 'feature_flag'
    
    steps:
      - name: Disable problematic features
        run: |
          # Disable all experimental features
          curl -X PATCH "${{ secrets.FEATURE_FLAG_API }}/flags/batch-disable" \
            -H "Authorization: Bearer ${{ secrets.FEATURE_FLAG_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"flags": ["experimental_ml", "new_attack_patterns"], "enabled": false}'
```

## Monitoring and Alerting

### Deployment Monitoring Setup

```yaml
# monitoring/deployment-alerts.yml
groups:
- name: deployment.rules
  rules:
  - alert: DeploymentFailure
    expr: kube_deployment_status_replicas_unavailable > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Deployment has unavailable replicas"
      description: "Deployment {{ $labels.deployment }} has {{ $value }} unavailable replicas"

  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: ResponseTimeHigh
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time"
      description: "95th percentile response time is {{ $value }}s"

  - alert: CanaryAnalysisFailed
    expr: argoproj_rollout_analysis_runs_failed > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Canary analysis failed"
      description: "Canary rollout analysis has failed"
```

## Best Practices

### Deployment Checklist

1. **Pre-deployment**:
   - [ ] All tests pass in CI/CD pipeline
   - [ ] Security scans completed successfully
   - [ ] Performance benchmarks within acceptable range
   - [ ] Database migrations tested (if applicable)
   - [ ] Feature flags configured correctly

2. **During Deployment**:
   - [ ] Monitor application metrics continuously
   - [ ] Verify health checks pass
   - [ ] Check error rates and response times
   - [ ] Validate that new features work as expected
   - [ ] Monitor resource utilization

3. **Post-deployment**:
   - [ ] Run smoke tests against production
   - [ ] Verify all critical user journeys work
   - [ ] Check that monitoring and alerting are functioning
   - [ ] Update documentation if needed
   - [ ] Notify stakeholders of successful deployment

### Rollback Criteria

Initiate rollback if:
- Error rate exceeds 1% for more than 2 minutes
- 95th percentile response time exceeds 2 seconds for more than 5 minutes
- More than 10% of health checks fail
- Critical functionality is broken
- Security vulnerability is discovered in production

These advanced deployment strategies provide enterprise-grade reliability and safety for deploying security-critical applications like the Agentic RedTeam Radar.