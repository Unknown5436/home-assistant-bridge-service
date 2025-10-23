# Security Testing Procedures

## Overview

This document outlines comprehensive security testing procedures for the Home Assistant Bridge Service. It covers vulnerability scanning, penetration testing, security validation, and ongoing security monitoring.

## Security Testing Framework

### Testing Categories

1. **Static Application Security Testing (SAST)**
2. **Dynamic Application Security Testing (DAST)**
3. **Dependency Vulnerability Scanning**
4. **Infrastructure Security Testing**
5. **API Security Testing**
6. **Authentication and Authorization Testing**
7. **Data Protection Testing**

## Pre-Testing Setup

### Environment Preparation

```bash
# Create isolated testing environment
docker network create security-test-network
docker run -d --name ha-bridge-test --network security-test-network ha-bridge:test

# Install security testing tools
pip install bandit safety semgrep
npm install -g retire
```

### Test Data Preparation

```bash
# Create test API keys
export TEST_API_KEY="test-security-key-12345"
export TEST_HA_API_KEY="test-ha-key-67890"

# Create test configuration
cat > test-security.env << EOF
HA_BASE_URL=http://test-ha-instance:8123
HA_API_KEY=$TEST_HA_API_KEY
BRIDGE_API_KEY=$TEST_API_KEY
BRIDGE_LOG_LEVEL=DEBUG
ENABLE_RATE_LIMITING=true
EOF
```

## Static Application Security Testing (SAST)

### Code Analysis with Bandit

```bash
# Install bandit
pip install bandit

# Run security analysis
bandit -r app/ -f json -o bandit-report.json
bandit -r app/ -f txt -o bandit-report.txt

# Check for specific security issues
bandit -r app/ -t B101,B102,B103  # SQL injection, hardcoded passwords, etc.
```

### Advanced SAST with Semgrep

```bash
# Install semgrep
pip install semgrep

# Run security rules
semgrep --config=auto app/
semgrep --config=p/security-audit app/
semgrep --config=p/secrets app/

# Custom security rules
semgrep --config=.semgrep-rules.yml app/
```

### Custom Security Rules

```yaml
# .semgrep-rules.yml
rules:
  - id: hardcoded-secrets
    patterns:
      - pattern: |
          $KEY = "..."
          $API_KEY = "..."
          $PASSWORD = "..."
    message: "Hardcoded secret detected"
    severity: ERROR
    languages: [python]

  - id: sql-injection
    patterns:
      - pattern: |
          f"SELECT * FROM {table} WHERE id = {user_input}"
    message: "Potential SQL injection vulnerability"
    severity: ERROR
    languages: [python]

  - id: unsafe-deserialization
    patterns:
      - pattern: |
          pickle.loads($data)
          yaml.load($data)
    message: "Unsafe deserialization detected"
    severity: ERROR
    languages: [python]
```

## Dynamic Application Security Testing (DAST)

### OWASP ZAP Testing

```bash
# Install OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000

# Full scan
docker run -t owasp/zap2docker-stable zap-full-scan.py -t http://localhost:8000

# API scan
docker run -t owasp/zap2docker-stable zap-api-scan.py -t http://localhost:8000 -f openapi
```

### Custom DAST Scripts

