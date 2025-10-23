# Home Assistant Bridge Service - Deployment Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Production Configuration](#production-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Scaling Considerations](#scaling-considerations)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker installed
- Home Assistant instance accessible
- Valid Home Assistant long-lived access token

### Basic Docker Run

```bash
# Clone the repository
git clone <repository-url>
cd ha-bridge-service

# Create environment file
cp env.example .env
# Edit .env with your configuration

# Run with Docker
docker run -d \
  --name ha-bridge \
  --env-file .env \
  -p 8000:8000 \
  ha-bridge-service:latest
```

### Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health

# Test API endpoint
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/v1/states/all
```

## Docker Deployment

### Single Container Deployment

#### Build Docker Image

```bash
# Build the image
docker build -t ha-bridge-service:latest .

# Tag for registry
docker tag ha-bridge-service:latest your-registry/ha-bridge-service:latest
```

#### Run Container

```bash
# Basic run
docker run -d \
  --name ha-bridge \
  --env-file .env \
  -p 8000:8000 \
  ha-bridge-service:latest

# With resource limits
docker run -d \
  --name ha-bridge \
  --env-file .env \
  -p 8000:8000 \
  --memory=512m \
  --cpus=1.0 \
  --restart=unless-stopped \
  ha-bridge-service:latest
```

#### Container Configuration

```bash
# Environment variables
docker run -d \
  --name ha-bridge \
  -e HA_URL=https://your-ha-server:8123 \
  -e HA_TOKEN=your-long-lived-token \
  -e API_KEYS='["key1","key2","key3"]' \
  -e CACHE_TTL=300 \
  -e RATE_LIMIT_REQUESTS=100 \
  -e RATE_LIMIT_WINDOW=60 \
  -e WEBSOCKET_ENABLED=true \
  -p 8000:8000 \
  ha-bridge-service:latest
```

### Dockerfile Optimization

```dockerfile
# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r hauser && useradd -r -g hauser hauser

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY . .

# Change ownership
RUN chown -R hauser:hauser /app
USER hauser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose Deployment

### Basic Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  ha-bridge:
    build: .
    container_name: ha-bridge
    ports:
      - "8000:8000"
    environment:
      - HA_URL=https://your-ha-server:8123
      - HA_TOKEN=${HA_TOKEN}
      - API_KEYS=${API_KEYS}
      - CACHE_TTL=300
      - RATE_LIMIT_REQUESTS=100
      - RATE_LIMIT_WINDOW=60
      - WEBSOCKET_ENABLED=true
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Add monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: ha-bridge-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    depends_on:
      - ha-bridge

  grafana:
    image: grafana/grafana:latest
    container_name: ha-bridge-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  grafana-storage:
```

### Production Compose Setup

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ha-bridge:
    build: 
      context: .
      dockerfile: Dockerfile.prod
    container_name: ha-bridge-prod
    ports:
      - "8000:8000"
    environment:
      - HA_URL=${HA_URL}
      - HA_TOKEN=${HA_TOKEN}
      - API_KEYS=${API_KEYS}
      - CACHE_TTL=300
      - STATES_CACHE_TTL=60
      - SERVICES_CACHE_TTL=1800
      - CONFIG_CACHE_TTL=3600
      - RATE_LIMIT_REQUESTS=200
      - RATE_LIMIT_WINDOW=60
      - WEBSOCKET_ENABLED=true
      - WEBSOCKET_FILTER_ENABLED=true
      - WEBSOCKET_EXCLUDE_DOMAINS=media_player,camera
      - METRICS_ENABLED=true
      - DEBUG=false
    volumes:
      - ./logs:/app/logs:rw
      - ./config:/app/config:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
        reservations:
          memory: 512M
          cpus: '1'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - ha-bridge-network

  nginx:
    image: nginx:alpine
    container_name: ha-bridge-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - ha-bridge
    restart: unless-stopped
    networks:
      - ha-bridge-network

  redis:
    image: redis:alpine
    container_name: ha-bridge-redis
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - ha-bridge-network

networks:
  ha-bridge-network:
    driver: bridge

volumes:
  redis-data:
```

### Environment File

```bash
# .env.prod
HA_URL=https://your-ha-server:8123
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
API_KEYS=["prod-key-1","prod-key-2","prod-key-3"]
CACHE_TTL=300
STATES_CACHE_TTL=60
SERVICES_CACHE_TTL=1800
CONFIG_CACHE_TTL=3600
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW=60
WEBSOCKET_ENABLED=true
WEBSOCKET_FILTER_ENABLED=true
WEBSOCKET_EXCLUDE_DOMAINS=media_player,camera
METRICS_ENABLED=true
DEBUG=false
```

