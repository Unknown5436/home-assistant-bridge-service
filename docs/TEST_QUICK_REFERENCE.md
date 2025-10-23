# Home Assistant Bridge Service - Test Suite Quick Reference

## Quick Commands

```bash
# Run full test suite (default)
python test_complete_ha_bridge.py

# Run quick tests (~1 minute)
python test_complete_ha_bridge.py quick

# Run stress tests (~10 minutes)
python test_complete_ha_bridge.py stress

# Run integration tests (~3 minutes)
python test_complete_ha_bridge.py integration

# Show help
python test_complete_ha_bridge.py --help
```

## Test Modes Comparison

| Mode            | Duration | Tests         | Use Case         |
| --------------- | -------- | ------------- | ---------------- |
| **quick**       | ~1 min   | Core + Auth   | Daily dev, CI/CD |
| **full**        | ~5 min   | All standard  | Pre-deploy, QA   |
| **stress**      | ~10 min  | Load testing  | Benchmarking     |
| **integration** | ~3 min   | HA validation | After HA updates |

## Expected Output (Success)

```
🚀 HOME ASSISTANT BRIDGE SERVICE - COMPREHENSIVE TEST SUITE
======================================================================
Test Mode: FULL
Base URL: http://127.0.0.1:8000
Start Time: 2025-10-22 20:30:15

======================================================================
🔍 TESTING CORE API ENDPOINTS
======================================================================
✅ Health Check: 200 (0.045s)
✅ API Status: 200 (0.038s)
✅ Service Health Check: 200 (0.042s)
✅ Config Health: 200 (0.156s)
✅ Metrics Endpoint: 200 (0.023s)

======================================================================
🏠 TESTING STATES MANAGEMENT
======================================================================
✅ Get All States: 200 (0.891s)
   📊 entity_count: 1186
✅ Get Specific Entity: 200 (0.123s)
✅ Get Non-existent Entity: 404 (0.087s)

======================================================================
🔧 TESTING SERVICES MANAGEMENT
======================================================================
✅ Get All Services: 200 (0.876s)
   📊 service_count: 127
   📊 domain_count: 34
✅ Get Light Domain Services: 200 (0.134s)
✅ Get Non-existent Domain: 404 (0.089s)

======================================================================
🔐 TESTING AUTHENTICATION & SECURITY
======================================================================
✅ No Authentication: 401 (0.034s)
✅ Invalid API Key: 401 (0.036s)
✅ Valid API Key: 200 (0.867s)
✅ Public Endpoint Access: 200 (0.041s)

======================================================================
⚡ TESTING PERFORMANCE & CACHING
======================================================================
   Request 1: 0.889s
   Request 2: 0.098s
   Request 3: 0.092s
   Request 4: 0.095s
   Request 5: 0.091s
✅ Response Time Performance: 200 (0.273s)
   📊 avg_time: 0.273s
   📊 median_time: 0.095s
   📊 min_time: 0.091s
   📊 max_time: 0.889s
   📊 cache_effective: True

   Testing concurrent requests...
✅ Concurrent Request Handling: 200 (1.234s)
   📊 successful: 10
   📊 total: 10
   📊 time: 1.234s
   📊 avg_per_request: 0.123s

======================================================================
🛡️ TESTING ERROR HANDLING
======================================================================
✅ Non-existent Endpoint: 404 (0.034s)
✅ Invalid Entity ID Format: 404 (0.087s)
✅ Malformed Entity Request: 404 (0.033s)
✅ Method Not Allowed: 405 (0.036s)

======================================================================
🚀 TESTING ADVANCED FEATURES
======================================================================
✅ Prometheus Metrics Format: 200 (0.024s)
   📊 has_prometheus_format: True
✅ WebSocket Status Check: 200 (0.039s)
   📊 websocket_status: connected
✅ Configuration Info: 200 (0.145s)

======================================================================
📊 TEST SUMMARY
======================================================================

Total Tests: 25
✅ Passed: 25
❌ Failed: 0
Success Rate: 100.0%
Duration: 15.45s

⚡ Performance Metrics:
  Average Response Time: 0.234s
  Median Response Time: 0.089s
  P95 Response Time: 0.891s

📋 Results by Category:
  ✅ Core: 5/5 passed (100.0%)
  ✅ States: 3/3 passed (100.0%)
  ✅ Services: 3/3 passed (100.0%)
  ✅ Security: 4/4 passed (100.0%)
  ✅ Performance: 2/2 passed (100.0%)
  ✅ Error Handling: 4/4 passed (100.0%)
  ✅ Advanced: 3/3 passed (100.0%)

======================================================================
🎉 ALL TESTS PASSED! Service is fully operational.
======================================================================

📄 Detailed report saved to: test_reports/test_report_20251022_203030.json
```

## Performance Benchmarks

### Response Times (Reference Hardware: RPi 4)

| Endpoint               | First Request | Cached | P95    |
| ---------------------- | ------------- | ------ | ------ |
| `/health`              | 0.045s        | 0.040s | 0.050s |
| `/api/v1/states/all`   | 0.891s        | 0.095s | 0.950s |
| `/api/v1/services/all` | 0.876s        | 0.089s | 0.920s |
| Specific entity        | 0.123s        | 0.087s | 0.150s |