```python
#!/usr/bin/env python3
"""
Custom DAST testing script for HA Bridge Service
"""

import requests
import json
import time
from typing import Dict, List

class SecurityTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.vulnerabilities = []

    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]

        for payload in payloads:
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/states/{payload}",
                    headers=self.headers,
                    timeout=5
                )
                if response.status_code == 200 and "error" not in response.text.lower():
                    self.vulnerabilities.append({
                        "type": "SQL Injection",
                        "payload": payload,
                        "response": response.text[:100]
                    })
            except Exception as e:
                print(f"SQL injection test error: {e}")

    def test_xss(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>"
        ]

        for payload in payloads:
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/states/{payload}",
                    headers=self.headers,
                    timeout=5
                )
                if payload in response.text:
                    self.vulnerabilities.append({
                        "type": "XSS",
                        "payload": payload,
                        "response": response.text[:100]
                    })
            except Exception as e:
                print(f"XSS test error: {e}")

    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        # Test without API key
        try:
            response = requests.get(f"{self.base_url}/api/v1/states", timeout=5)
            if response.status_code == 200:
                self.vulnerabilities.append({
                    "type": "Authentication Bypass",
                    "description": "API accessible without authentication"
                })
        except Exception as e:
            print(f"Auth bypass test error: {e}")

        # Test with invalid API key
        try:
            invalid_headers = {"Authorization": "Bearer invalid-key"}
            response = requests.get(
                f"{self.base_url}/api/v1/states",
                headers=invalid_headers,
                timeout=5
            )
            if response.status_code == 200:
                self.vulnerabilities.append({
                    "type": "Authentication Bypass",
                    "description": "API accessible with invalid API key"
                })
        except Exception as e:
            print(f"Invalid key test error: {e}")

    def test_rate_limiting(self):
        """Test rate limiting implementation"""
        requests_sent = 0
        start_time = time.time()

        while time.time() - start_time < 60:  # Test for 1 minute
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/states",
                    headers=self.headers,
                    timeout=5
                )
                requests_sent += 1

                if response.status_code == 429:  # Rate limited
                    print(f"Rate limiting triggered after {requests_sent} requests")
                    break

                time.sleep(0.1)  # 10 requests per second
            except Exception as e:
                print(f"Rate limiting test error: {e}")
                break

        if requests_sent > 1000:  # No rate limiting detected
            self.vulnerabilities.append({
                "type": "Rate Limiting",
                "description": f"No rate limiting detected after {requests_sent} requests"
            })

    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities"""
        endpoints = [
            "/health",
            "/metrics",
            "/docs",
            "/api/v1/states",
            "/api/v1/services"
        ]

        for endpoint in endpoints:
            try:
                # Test without authentication
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    # Check for sensitive information
                    content = response.text.lower()
                    sensitive_patterns = [
                        "password", "secret", "key", "token",
                        "internal", "admin", "debug", "error"
                    ]

                    for pattern in sensitive_patterns:
                        if pattern in content:
                            self.vulnerabilities.append({
                                "type": "Information Disclosure",
                                "endpoint": endpoint,
                                "pattern": pattern
                            })
            except Exception as e:
                print(f"Information disclosure test error: {e}")

    def run_all_tests(self):
        """Run all security tests"""
        print("Starting security testing...")

        self.test_sql_injection()
        self.test_xss()
        self.test_authentication_bypass()
        self.test_rate_limiting()
        self.test_information_disclosure()

        print(f"Security testing completed. Found {len(self.vulnerabilities)} vulnerabilities.")
        return self.vulnerabilities

if __name__ == "__main__":
    tester = SecurityTester("http://localhost:8000", "test-api-key-12345")
    vulnerabilities = tester.run_all_tests()

    # Save results
    with open("security-test-results.json", "w") as f:
        json.dump(vulnerabilities, f, indent=2)
```

## Dependency Vulnerability Scanning

### Python Dependencies

```bash
# Install safety
pip install safety

# Scan for vulnerabilities
safety check --json --output safety-report.json
safety check --full-report

# Check specific requirements file
safety check -r requirements.txt
```

### Container Image Scanning

```bash
# Install Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh

# Scan container image
trivy image ha-bridge:latest
trivy image --format json --output trivy-report.json ha-bridge:latest

# Scan filesystem
trivy fs .
trivy fs --format json --output trivy-fs-report.json .
```

### Node.js Dependencies (if any)

```bash
# Install retire.js
npm install -g retire

# Scan for vulnerabilities
retire --outputformat json --outputpath retire-report.json
```

## API Security Testing

### Authentication Testing

```python
def test_api_authentication():
    """Test API authentication mechanisms"""
    test_cases = [
        {"headers": {}, "expected_status": 401, "description": "No authentication"},
        {"headers": {"Authorization": "Bearer invalid-key"}, "expected_status": 401, "description": "Invalid key"},
        {"headers": {"Authorization": "Bearer test-api-key-12345"}, "expected_status": 200, "description": "Valid key"},
        {"headers": {"X-API-Key": "test-api-key-12345"}, "expected_status": 401, "description": "Wrong header format"},
    ]

    for test_case in test_cases:
        response = requests.get(
            "http://localhost:8000/api/v1/states",
            headers=test_case["headers"],
            timeout=5
        )

        if response.status_code != test_case["expected_status"]:
            print(f"Authentication test failed: {test_case['description']}")
            print(f"Expected: {test_case['expected_status']}, Got: {response.status_code}")
```

### Authorization Testing

```python
def test_api_authorization():
    """Test API authorization mechanisms"""
    # Test access to different endpoints
    endpoints = [
        "/api/v1/states",
        "/api/v1/services",
        "/api/v1/config",
        "/health",
        "/metrics"
    ]

    for endpoint in endpoints:
        response = requests.get(
            f"http://localhost:8000{endpoint}",
            headers={"Authorization": "Bearer test-api-key-12345"},
            timeout=5
        )

        if response.status_code not in [200, 404]:  # 404 is acceptable for non-existent endpoints
            print(f"Authorization test failed for {endpoint}: {response.status_code}")
```

## Infrastructure Security Testing

### Network Security Testing

```bash
# Install nmap
sudo apt-get install nmap

# Scan for open ports
nmap -sS -O localhost

# Check for vulnerable services
nmap --script vuln localhost

# Test SSL/TLS configuration
nmap --script ssl-enum-ciphers -p 443 localhost
```