### Deploy with Compose

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d

# Scale service
docker-compose up -d --scale ha-bridge=3

# View logs
docker-compose logs -f ha-bridge

# Update service
docker-compose pull
docker-compose up -d
```

## Kubernetes Deployment

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ha-bridge
  labels:
    name: ha-bridge
```

### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ha-bridge-config
  namespace: ha-bridge
data:
  HA_URL: "https://your-ha-server:8123"
  CACHE_TTL: "300"
  STATES_CACHE_TTL: "60"
  SERVICES_CACHE_TTL: "1800"
  CONFIG_CACHE_TTL: "3600"
  RATE_LIMIT_REQUESTS: "200"
  RATE_LIMIT_WINDOW: "60"
  WEBSOCKET_ENABLED: "true"
  WEBSOCKET_FILTER_ENABLED: "true"
  WEBSOCKET_EXCLUDE_DOMAINS: "media_player,camera"
  METRICS_ENABLED: "true"
  DEBUG: "false"
```

### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ha-bridge-secrets
  namespace: ha-bridge
type: Opaque
data:
  HA_TOKEN: <base64-encoded-token>
  API_KEYS: <base64-encoded-json-array>
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-bridge
  namespace: ha-bridge
  labels:
    app: ha-bridge
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ha-bridge
  template:
    metadata:
      labels:
        app: ha-bridge
    spec:
      containers:
      - name: ha-bridge
        image: ha-bridge-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: HA_URL
          valueFrom:
            configMapKeyRef:
              name: ha-bridge-config
              key: HA_URL
        - name: HA_TOKEN
          valueFrom:
            secretKeyRef:
              name: ha-bridge-secrets
              key: HA_TOKEN
        - name: API_KEYS
          valueFrom:
            secretKeyRef:
              name: ha-bridge-secrets
              key: API_KEYS
        - name: CACHE_TTL
          valueFrom:
            configMapKeyRef:
              name: ha-bridge-config
              key: CACHE_TTL
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
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
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ha-bridge-service
  namespace: ha-bridge
  labels:
    app: ha-bridge
spec:
  selector:
    app: ha-bridge
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ha-bridge-ingress
  namespace: ha-bridge
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - ha-bridge.yourdomain.com
    secretName: ha-bridge-tls
  rules:
  - host: ha-bridge.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ha-bridge-service
            port:
              number: 8000
```

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ha-bridge-hpa
  namespace: ha-bridge
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ha-bridge
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

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# Check deployment
kubectl get pods -n ha-bridge
kubectl get services -n ha-bridge
kubectl get ingress -n ha-bridge

# View logs
kubectl logs -f deployment/ha-bridge -n ha-bridge

# Scale deployment
kubectl scale deployment ha-bridge --replicas=5 -n ha-bridge
```

## Environment Configuration

### Required Environment Variables

```bash
# Core Configuration
HA_URL=https://your-ha-server:8123
HA_TOKEN=your-long-lived-access-token
API_KEYS=["key1","key2","key3"]

# Optional Configuration
CACHE_TTL=300
STATES_CACHE_TTL=60
SERVICES_CACHE_TTL=1800
CONFIG_CACHE_TTL=3600
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
WEBSOCKET_ENABLED=true
WEBSOCKET_FILTER_ENABLED=true
WEBSOCKET_EXCLUDE_DOMAINS=media_player,camera
METRICS_ENABLED=true
DEBUG=false
```

### Environment-Specific Configurations

#### Development

```bash
# .env.dev
HA_URL=http://localhost:8123
HA_TOKEN=dev-token
API_KEYS=["dev-key"]
CACHE_TTL=60
DEBUG=true
WEBSOCKET_ENABLED=false
```

#### Staging

```bash
# .env.staging
HA_URL=https://staging-ha.yourdomain.com:8123
HA_TOKEN=staging-token
API_KEYS=["staging-key-1","staging-key-2"]
CACHE_TTL=180
DEBUG=false
WEBSOCKET_ENABLED=true
```

#### Production

```bash
# .env.prod
HA_URL=https://ha.yourdomain.com:8123
HA_TOKEN=prod-token
API_KEYS=["prod-key-1","prod-key-2","prod-key-3"]
CACHE_TTL=300
STATES_CACHE_TTL=60
SERVICES_CACHE_TTL=1800
CONFIG_CACHE_TTL=3600
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW=60
WEBSOCKET_ENABLED=true
WEBSOCKET_FILTER_ENABLED=true
WEBSOCKET_EXCLUDE_DOMAINS=media_player,camera
METRICS_ENABLED=true
DEBUG=false
```

## Production Configuration

### Performance Tuning

```bash
# High-performance configuration
CACHE_TTL=600
STATES_CACHE_TTL=120
SERVICES_CACHE_TTL=3600
CONFIG_CACHE_TTL=7200
RATE_LIMIT_REQUESTS=500
RATE_LIMIT_WINDOW=60
WEBSOCKET_ENABLED=true
WEBSOCKET_FILTER_ENABLED=true
WEBSOCKET_EXCLUDE_DOMAINS=media_player,camera,automation
```

### Resource Limits

```yaml
# Docker Compose resource limits
services:
  ha-bridge:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '4'
        reservations:
          memory: 1G
          cpus: '2'