### Success Criteria

| Metric         | Target | Good    | Acceptable |
| -------------- | ------ | ------- | ---------- |
| Success Rate   | 100%   | ≥99%    | ≥95%       |
| Avg Response   | <0.5s  | <1.0s   | <2.0s      |
| P95 Response   | <1.0s  | <2.0s   | <3.0s      |
| Cache Hit Rate | N/A    | Visible | N/A        |

## Common Test Scenarios

### Pre-Commit Check

```bash
python test_complete_ha_bridge.py quick
```

### Before Deployment

```bash
python test_complete_ha_bridge.py full
```

### After HA Update

```bash
python test_complete_ha_bridge.py integration
```

### Performance Tuning

```bash
python test_complete_ha_bridge.py stress
```

### Troubleshooting

```bash
# Test service is running
curl http://127.0.0.1:8000/health

# Test with authentication
curl -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/services/all

# Check specific entity
curl -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/states/binary_sensor.samba_backup_running
```

## Test Configuration

Edit `test_complete_ha_bridge.py` to customize:

```python
@dataclass
class TestConfig:
    base_url: str = "http://127.0.0.1:8000"        # Bridge URL
    api_key: str = "test-api-key-12345"            # API key
    ha_url: str = "https://your-ha.com:8123"       # HA URL
    ha_token: str = "your-long-lived-token"        # HA token
    timeout: int = 30                               # Timeout (seconds)
    test_mode: str = "full"                         # Test mode
```

## Test Results Interpretation

### ✅ All Tests Pass

Service is production-ready. Deploy with confidence.

### ⚠️ 95-99% Success Rate

Minor issues present. Review failed tests before deploying.

### ❌ <95% Success Rate

Critical issues. Do not deploy. Investigate failures immediately.

## Quick Diagnostics

### Service Not Responding

```bash
# Check if running
curl http://127.0.0.1:8000/health

# Start service
python start.py

# Check port
netstat -an | grep 8000  # Linux/Mac
netstat -an | findstr 8000  # Windows
```

### Authentication Failures

```bash
# Check .env file
cat .env | grep API_KEYS

# Verify environment
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('API_KEYS'))"

# Update test config to match
api_key: str = "your-actual-key"
```

### Home Assistant Unreachable

```bash
# Test HA directly
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/

# Check connectivity
ping your-ha-domain.com

# Verify token
# Go to HA Profile -> Long-Lived Access Tokens
```

### Slow Performance

```bash
# Check cache is enabled
cat .env | grep CACHE_TTL

# Should show: CACHE_TTL=300

# Restart service
python start.py

# Run performance test
python test_complete_ha_bridge.py full
```

## Test Report Files

Each test run generates: `test_reports/test_report_YYYYMMDD_HHMMSS.json`

```json
{
  "timestamp": "2025-10-22T20:30:15",
  "test_mode": "full",
  "statistics": {
    "total_tests": 25,
    "passed": 25,
    "failed": 0,
    "success_rate": 100.0,
    "avg_response_time": 0.234
  },
  "results": [
    /* detailed test results */
  ]
}
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests
  run: python test_complete_ha_bridge.py quick
```

### GitLab CI

```yaml
test:
  script:
    - python test_complete_ha_bridge.py quick
```

### Pre-commit Hook

```bash
#!/bin/bash
python test_complete_ha_bridge.py quick || exit 1
```

## Test Categories Overview

| Category       | Tests | Critical | Description             |
| -------------- | ----- | -------- | ----------------------- |
| Core           | 5     | Yes      | Basic service health    |
| States         | 3     | Yes      | Entity state management |
| Services       | 3     | Yes      | Service calls           |
| Security       | 4     | Yes      | Auth & authorization    |
| Performance    | 2     | No       | Speed & caching         |
| Error Handling | 4     | No       | Graceful failures       |
| Advanced       | 3     | No       | Extra features          |
| Integration    | 3     | No       | HA connectivity         |
| Stress         | 2     | No       | Load testing            |

## Keyboard Shortcuts (when running interactively)

- `Ctrl+C` - Stop tests immediately
- Tests run automatically, no interaction needed

## Environment Variables Reference

Required in `.env`:

```bash
# Home Assistant
HA_URL=https://your-ha-url:8123
HA_TOKEN=your-long-lived-access-token

# API Security
API_KEYS=["test-api-key-12345"]

# Optional
CACHE_TTL=300
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
METRICS_ENABLED=True
WEBSOCKET_ENABLED=True
```

## Useful Commands

```bash
# Install dependencies
pip install httpx

# Run all tests
python test_complete_ha_bridge.py

# Check service manually
curl http://127.0.0.1:8000/health

# View latest test report
cat test_reports/test_report_*.json | jq '.statistics'

# Count entities
curl -s -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/states/all | jq '.count'

# List all domains
curl -s -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/services/all | jq '.services | keys'
```

## Getting Help

- **Documentation**: See [TEST_SUITE_GUIDE.md](TEST_SUITE_GUIDE.md)
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Project README**: See [README.md](README.md)

## Version Info

- **Test Suite Version**: 1.0.0
- **Python Required**: 3.9+
- **Dependencies**: httpx
- **Last Updated**: 2025-10-22