### Container Security Testing

```bash
# Install Docker Bench Security
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
sudo sh docker-bench-security.sh

# Run container security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image ha-bridge:latest
```

## Data Protection Testing

### Data Encryption Testing

```python
def test_data_encryption():
    """Test data encryption in transit and at rest"""
    # Test HTTPS enforcement
    response = requests.get("http://localhost:8000/api/v1/states", allow_redirects=False)
    if response.status_code != 301:  # Should redirect to HTTPS
        print("HTTPS enforcement not working")

    # Test data in transit
    import ssl
    context = ssl.create_default_context()
    try:
        with context.wrap_socket(socket.socket(), server_hostname="localhost") as s:
            s.connect(("localhost", 443))
            print(f"SSL/TLS version: {s.version()}")
    except Exception as e:
        print(f"SSL/TLS test failed: {e}")
```

### Data Sanitization Testing

```python
def test_data_sanitization():
    """Test data sanitization and validation"""
    malicious_inputs = [
        "<script>alert('XSS')</script>",
        "'; DROP TABLE users; --",
        "../../etc/passwd",
        "{{7*7}}",  # Template injection
        "{{config}}",  # Configuration disclosure
    ]

    for malicious_input in malicious_inputs:
        response = requests.post(
            "http://localhost:8000/api/v1/states",
            json={"entity_id": malicious_input},
            headers={"Authorization": "Bearer test-api-key-12345"},
            timeout=5
        )

        # Check if malicious input is reflected in response
        if malicious_input in response.text:
            print(f"Data sanitization failed for: {malicious_input}")
```

## Security Monitoring and Alerting

### Security Event Monitoring

```python
def setup_security_monitoring():
    """Setup security event monitoring"""
    import logging

    # Configure security logging
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)

    handler = logging.FileHandler('security-events.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

    # Log security events
    security_logger.info("Security monitoring enabled")
    security_logger.warning("Failed authentication attempt")
    security_logger.error("Potential security breach detected")
```

### Automated Security Testing

```bash
#!/bin/bash
# automated-security-test.sh

# Run security tests daily
echo "Starting automated security testing..."

# Run SAST
bandit -r app/ -f json -o daily-bandit-report.json

# Run dependency scan
safety check --json --output daily-safety-report.json

# Run DAST
python security-tester.py > daily-dast-report.txt

# Run container scan
trivy image --format json --output daily-trivy-report.json ha-bridge:latest

# Send alerts if vulnerabilities found
if [ -s daily-bandit-report.json ] || [ -s daily-safety-report.json ]; then
    echo "Security vulnerabilities detected!" | mail -s "Security Alert" admin@company.com
fi

echo "Automated security testing completed."
```

## Security Testing Checklist

### Pre-Deployment Security Testing

- [ ] Static code analysis (SAST) completed
- [ ] Dynamic application testing (DAST) completed
- [ ] Dependency vulnerability scan completed
- [ ] Container image security scan completed
- [ ] API security testing completed
- [ ] Authentication and authorization testing completed
- [ ] Data protection testing completed
- [ ] Infrastructure security testing completed
- [ ] Security monitoring configured
- [ ] Incident response procedures tested

### Ongoing Security Testing

- [ ] Daily automated security scans
- [ ] Weekly manual security reviews
- [ ] Monthly penetration testing
- [ ] Quarterly security audits
- [ ] Annual security assessment
- [ ] Continuous vulnerability monitoring
- [ ] Security event logging and alerting
- [ ] Regular security training and updates

## Security Testing Tools

### Recommended Tools

1. **SAST Tools**

   - Bandit (Python)
   - Semgrep (Multi-language)
   - SonarQube (Enterprise)

2. **DAST Tools**

   - OWASP ZAP
   - Burp Suite
   - Custom scripts

3. **Dependency Scanning**

   - Safety (Python)
   - Trivy (Multi-language)
   - Snyk (Commercial)

4. **Container Security**

   - Trivy
   - Clair
   - Docker Bench Security

5. **Infrastructure Security**
   - Nmap
   - Nessus
   - OpenVAS

## Security Testing Reports

### Report Templates

```json
{
  "security_test_report": {
    "timestamp": "2025-10-23T17:00:00Z",
    "test_type": "comprehensive",
    "vulnerabilities": [
      {
        "severity": "high",
        "type": "SQL Injection",
        "description": "Potential SQL injection vulnerability",
        "location": "app/routes/states.py:45",
        "recommendation": "Use parameterized queries"
      }
    ],
    "summary": {
      "total_vulnerabilities": 1,
      "high_severity": 1,
      "medium_severity": 0,
      "low_severity": 0
    }
  }
}
```

This comprehensive security testing framework ensures the Home Assistant Bridge Service is secure and ready for production deployment.
