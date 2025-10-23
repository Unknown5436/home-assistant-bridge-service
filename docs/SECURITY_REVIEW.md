# Home Assistant Bridge Service - Security Review & Hardening Guide

## Table of Contents

1. [Security Assessment Overview](#security-assessment-overview)
2. [Current Security Measures](#current-security-measures)
3. [API Key Management](#api-key-management)
4. [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
5. [Input Validation & Sanitization](#input-validation--sanitization)
6. [HTTPS & TLS Configuration](#https--tls-configuration)
7. [Dependency Security](#dependency-security)
8. [Secrets Management](#secrets-management)
9. [Network Security](#network-security)
10. [Audit Logging](#audit-logging)
11. [Incident Response](#incident-response)
12. [Security Testing](#security-testing)
13. [Compliance Considerations](#compliance-considerations)
14. [Security Hardening Checklist](#security-hardening-checklist)

## Security Assessment Overview

### Security Posture Summary

**Overall Security Rating: B+ (Good)**

The Home Assistant Bridge Service implements solid security fundamentals with room for enhancement in advanced security features.

### Key Security Strengths

- ✅ **API Key Authentication**: Multi-key support with Bearer token validation
- ✅ **Rate Limiting**: Per-API-key and per-IP rate limiting
- ✅ **Input Validation**: Pydantic models for request validation
- ✅ **Error Handling**: No sensitive data exposure in error responses
- ✅ **Structured Logging**: Comprehensive audit logging
- ✅ **CORS Protection**: Configurable cross-origin resource sharing

### Areas for Improvement

- ⚠️ **HTTPS Enforcement**: Currently optional, should be mandatory in production
- ⚠️ **Secrets Management**: Basic .env file approach needs enhancement
- ⚠️ **Dependency Scanning**: No automated vulnerability scanning
- ⚠️ **Security Headers**: Missing security headers (CSP, HSTS, etc.)
- ⚠️ **Session Management**: No session timeout or invalidation

## Current Security Measures

### Authentication System

```python
# Current implementation in app/auth/middleware.py
class APIKeyAuth:
    def __init__(self, api_keys: List[str]):
        self.api_keys = set(api_keys)
    
    async def __call__(self, request: Request, call_next):
        # Extract API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        # Add API key to request state for logging
        request.state.api_key = api_key
        return await call_next(request)
```

**Security Analysis:**
- ✅ **Strong**: Bearer token format prevents key leakage in URLs
- ✅ **Strong**: Multiple API key support enables key rotation
- ⚠️ **Weak**: No key expiration or rotation mechanism
- ⚠️ **Weak**: No key usage tracking or monitoring

### Rate Limiting Implementation

```python
# Current implementation
class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)
    
    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        api_key = getattr(request.state, 'api_key', None)
        
        # Rate limit by IP and API key
        if not self._check_rate_limit(client_ip, api_key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        return await call_next(request)
```

**Security Analysis:**
- ✅ **Strong**: Dual rate limiting (IP + API key)
- ✅ **Strong**: Configurable limits
- ⚠️ **Weak**: In-memory storage (lost on restart)
- ⚠️ **Weak**: No distributed rate limiting for multi-instance deployments

### Input Validation

```python
# Pydantic models for validation
class StateRequest(BaseModel):
    state: str
    attributes: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"  # Reject extra fields

class ServiceCallRequest(BaseModel):
    entity_id: Optional[str] = None
    service_data: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"
```

**Security Analysis:**
- ✅ **Strong**: Pydantic validation prevents injection attacks
- ✅ **Strong**: Extra field rejection prevents parameter pollution
- ✅ **Strong**: Type validation prevents type confusion attacks
- ⚠️ **Weak**: No custom validation rules for specific fields

## API Key Management

### Current Implementation

```bash
# .env file
API_KEYS=["test-api-key-12345","jz6dpr1Xr7fi0x8TZ8AFo_PuKSkYORQB_X1VKyFAmF8","L2z5O5eWDgB4FBQ1RWu-IXpeTHQO0STj1fltE4Rx_-o"]
```

### Security Issues

1. **Plain Text Storage**: API keys stored in plain text
2. **No Expiration**: Keys never expire
3. **No Rotation**: No mechanism for key rotation
4. **No Monitoring**: No tracking of key usage
5. **Version Control Risk**: Keys could be committed to git

### Recommended Improvements

#### 1. Key Rotation System

```python
# Enhanced API key management
class APIKeyManager:
    def __init__(self):
        self.keys = {}
        self.key_history = []
    
    def generate_key(self, name: str, expires_in_days: int = 90):
        """Generate a new API key with expiration."""
        key_id = str(uuid.uuid4())
        key_value = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        self.keys[key_id] = {
            'name': name,
            'value': key_value,
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'last_used': None,
            'usage_count': 0,
            'active': True
        }
        
        return key_id, key_value
    
    def validate_key(self, key_value: str) -> bool:
        """Validate API key and update usage stats."""
        for key_id, key_data in self.keys.items():
            if key_data['value'] == key_value and key_data['active']:
                if datetime.now() > key_data['expires_at']:
                    self._deactivate_key(key_id)
                    return False
                
                # Update usage stats
                key_data['last_used'] = datetime.now()
                key_data['usage_count'] += 1
                return True
        
        return False
    
    def rotate_key(self, key_id: str) -> str:
        """Rotate an existing API key."""
        if key_id not in self.keys:
            raise ValueError("Key not found")
        
        old_key = self.keys[key_id]['value']
        new_key_value = secrets.token_urlsafe(32)
        
        # Archive old key
        self.key_history.append({
            'key_id': key_id,
            'old_value': old_key,
            'rotated_at': datetime.now()
        })
        
        # Update with new key
        self.keys[key_id]['value'] = new_key_value
        self.keys[key_id]['created_at'] = datetime.now()
        
        return new_key_value
```

#### 2. Secure Key Storage

```python
# Use external secret management
import boto3
from azure.keyvault.secrets import SecretClient

class SecureKeyManager:
    def __init__(self, provider: str = "aws"):
        if provider == "aws":
            self.client = boto3.client('secretsmanager')
        elif provider == "azure":
            self.client = SecretClient(vault_url="https://your-vault.vault.azure.net/")
    
    def get_api_keys(self) -> List[str]:
        """Retrieve API keys from secure storage."""
        if self.provider == "aws":
            response = self.client.get_secret_value(SecretId='ha-bridge-api-keys')
            return json.loads(response['SecretString'])
        elif self.provider == "azure":
            secret = self.client.get_secret("ha-bridge-api-keys")
            return json.loads(secret.value)
```

#### 3. Key Monitoring

```python
# API key usage monitoring
class KeyMonitor:
    def __init__(self):
        self.usage_stats = defaultdict(list)
        self.suspicious_activity = []
    
    def log_key_usage(self, key_id: str, request: Request):
        """Log API key usage for monitoring."""
        usage = {
            'timestamp': datetime.now(),
            'ip': request.client.host,
            'user_agent': request.headers.get('User-Agent'),
            'endpoint': str(request.url),
            'method': request.method
        }
        
        self.usage_stats[key_id].append(usage)
        
        # Check for suspicious activity
        self._check_suspicious_activity(key_id, usage)
    
    def _check_suspicious_activity(self, key_id: str, usage: dict):
        """Detect suspicious API key usage patterns."""
        recent_usage = [u for u in self.usage_stats[key_id] 
                        if datetime.now() - u['timestamp'] < timedelta(hours=1)]
        
        # Check for rapid requests from different IPs
        unique_ips = set(u['ip'] for u in recent_usage)
        if len(unique_ips) > 5:
            self.suspicious_activity.append({
                'key_id': key_id,
                'type': 'multiple_ips',
                'timestamp': datetime.now(),
                'details': f"Key used from {len(unique_ips)} different IPs"
            })
        
        # Check for unusual user agents
        user_agents = [u['user_agent'] for u in recent_usage]
        if any('bot' in ua.lower() for ua in user_agents if ua):
            self.suspicious_activity.append({
                'key_id': key_id,
                'type': 'bot_usage',
                'timestamp': datetime.now(),
                'details': "Bot-like user agent detected"
            })
```

## Rate Limiting & DDoS Protection

### Current Implementation Analysis

```python
# Current rate limiter limitations
class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)  # In-memory storage
```

### Enhanced Rate Limiting

#### 1. Distributed Rate Limiting

```python
# Redis-based distributed rate limiting
import redis
import time

class DistributedRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_limits = {
            'requests': 100,
            'window': 60,
            'burst': 20
        }
    
    async def check_rate_limit(self, identifier: str, limits: dict = None) -> bool:
        """Check if request is within rate limits."""
        limits = limits or self.default_limits
        key = f"rate_limit:{identifier}"
        
        # Use sliding window algorithm
        now = time.time()
        window_start = now - limits['window']
        
        # Remove old entries
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_requests = self.redis.zcard(key)
        
        if current_requests >= limits['requests']:
            return False
        
        # Add current request
        self.redis.zadd(key, {str(now): now})
        self.redis.expire(key, limits['window'])
        
        return True
    
    async def get_rate_limit_info(self, identifier: str) -> dict:
        """Get current rate limit status."""
        key = f"rate_limit:{identifier}"
        current_requests = self.redis.zcard(key)
        
        return {
            'current_requests': current_requests,
            'limit': self.default_limits['requests'],
            'window': self.default_limits['window'],
            'remaining': max(0, self.default_limits['requests'] - current_requests)
        }
```

#### 2. Advanced DDoS Protection

```python
# DDoS protection with multiple strategies
class DDoSProtection:
    def __init__(self):
        self.ip_blacklist = set()
        self.suspicious_ips = defaultdict(list)
        self.challenge_required = set()
    
    async def check_ddos_protection(self, request: Request) -> bool:
        """Check if request should be blocked due to DDoS."""
        client_ip = request.client.host
        
        # Check blacklist
        if client_ip in self.ip_blacklist:
            return False
        
        # Check for rapid requests
        now = time.time()
        self.suspicious_ips[client_ip].append(now)
        
        # Keep only recent requests
        self.suspicious_ips[client_ip] = [
            req_time for req_time in self.suspicious_ips[client_ip]
            if now - req_time < 300  # 5 minutes
        ]
        
        # Check for suspicious patterns
        if len(self.suspicious_ips[client_ip]) > 100:
            self.ip_blacklist.add(client_ip)
            return False
        
        # Check for challenge requirement
        if client_ip in self.challenge_required:
            return await self._verify_challenge(request)
        
        return True
    
    async def _verify_challenge(self, request: Request) -> bool:
        """Verify challenge response for suspicious IPs."""
        challenge_token = request.headers.get('X-Challenge-Token')
        if not challenge_token:
            return False
        
        # Verify challenge token (implement your challenge system)
        return self._validate_challenge_token(challenge_token)
```

## Input Validation & Sanitization

### Enhanced Validation Rules

```python
# Enhanced input validation
from pydantic import BaseModel, validator, Field
import re

class SecureStateRequest(BaseModel):
    state: str = Field(..., min_length=1, max_length=100)
    attributes: Optional[Dict[str, Any]] = Field(None, max_items=50)
    
    @validator('state')
    def validate_state(cls, v):
        # Only allow alphanumeric characters and common symbols
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError('State contains invalid characters')
        return v.strip()
    
    @validator('attributes')
    def validate_attributes(cls, v):
        if v is None:
            return v
        
        # Limit attribute values
        for key, value in v.items():
            if len(str(value)) > 1000:
                raise ValueError(f'Attribute {key} value too long')
            
            # Prevent script injection
            if isinstance(value, str) and any(tag in value.lower() for tag in ['<script', '<iframe', 'javascript:']):
                raise ValueError(f'Attribute {key} contains potentially malicious content')
        
        return v

class SecureServiceCallRequest(BaseModel):
    entity_id: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$')
    service_data: Optional[Dict[str, Any]] = Field(None, max_items=20)
    
    @validator('entity_id')
    def validate_entity_id(cls, v):
        if v is None:
            return v
        
        # Validate entity ID format
        if not re.match(r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$', v):
            raise ValueError('Invalid entity ID format')
        
        # Check for common injection patterns
        if any(pattern in v.lower() for pattern in ['../', '..\\', 'script:', 'javascript:']):
            raise ValueError('Entity ID contains potentially malicious content')
        
        return v
```

### SQL Injection Prevention

```python
# Ensure all database queries use parameterized statements
class SecureDatabaseClient:
    def __init__(self, connection_string: str):
        self.connection = create_connection(connection_string)
    
    def get_entity_state(self, entity_id: str) -> dict:
        """Get entity state using parameterized query."""
        # CORRECT: Parameterized query
        query = "SELECT * FROM entity_states WHERE entity_id = ?"
        result = self.connection.execute(query, (entity_id,))
        
        # INCORRECT: String concatenation (vulnerable to SQL injection)
        # query = f"SELECT * FROM entity_states WHERE entity_id = '{entity_id}'"
        
        return result.fetchone()
```

## HTTPS & TLS Configuration

### Current Status

The service currently supports HTTP and HTTPS but doesn't enforce HTTPS in production.

### HTTPS Enforcement

```python
# HTTPS enforcement middleware
from fastapi import Request, HTTPException
import ssl

class HTTPSEnforcementMiddleware:
    def __init__(self, enforce_https: bool = True):
        self.enforce_https = enforce_https
    
    async def __call__(self, request: Request, call_next):
        if self.enforce_https:
            # Check if request is over HTTPS
            if request.url.scheme != 'https':
                # Check for X-Forwarded-Proto header (for load balancers)
                forwarded_proto = request.headers.get('X-Forwarded-Proto')
                if forwarded_proto != 'https':
                    raise HTTPException(
                        status_code=426,
                        detail="HTTPS required. Please use HTTPS to access this service."
                    )
        
        # Add security headers
        response = await call_next(request)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
```

### TLS Configuration

```python
# Secure TLS configuration
import ssl

def create_ssl_context() -> ssl.SSLContext:
    """Create secure SSL context."""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Disable weak protocols
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Disable weak ciphers
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    
    # Enable certificate verification
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    
    return context

# Use in uvicorn
if __name__ == "__main__":
    ssl_context = create_ssl_context()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        ssl_context=ssl_context
    )
```

## Dependency Security

### Vulnerability Scanning

```bash
# Install security scanning tools
pip install safety bandit

# Scan for known vulnerabilities
safety check

# Scan for security issues in code
bandit -r app/

# Scan dependencies
pip-audit
```

### Dependency Management

```python
# requirements.txt with version pinning
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
pydantic==2.5.0
structlog==23.2.0
python-dotenv==1.0.0
prometheus-client==0.19.0
redis==5.0.1
```

### Automated Security Updates

```yaml
# GitHub Actions security workflow
name: Security Scan
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install safety bandit pip-audit
      
      - name: Run safety check
        run: safety check
      
      - name: Run bandit
        run: bandit -r app/
      
      - name: Run pip-audit
        run: pip-audit
      
      - name: Check for updates
        run: pip-audit --desc
```

## Secrets Management

### Current Issues

1. **Plain Text Storage**: Secrets in .env files
2. **Version Control Risk**: Secrets could be committed
3. **No Rotation**: No mechanism for secret rotation
4. **No Encryption**: Secrets not encrypted at rest

### Recommended Solutions

#### 1. Environment-Based Secrets

```bash
# Production environment variables
export HA_TOKEN=$(aws secretsmanager get-secret-value --secret-id ha-bridge-token --query SecretString --output text)
export API_KEYS=$(aws secretsmanager get-secret-value --secret-id ha-bridge-api-keys --query SecretString --output text)
```

#### 2. Kubernetes Secrets

```yaml
# kubernetes-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ha-bridge-secrets
type: Opaque
data:
  ha-token: <base64-encoded-token>
  api-keys: <base64-encoded-json>
```

#### 3. HashiCorp Vault Integration

```python
# Vault integration
import hvac

class VaultSecretManager:
    def __init__(self, vault_url: str, token: str):
        self.client = hvac.Client(url=vault_url, token=token)
    
    def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    
    def rotate_secret(self, path: str) -> str:
        """Rotate secret in Vault."""
        new_secret = secrets.token_urlsafe(32)
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret={'value': new_secret}
        )
        return new_secret
```

## Network Security

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # HA Bridge Service
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Network Policies (Kubernetes)

```yaml
# network-policy.yaml
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
      port: 443    # HTTPS to Home Assistant
    - protocol: TCP
      port: 8123  # Home Assistant API
```

### Load Balancer Security

```yaml
# nginx.conf with security headers
server {
    listen 443 ssl http2;
    server_name ha-bridge.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/ha-bridge.crt;
    ssl_certificate_key /etc/ssl/private/ha-bridge.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://ha-bridge-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Audit Logging

### Current Logging Implementation

```python
# Current structured logging
import structlog

logger = structlog.get_logger()

# Log API requests
logger.info(
    "API request",
    method=request.method,
    url=str(request.url),
    client_ip=request.client.host,
    api_key=getattr(request.state, 'api_key', None)[:8] + "...",  # Masked
    user_agent=request.headers.get('User-Agent')
)
```

### Enhanced Audit Logging

```python
# Enhanced audit logging
class SecurityAuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger("security_audit")
    
    def log_authentication_attempt(self, request: Request, success: bool):
        """Log authentication attempts."""
        self.logger.info(
            "Authentication attempt",
            event_type="auth_attempt",
            success=success,
            client_ip=request.client.host,
            user_agent=request.headers.get('User-Agent'),
            timestamp=datetime.now().isoformat(),
            api_key_hash=hashlib.sha256(
                request.headers.get('Authorization', '').encode()
            ).hexdigest()[:16]
        )
    
    def log_rate_limit_exceeded(self, request: Request, limit_type: str):
        """Log rate limit violations."""
        self.logger.warning(
            "Rate limit exceeded",
            event_type="rate_limit_exceeded",
            limit_type=limit_type,
            client_ip=request.client.host,
            endpoint=str(request.url),
            timestamp=datetime.now().isoformat()
        )
    
    def log_suspicious_activity(self, request: Request, activity_type: str, details: str):
        """Log suspicious activity."""
        self.logger.error(
            "Suspicious activity detected",
            event_type="suspicious_activity",
            activity_type=activity_type,
            details=details,
            client_ip=request.client.host,
            endpoint=str(request.url),
            timestamp=datetime.now().isoformat()
        )
```

### Log Analysis

```python
# Log analysis for security monitoring
class SecurityLogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
    
    def analyze_failed_logins(self, hours: int = 24) -> dict:
        """Analyze failed login attempts."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        failed_logins = []
        with open(self.log_file, 'r') as f:
            for line in f:
                log_entry = json.loads(line)
                if (log_entry.get('event_type') == 'auth_attempt' and 
                    not log_entry.get('success', True) and
                    datetime.fromisoformat(log_entry['timestamp']) > cutoff_time):
                    failed_logins.append(log_entry)
        
        # Group by IP
        ip_counts = defaultdict(int)
        for login in failed_logins:
            ip_counts[login['client_ip']] += 1
        
        return {
            'total_failed': len(failed_logins),
            'unique_ips': len(ip_counts),
            'top_offending_ips': sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def detect_brute_force_attacks(self) -> List[dict]:
        """Detect potential brute force attacks."""
        attacks = []
        ip_counts = defaultdict(list)
        
        with open(self.log_file, 'r') as f:
            for line in f:
                log_entry = json.loads(line)
                if log_entry.get('event_type') == 'auth_attempt':
                    ip_counts[log_entry['client_ip']].append(
                        datetime.fromisoformat(log_entry['timestamp'])
                    )
        
        # Check for rapid failed attempts
        for ip, timestamps in ip_counts.items():
            recent_failures = [
                ts for ts in timestamps 
                if datetime.now() - ts < timedelta(minutes=15)
            ]
            
            if len(recent_failures) > 10:
                attacks.append({
                    'ip': ip,
                    'attempts': len(recent_failures),
                    'timeframe': '15 minutes'
                })
        
        return attacks
```

## Incident Response

### Incident Response Plan

#### 1. Detection

```python
# Automated threat detection
class ThreatDetector:
    def __init__(self):
        self.threat_rules = [
            self._detect_brute_force,
            self._detect_sql_injection,
            self._detect_xss_attempts,
            self._detect_ddos_attacks
        ]
    
    async def analyze_request(self, request: Request) -> List[str]:
        """Analyze request for threats."""
        threats = []
        
        for rule in self.threat_rules:
            threat = await rule(request)
            if threat:
                threats.append(threat)
        
        return threats
    
    async def _detect_brute_force(self, request: Request) -> Optional[str]:
        """Detect brute force attacks."""
        # Implementation for brute force detection
        pass
    
    async def _detect_sql_injection(self, request: Request) -> Optional[str]:
        """Detect SQL injection attempts."""
        sql_patterns = [
            r"union\s+select",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from",
            r"update\s+set"
        ]
        
        request_str = str(request.url) + str(request.query_params)
        for pattern in sql_patterns:
            if re.search(pattern, request_str, re.IGNORECASE):
                return f"SQL injection attempt detected: {pattern}"
        
        return None
```

#### 2. Response Actions

```python
# Automated response actions
class IncidentResponder:
    def __init__(self):
        self.response_actions = {
            'brute_force': self._block_ip,
            'sql_injection': self._block_ip,
            'xss_attempt': self._rate_limit_ip,
            'ddos_attack': self._enable_challenge
        }
    
    async def respond_to_threat(self, threat_type: str, request: Request):
        """Respond to detected threat."""
        if threat_type in self.response_actions:
            await self.response_actions[threat_type](request)
    
    async def _block_ip(self, request: Request):
        """Block IP address."""
        client_ip = request.client.host
        # Add to blacklist
        # Log the action
        # Notify administrators
    
    async def _rate_limit_ip(self, request: Request):
        """Apply stricter rate limiting."""
        client_ip = request.client.host
        # Apply stricter rate limits
        # Log the action
    
    async def _enable_challenge(self, request: Request):
        """Enable challenge for IP."""
        client_ip = request.client.host
        # Require CAPTCHA or other challenge
        # Log the action
```

#### 3. Notification System

```python
# Incident notification system
class IncidentNotifier:
    def __init__(self):
        self.notification_channels = [
            self._send_email,
            self._send_slack_message,
            self._create_ticket
        ]
    
    async def notify_incident(self, incident: dict):
        """Notify about security incident."""
        for channel in self.notification_channels:
            try:
                await channel(incident)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.__name__}: {e}")
    
    async def _send_email(self, incident: dict):
        """Send email notification."""
        # Email implementation
        pass
    
    async def _send_slack_message(self, incident: dict):
        """Send Slack notification."""
        # Slack implementation
        pass
    
    async def _create_ticket(self, incident: dict):
        """Create support ticket."""
        # Ticket system implementation
        pass
```

## Security Testing

### Automated Security Testing

```python
# Security test suite
import pytest
from fastapi.testclient import TestClient

class SecurityTestSuite:
    def __init__(self, client: TestClient):
        self.client = client
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in malicious_payloads:
            response = self.client.get(f"/api/v1/states/{payload}")
            assert response.status_code in [400, 404, 422]  # Should not be 200
    
    def test_xss_protection(self):
        """Test XSS protection."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
        for payload in xss_payloads:
            response = self.client.post(
                "/api/v1/states/test_entity",
                json={"state": payload}
            )
            assert response.status_code in [400, 422]  # Should be rejected
    
    def test_rate_limiting(self):
        """Test rate limiting."""
        # Make rapid requests
        for i in range(150):  # Exceed rate limit
            response = self.client.get("/api/v1/states/all")
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
    
    def test_authentication_bypass(self):
        """Test authentication bypass attempts."""
        bypass_attempts = [
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Bearer invalid-token"},  # Invalid token
            {"X-API-Key": "valid-key"},  # Wrong header
            {},  # No auth header
        ]
        
        for headers in bypass_attempts:
            response = self.client.get("/api/v1/states/all", headers=headers)
            assert response.status_code == 401
    
    def test_cors_protection(self):
        """Test CORS protection."""
        response = self.client.options(
            "/api/v1/states/all",
            headers={"Origin": "https://malicious-site.com"}
        )
        # Should not allow cross-origin requests from untrusted domains
        assert "Access-Control-Allow-Origin" not in response.headers
```

### Penetration Testing

```bash
# OWASP ZAP automated scanning
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000

# Nmap security scan
nmap -sS -O -sV -sC -p 8000 localhost

# Nikto web vulnerability scanner
nikto -h http://localhost:8000
```

## Compliance Considerations

### GDPR Compliance

```python
# GDPR compliance features
class GDPRCompliance:
    def __init__(self):
        self.data_retention_days = 30
        self.audit_log = []
    
    def log_data_access(self, user_id: str, data_type: str, purpose: str):
        """Log data access for GDPR compliance."""
        self.audit_log.append({
            'timestamp': datetime.now(),
            'user_id': user_id,
            'data_type': data_type,
            'purpose': purpose,
            'legal_basis': 'legitimate_interest'
        })
    
    def anonymize_user_data(self, user_id: str):
        """Anonymize user data for GDPR compliance."""
        # Remove or anonymize personal data
        pass
    
    def export_user_data(self, user_id: str) -> dict:
        """Export user data for GDPR compliance."""
        # Return all data associated with user
        pass
    
    def delete_user_data(self, user_id: str):
        """Delete user data for GDPR compliance."""
        # Permanently delete user data
        pass
```

### SOC 2 Compliance

```python
# SOC 2 compliance features
class SOC2Compliance:
    def __init__(self):
        self.access_logs = []
        self.change_logs = []
    
    def log_access(self, user: str, resource: str, action: str):
        """Log access for SOC 2 compliance."""
        self.access_logs.append({
            'timestamp': datetime.now(),
            'user': user,
            'resource': resource,
            'action': action,
            'result': 'success'
        })
    
    def log_change(self, user: str, change_type: str, details: str):
        """Log changes for SOC 2 compliance."""
        self.change_logs.append({
            'timestamp': datetime.now(),
            'user': user,
            'change_type': change_type,
            'details': details
        })
    
    def generate_compliance_report(self) -> dict:
        """Generate SOC 2 compliance report."""
        return {
            'access_logs': len(self.access_logs),
            'change_logs': len(self.change_logs),
            'last_audit': datetime.now(),
            'compliance_status': 'compliant'
        }
```

## Security Hardening Checklist

### ✅ Immediate Actions (High Priority)

- [ ] **Enable HTTPS enforcement** in production
- [ ] **Implement API key rotation** mechanism
- [ ] **Add security headers** (HSTS, CSP, X-Frame-Options)
- [ ] **Enable dependency vulnerability scanning**
- [ ] **Implement secrets management** (Vault/AWS Secrets Manager)
- [ ] **Add comprehensive audit logging**
- [ ] **Implement rate limiting** with Redis backend
- [ ] **Add input validation** for all endpoints
- [ ] **Enable automated security testing** in CI/CD
- [ ] **Implement network policies** (Kubernetes)

### ⚠️ Medium Priority Actions

- [ ] **Add DDoS protection** with challenge system
- [ ] **Implement threat detection** and automated response
- [ ] **Add security monitoring** and alerting
- [ ] **Implement session management** with timeouts
- [ ] **Add file upload validation** (if applicable)
- [ ] **Implement backup encryption**
- [ ] **Add security incident response** procedures
- [ ] **Implement compliance reporting** (GDPR/SOC2)
- [ ] **Add security training** for developers
- [ ] **Implement security code review** process

### 📋 Long-term Actions (Lower Priority)

- [ ] **Implement zero-trust architecture**
- [ ] **Add advanced threat detection** (ML-based)
- [ ] **Implement security orchestration** (SOAR)
- [ ] **Add compliance automation** tools
- [ ] **Implement security metrics** dashboard
- [ ] **Add penetration testing** schedule
- [ ] **Implement security awareness** program
- [ ] **Add security architecture** review
- [ ] **Implement security governance** framework
- [ ] **Add security risk assessment** process

### 🔒 Security Configuration Examples

#### Production Security Configuration

```bash
# .env.prod.security
# HTTPS enforcement
HTTPS_ENFORCED=true
SSL_CERT_PATH=/etc/ssl/certs/ha-bridge.crt
SSL_KEY_PATH=/etc/ssl/private/ha-bridge.key

# Security headers
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
CSP_POLICY="default-src 'self'; script-src 'self' 'unsafe-inline'"

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BACKEND=redis

# Audit logging
AUDIT_LOGGING_ENABLED=true
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_RETENTION_DAYS=90

# Security monitoring
SECURITY_MONITORING_ENABLED=true
THREAT_DETECTION_ENABLED=true
INCIDENT_RESPONSE_ENABLED=true

# Compliance
GDPR_COMPLIANCE_ENABLED=true
SOC2_COMPLIANCE_ENABLED=true
DATA_RETENTION_DAYS=30
```

This comprehensive security review provides a roadmap for hardening the Home Assistant Bridge Service. The recommendations are prioritized by risk level and implementation complexity, allowing for a phased approach to security improvements.