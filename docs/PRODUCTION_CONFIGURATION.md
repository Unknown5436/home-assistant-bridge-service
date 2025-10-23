# Production Configuration Guide

## Overview

This guide provides comprehensive configuration options for deploying the Home Assistant Bridge Service in production environments. It covers scaling considerations, performance tuning, security hardening, and monitoring setup.

## Production Environment Variables

### Core Configuration

```bash
# Home Assistant Connection
HA_BASE_URL=https://your-ha-instance.local:8123
HA_API_KEY=your-production-api-key-here
HA_SSL_VERIFY=true

# Bridge Service Configuration
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8000
BRIDGE_API_KEY=your-secure-bridge-api-key
BRIDGE_LOG_LEVEL=INFO

# Security Settings
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
ENABLE_CORS=true
CORS_ORIGINS=https://your-frontend.com,https://your-admin.com

# Performance Settings
CACHE_ENABLED=true
CACHE_TTL_STATES=300
CACHE_TTL_SERVICES=600
CACHE_TTL_CONFIG=1800
CONNECTION_POOL_SIZE=20
REQUEST_TIMEOUT=30

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECKS=true
HEALTH_CHECK_INTERVAL=30
```

### Scaling Configuration

#### Horizontal Scaling

```bash
# Load Balancer Configuration
LOAD_BALANCER_ALGORITHM=round_robin
HEALTH_CHECK_PATH=/health
HEALTH_CHECK_INTERVAL=10
HEALTH_CHECK_TIMEOUT=5

# Session Affinity (if needed)
SESSION_AFFINITY=false
STICKY_SESSIONS=false

# Auto-scaling Configuration
MIN_INSTANCES=2
MAX_INSTANCES=10
SCALE_UP_THRESHOLD=80
SCALE_DOWN_THRESHOLD=20
```

#### Vertical Scaling

```bash
# Resource Limits
CPU_LIMIT=2000m
MEMORY_LIMIT=2Gi
CPU_REQUEST=500m
MEMORY_REQUEST=512Mi

# JVM Settings (if using Java components)
JAVA_OPTS=-Xmx1g -Xms512m -XX:+UseG1GC
```

## Docker Production Configuration

### Dockerfile Optimizations

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r ha-bridge && useradd -r -g ha-bridge ha-bridge

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

# Set ownership and permissions
RUN chown -R ha-bridge:ha-bridge /app
USER ha-bridge

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["python", "start.py"]
```

### Docker Compose Production

```yaml
version: "3.8"

services:
  ha-bridge:
    build: .
    ports:
      - "8000:8000"
    environment:
      - HA_BASE_URL=${HA_BASE_URL}
      - HA_API_KEY=${HA_API_KEY}
      - BRIDGE_API_KEY=${BRIDGE_API_KEY}
      - BRIDGE_LOG_LEVEL=INFO
      - ENABLE_RATE_LIMITING=true
      - CACHE_ENABLED=true
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ha-bridge
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
      - "--web.enable-lifecycle"
    restart: unless-stopped

volumes:
  prometheus_data:
```

## Kubernetes Production Configuration

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-bridge
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
          image: ha-bridge:latest
          ports:
            - containerPort: 8000
          env:
            - name: HA_BASE_URL
              valueFrom:
                secretKeyRef:
                  name: ha-bridge-secrets
                  key: ha-base-url
            - name: HA_API_KEY
              valueFrom:
                secretKeyRef:
                  name: ha-bridge-secrets
                  key: ha-api-key
            - name: BRIDGE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: ha-bridge-secrets
                  key: bridge-api-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
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
      restartPolicy: Always
---
apiVersion: v1
kind: Service
metadata:
  name: ha-bridge-service
spec:
  selector:
    app: ha-bridge
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: Secret
metadata:
  name: ha-bridge-secrets
type: Opaque
data:
  ha-base-url: <base64-encoded-url>
  ha-api-key: <base64-encoded-key>
  bridge-api-key: <base64-encoded-key>
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ha-bridge-hpa
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

## Performance Tuning

### Cache Optimization

```python
# Production cache settings
CACHE_SETTINGS = {
    "states": {
        "ttl": 300,  # 5 minutes
        "max_size": 10000,
        "eviction_policy": "lru"
    },
    "services": {
        "ttl": 600,  # 10 minutes
        "max_size": 1000,
        "eviction_policy": "lru"
    },
    "config": {
        "ttl": 1800,  # 30 minutes
        "max_size": 100,
        "eviction_policy": "lru"
    }
}
```

### Connection Pooling

```python
# Production connection settings
CONNECTION_SETTINGS = {
    "pool_size": 20,
    "max_connections": 100,
    "timeout": 30,
    "retry_attempts": 3,
    "backoff_factor": 2
}
```

### Rate Limiting

```python
# Production rate limiting
RATE_LIMIT_SETTINGS = {
    "requests_per_minute": 1000,
    "burst_size": 100,
    "window_size": 60,
    "enabled": True
}
```

## Monitoring and Alerting

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "ha-bridge-rules.yml"

scrape_configs:
  - job_name: "ha-bridge"
    static_configs:
      - targets: ["ha-bridge:8000"]
    metrics_path: /metrics
    scrape_interval: 5s
    scrape_timeout: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

### Alert Rules

```yaml
# ha-bridge-rules.yml
groups:
  - name: ha-bridge
    rules:
      - alert: HighErrorRate
        expr: ha_bridge_error_rate > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} for 5 minutes"

      - alert: HighResponseTime
        expr: ha_bridge_request_duration_seconds > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "Response time is {{ $value }}s for 2 minutes"

      - alert: ServiceDown
        expr: up{job="ha-bridge"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "HA Bridge service is down"
          description: "Service has been down for more than 1 minute"
```

## Security Hardening

### Network Security

```bash
# Firewall rules
ufw allow 8000/tcp
ufw allow 9090/tcp
ufw deny 22/tcp  # Disable SSH if not needed
ufw enable

# SSL/TLS Configuration
SSL_CERT_PATH=/etc/ssl/certs/ha-bridge.crt
SSL_KEY_PATH=/etc/ssl/private/ha-bridge.key
SSL_VERIFY_CLIENT=false
SSL_CIPHERS=ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256
```

### Application Security

```python
# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}
```

## Backup and Recovery

### Data Backup

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ha-bridge"
mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /app/logs

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Disaster Recovery

```bash
#!/bin/bash
# restore.sh
BACKUP_FILE=$1
BACKUP_DIR="/backups/ha-bridge"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop service
systemctl stop ha-bridge

# Restore configuration
tar -xzf $BACKUP_DIR/$BACKUP_FILE -C /

# Start service
systemctl start ha-bridge
```

## Troubleshooting Production Issues

### Common Issues

1. **High Memory Usage**

   - Check cache size limits
   - Monitor for memory leaks
   - Adjust garbage collection settings

2. **Slow Response Times**

   - Check Home Assistant server performance
   - Verify network connectivity
   - Review cache hit rates

3. **Connection Failures**
   - Check SSL certificates
   - Verify API key validity
   - Monitor network connectivity

### Performance Monitoring

```bash
# Monitor resource usage
htop
iostat -x 1
netstat -tuln

# Check service logs
tail -f /app/logs/service.log
journalctl -u ha-bridge -f
```

## Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Monitoring setup complete
- [ ] Backup procedures tested
- [ ] Load balancer configured
- [ ] Auto-scaling configured
- [ ] Security headers enabled
- [ ] Rate limiting enabled
- [ ] Health checks configured
- [ ] Log aggregation setup
- [ ] Alerting configured
- [ ] Disaster recovery tested
- [ ] Performance benchmarks met
- [ ] Security audit completed
