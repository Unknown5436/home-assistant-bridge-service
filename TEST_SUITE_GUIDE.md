# Home Assistant Bridge Service - Comprehensive Test Suite Guide

## Overview

This guide provides complete instructions for using the comprehensive test suite for the Home Assistant Bridge Service.

## Quick Start

```bash
# Install dependencies (if not already installed)
pip install httpx

# Run the test suite (full mode - default)
python test_complete_ha_bridge.py

# Run quick tests only
python test_complete_ha_bridge.py quick

# Run stress tests
python test_complete_ha_bridge.py stress

# Run integration tests
python test_complete_ha_bridge.py integration
```

## Test Modes

### 1. Quick Mode (~1 minute)

**Purpose**: Fast validation of core functionality

**What it tests**:

- ✅ Core API endpoints (health, status, metrics)
- ✅ States management (all states, specific entities)
- ✅ Services management (all services, domain-specific)
- ✅ Authentication and authorization

**When to use**:

- Quick validation after code changes
- Pre-commit checks
- Continuous integration pipelines
- Initial service health check

**Command**: `python test_complete_ha_bridge.py quick`

### 2. Full Mode (~5 minutes) - DEFAULT

**Purpose**: Comprehensive testing of all features

**What it tests**:

- ✅ Everything in Quick mode
- ✅ Performance and caching behavior
- ✅ Error handling and edge cases
- ✅ Advanced features (metrics, WebSocket status, config)
- ✅ Concurrent request handling

**When to use**:

- Before deploying to production
- After significant code changes
- Regular quality assurance checks
- Pre-release testing

**Command**: `python test_complete_ha_bridge.py` or `python test_complete_ha_bridge.py full`

### 3. Stress Mode (~10 minutes)

**Purpose**: Load testing and performance validation under stress

**What it tests**:

- ✅ Everything in Full mode
- ✅ Rapid fire requests (50+ requests)
- ✅ Rate limiting enforcement
- ✅ Service stability under load
- ✅ Performance degradation analysis

**When to use**:

- Before scaling up in production
- Performance benchmarking
- Identifying bottlenecks
- Load capacity planning

**Command**: `python test_complete_ha_bridge.py stress`

### 4. Integration Mode (~3 minutes)

**Purpose**: End-to-end validation with Home Assistant

**What it tests**:

- ✅ Everything in Full mode
- ✅ Direct Home Assistant API connectivity
- ✅ Data consistency (Bridge vs HA direct)
- ✅ Real-time synchronization
- ✅ Performance comparison (Bridge speedup)

**When to use**:

- After Home Assistant updates
- Validating HA connectivity
- Ensuring data accuracy
- Performance optimization verification

**Command**: `python test_complete_ha_bridge.py integration`

## Test Categories

### Category 1: Core API Endpoints

**Tests**: 5 tests

- Health check endpoint
- API status endpoint
- Service health check
- Config health endpoint
- Metrics endpoint

**Success Criteria**: All endpoints return 200 status

### Category 2: States Management

**Tests**: 3 tests

- Get all states (validates structure, entity count)
- Get specific entity (existing entity)
- Get non-existent entity (404 handling)

**Success Criteria**:

- All states returned with correct count (1,186+ entities)
- Specific entity retrieval works
- Invalid entities return 404

### Category 3: Services Management

**Tests**: 3 tests

- Get all services (validates structure, service count)
- Get domain-specific services (e.g., light domain)
- Get non-existent domain (404 handling)

**Success Criteria**:

- All services returned with correct count
- Domain filtering works correctly
- Invalid domains return 404

### Category 4: Authentication & Security

**Tests**: 4 tests

- No authentication (should fail with 401)
- Invalid API key (should fail with 401)
- Valid API key (should succeed)
- Public endpoint access (no auth required)

**Success Criteria**:

- Protected endpoints require authentication
- Invalid credentials are rejected
- Valid credentials grant access
- Public endpoints work without auth

### Category 5: Performance & Caching

**Tests**: 2-3 tests