```

### Health Checks

```yaml
# Comprehensive health checks
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging Configuration

```python
# Production logging
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Set log level
logging.basicConfig(level=logging.INFO)
```

## Monitoring & Logging

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ha-bridge'
    static_configs:
      - targets: ['ha-bridge:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "HA Bridge Service",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / rate(cache_requests_total[5m]) * 100",
            "legendFormat": "Hit Rate %"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

```yaml
# ELK Stack integration
version: '3.8'
services:
  ha-bridge:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    labels:
      - "logging=promtail"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - ./promtail.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

## Scaling Considerations

### Horizontal Scaling

```yaml
# Multiple replicas
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-bridge
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 2
```

### Load Balancing

```yaml
# Nginx load balancer
upstream ha_bridge {
    least_conn;
    server ha-bridge-1:8000;
    server ha-bridge-2:8000;
    server ha-bridge-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://ha_bridge;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Scaling

```yaml
# Redis cluster for caching
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
spec:
  serviceName: redis-cluster
  replicas: 3
  template:
    spec:
      containers:
      - name: redis
        image: redis:alpine
        command:
        - redis-server
        - --cluster-enabled
        - --cluster-config-file
        - /data/nodes.conf
```

## Security Hardening

### Network Security

```yaml
# Network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ha-bridge-netpol
spec:
  podSelector:
    matchLabels:
      app: ha-bridge
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 8123
```

### Pod Security

```yaml
# Pod security context
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: ha-bridge
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### Secrets Management

```bash
# Use external secret management
# HashiCorp Vault
vault kv put secret/ha-bridge \
  ha_token="your-token" \
  api_keys='["key1","key2"]'

# AWS Secrets Manager
aws secretsmanager create-secret \
  --name ha-bridge-secrets \
  --secret-string '{"ha_token":"your-token","api_keys":["key1","key2"]}'
```

## Troubleshooting

### Common Deployment Issues

#### Container Won't Start

```bash
# Check container logs
docker logs ha-bridge

# Check environment variables
docker exec ha-bridge env | grep HA_

# Verify configuration
docker exec ha-bridge cat /app/.env
```

#### Service Unreachable

```bash
# Check service status
kubectl get pods -n ha-bridge
kubectl describe pod ha-bridge-xxx -n ha-bridge

# Check service endpoints
kubectl get endpoints -n ha-bridge

# Test connectivity
kubectl exec -it ha-bridge-xxx -n ha-bridge -- curl localhost:8000/health
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n ha-bridge

# Check HPA status
kubectl get hpa -n ha-bridge

# Monitor metrics
curl http://localhost:8000/metrics
```

### Debug Commands

```bash
# Docker debugging
docker exec -it ha-bridge /bin/bash
docker logs -f ha-bridge
docker stats ha-bridge

# Kubernetes debugging
kubectl exec -it ha-bridge-xxx -n ha-bridge -- /bin/bash
kubectl logs -f deployment/ha-bridge -n ha-bridge
kubectl describe pod ha-bridge-xxx -n ha-bridge
```

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl -H "Authorization: Bearer your-key" http://localhost:8000/status

# Metrics
curl http://localhost:8000/metrics

# Service info
curl http://localhost:8000/info
```

## Best Practices

### 1. Environment Management

- Use separate environments for dev/staging/prod
- Never commit secrets to version control
- Use external secret management systems
- Rotate API keys regularly

### 2. Resource Management

- Set appropriate resource limits
- Monitor resource usage
- Use horizontal pod autoscaling
- Implement circuit breakers

### 3. Security

- Run containers as non-root users
- Use read-only root filesystems
- Implement network policies
- Regular security updates

### 4. Monitoring

- Implement comprehensive logging
- Set up alerting for critical metrics
- Monitor cache hit rates
- Track API usage patterns

### 5. Backup & Recovery

- Regular configuration backups
- Test disaster recovery procedures
- Document rollback procedures
- Maintain multiple deployment environments

This deployment guide provides comprehensive instructions for deploying the Home Assistant Bridge Service in various environments, from simple Docker containers to production Kubernetes clusters with full monitoring and security hardening.