- Response time performance (5 requests)
- Cache effectiveness validation
- Concurrent request handling (10 simultaneous)

**Success Criteria**:

- Average response time < 1.0 second
- Caching reduces subsequent request times
- Concurrent requests handled correctly

### Category 6: Error Handling

**Tests**: 4 tests

- Non-existent endpoint (404)
- Invalid entity ID format
- Malformed requests
- Method not allowed

**Success Criteria**:

- Graceful error handling for all cases
- Appropriate HTTP status codes
- No service crashes or exceptions

### Category 7: Advanced Features

**Tests**: 3 tests

- Prometheus metrics format validation
- WebSocket status check
- Configuration info retrieval

**Success Criteria**:

- Metrics in Prometheus format
- WebSocket status reported correctly
- Configuration accessible

### Category 8: Integration Tests

**Tests**: 3 tests (integration mode only)

- Direct HA API connection
- HA states API access
- Data consistency (Bridge vs HA)

**Success Criteria**:

- Direct HA connection succeeds
- Entity counts match between Bridge and HA
- Bridge provides performance improvement

### Category 9: Stress Testing

**Tests**: 2 tests (stress mode only)

- Rapid fire load test (50 requests)
- Rate limiting enforcement

**Success Criteria**:

- All requests succeed under load
- Average response time < 2.0 seconds
- Rate limiting triggers appropriately

## Configuration

Edit the `TestConfig` class in `test_complete_ha_bridge.py` to customize:

```python
@dataclass
class TestConfig:
    base_url: str = "http://127.0.0.1:8000"      # Bridge service URL
    api_key: str = "test-api-key-12345"          # API authentication key
    ha_url: str = "https://your-ha-url:8123"     # Home Assistant URL
    ha_token: str = "your-long-lived-token"      # HA long-lived token
    timeout: int = 30                             # Request timeout (seconds)
    test_mode: str = "full"                       # Default test mode
```

## Understanding Test Output

### Test Result Format

```
✅ Test Name: 200 (0.123s)
   📊 detail_key: detail_value
```

- **✅** = Passed, **❌** = Failed
- **Status Code**: HTTP response code
- **(0.123s)**: Response time in seconds
- **📊 Details**: Additional information about the test

### Summary Statistics

```
📊 TEST SUMMARY
Total Tests: 25
✅ Passed: 25
❌ Failed: 0
Success Rate: 100.0%
Duration: 15.45s

⚡ Performance Metrics:
  Average Response Time: 0.123s
  Median Response Time: 0.098s
  P95 Response Time: 0.345s

📋 Results by Category:
  ✅ Core: 5/5 passed (100.0%)
  ✅ States: 3/3 passed (100.0%)
  ✅ Services: 3/3 passed (100.0%)
  ✅ Security: 4/4 passed (100.0%)
  ✅ Performance: 2/2 passed (100.0%)
  ✅ Error Handling: 4/4 passed (100.0%)
  ✅ Advanced: 3/3 passed (100.0%)
```

### Performance Interpretation

| Metric                | Good   | Acceptable  | Poor   |
| --------------------- | ------ | ----------- | ------ |
| Average Response Time | < 0.5s | 0.5s - 1.0s | > 1.0s |
| P95 Response Time     | < 1.0s | 1.0s - 2.0s | > 2.0s |
| Success Rate          | 100%   | 95% - 99%   | < 95%  |

## Test Reports

After each test run, a detailed JSON report is saved:

**Filename**: `test_report_YYYYMMDD_HHMMSS.json`

**Contents**:

```json
{
  "timestamp": "2025-10-22T20:30:15.123456",
  "test_mode": "full",
  "statistics": {
    "total_tests": 25,
    "passed": 25,
    "failed": 0,
    "success_rate": 100.0,
    "duration_seconds": 15.45,
    "avg_response_time": 0.123,
    "median_response_time": 0.098,
    "p95_response_time": 0.345
  },
  "results": [
    {
      "name": "Health Check",
      "category": "Core",
      "success": true,
      "status_code": 200,
      "response_time": 0.045,
      "error": null,
      "details": {}
    }
  ]
}
```

## Expected Results

### Production-Ready Service

For a fully operational service, expect:

- **Success Rate**: 100% (all tests pass)
- **Average Response Time**: < 1.0 second
- **Entity Count**: 1,186+ entities accessible
- **Service Count**: 100+ services available
- **No Authentication Bypasses**: All security tests pass
- **Graceful Error Handling**: All error cases handled correctly

### Known Issues

If certain tests fail, common causes include:

1. **Service Not Running**: Ensure bridge service is running on port 8000
2. **Wrong API Key**: Verify API_KEY in .env matches test config
3. **HA Unavailable**: Home Assistant server must be online
4. **Network Issues**: Check firewall and network connectivity
5. **Slow Network**: Increase timeout in TestConfig if needed

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test HA Bridge Service

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.9"
      - name: Install dependencies
        run: pip install httpx
      - name: Start service
        run: |
          python start.py &
          sleep 5
      - name: Run tests
        run: python test_complete_ha_bridge.py quick
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_report_*.json
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running HA Bridge tests..."
python test_complete_ha_bridge.py quick
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Advanced Usage

### Custom Test Configuration

Create a custom config file `test_config.py`:

```python
from test_complete_ha_bridge import TestConfig, HABridgeComprehensiveTester

# Custom configuration
config = TestConfig(
    base_url="https://my-bridge.example.com",
    api_key="my-custom-api-key",
    timeout=60,
    test_mode="full"
)

# Run tests
with HABridgeComprehensiveTester(config) as tester:
    tester.run_all_tests()
```

### Selective Test Execution

Run specific test categories:

```python
from test_complete_ha_bridge import TestConfig, HABridgeComprehensiveTester

config = TestConfig()

with HABridgeComprehensiveTester(config) as tester:
    # Run only specific tests
    tester.test_core_endpoints()
    tester.test_authentication()
    tester.print_summary()
```

### Programmatic Access

Use test results in your own scripts:

```python
from test_complete_ha_bridge import TestConfig, HABridgeComprehensiveTester

config = TestConfig()

with HABridgeComprehensiveTester(config) as tester:
    tester.run_all_tests()

    # Access results
    stats = tester.summary.get_stats()

    if stats['success_rate'] < 95:
        send_alert(f"Service health degraded: {stats['success_rate']}%")
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.

## Performance Benchmarks

### Expected Performance (Typical Hardware)

**Hardware**: Raspberry Pi 4 (4GB RAM)

| Test Category       | Expected Time |
| ------------------- | ------------- |
| Core Endpoints      | 0.3s - 0.5s   |
| States Management   | 0.8s - 1.2s   |
| Services Management | 0.8s - 1.2s   |
| Authentication      | 0.2s - 0.4s   |
| Performance Tests   | 3s - 5s       |
| Full Test Suite     | 4min - 6min   |

**Hardware**: Cloud VM (2 vCPU, 4GB RAM)

| Test Category       | Expected Time |
| ------------------- | ------------- |
| Core Endpoints      | 0.1s - 0.2s   |
| States Management   | 0.3s - 0.5s   |
| Services Management | 0.3s - 0.5s   |
| Authentication      | 0.1s - 0.2s   |
| Performance Tests   | 1s - 2s       |
| Full Test Suite     | 2min - 3min   |

## Best Practices

1. **Run quick tests frequently** during development
2. **Run full tests before commits** to main branch
3. **Run integration tests** after HA updates
4. **Run stress tests** before production deployment
5. **Monitor test reports** for performance trends
6. **Keep test configuration** in sync with production
7. **Review failed test details** before retrying
8. **Save test reports** for historical analysis

## Support

For issues or questions:

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review test output and error messages
- Check service logs for detailed error information
- Verify Home Assistant is accessible
- Ensure all dependencies are installed

## Version History

- **v1.0.0** (2025-10-22): Initial comprehensive test suite
  - All test modes implemented
  - Full documentation
  - JSON report generation
