# Home Assistant Bridge Service - Test Suite Troubleshooting Guide

## Quick Diagnostic Checklist

Before diving into specific issues, run through this quick checklist:

- [ ] Is the bridge service running? (`http://127.0.0.1:8000/health`)
- [ ] Is Home Assistant accessible? (`https://your-ha-url:8123`)
- [ ] Is the API key correct in test configuration?
- [ ] Are all dependencies installed? (`pip install httpx`)
- [ ] Is there a firewall blocking connections?
- [ ] Are environment variables set correctly?

## Common Issues & Solutions

### 1. Connection Refused / Service Not Running

**Symptom**:

```
❌ Health Check: 0 (0.000s)
   ❌ Error: Connection refused
```

**Causes**:

- Bridge service is not running
- Service is running on different port
- Firewall blocking connection

**Solutions**:

```bash
# Check if service is running
curl http://127.0.0.1:8000/health

# Start the service
python start.py

# Check if port 8000 is in use
netstat -an | grep 8000    # Linux/Mac
netstat -an | findstr 8000  # Windows

# Try different port in test config if needed
base_url: str = "http://127.0.0.1:8001"  # Change port
```

### 2. Authentication Failures (401 Unauthorized)

**Symptom**:

```
❌ Get All Services: 401 (0.123s)
   ❌ Error: Unauthorized
```

**Causes**:

- API key mismatch between service and test
- API key not configured in environment
- Wrong authorization header format

**Solutions**:

```bash
# Check .env file has correct API_KEY
cat .env | grep API_KEYS

# Verify API_KEY matches test config
# In test_complete_ha_bridge.py:
api_key: str = "test-api-key-12345"  # Must match .env

# Check environment variable is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('API_KEYS'))"

# Restart service after changing .env
pkill -f "python start.py"
python start.py
```

**Test Configuration**:

```python
# Ensure API key in test matches service
@dataclass
class TestConfig:
    api_key: str = "test-api-key-12345"  # Must match API_KEYS in .env
```

### 3. Timeout Errors

**Symptom**:

```
❌ Get All States: 0 (30.000s)
   ❌ Error: Read timeout
```

**Causes**:

- Home Assistant is slow or unresponsive
- Network latency issues
- Service overloaded
- Large dataset taking too long

**Solutions**:

```python
# Increase timeout in test config
@dataclass
class TestConfig:
    timeout: int = 60  # Increase from 30 to 60 seconds

# Check Home Assistant response time directly
curl -w "@curl-format.txt" -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/states

# Monitor service logs for slow queries
tail -f app.log

# Check cache is working (should speed up subsequent requests)
# Run test twice and compare times
```

### 4. Home Assistant Connection Issues

**Symptom**:

```
❌ Get All States: 500 (1.234s)
   ❌ Error: Unable to connect to Home Assistant
```

**Causes**:

- Home Assistant is down or unreachable
- Invalid HA URL or token
- SSL certificate issues
- Network/firewall blocking connection

**Solutions**:

```bash
# Test HA direct connection
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/

# Check HA is accessible
ping raspberrypieha.duckdns.org

# Test with SSL verification disabled (debugging only)
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/

# Verify token is valid and not expired
# Go to HA UI -> Profile -> Long-Lived Access Tokens
# Create new token if needed

# Check .env configuration
cat .env | grep HA_URL
cat .env | grep HA_TOKEN
```

**Fix SSL Certificate Issues**:

```python
# In ha_client.py, temporarily for debugging:
self.client = httpx.AsyncClient(
    timeout=30.0,
    verify=False  # Only for debugging SSL issues
)
```

### 5. Rate Limiting (429 Too Many Requests)

**Symptom**:

```
❌ Multiple Tests: 429 (0.045s)
   ❌ Error: Too many requests
```

**Causes**:

- Too many rapid requests
- Rate limit threshold too low
- Stress test triggered rate limiting

**Solutions**:

```python
# This is actually EXPECTED behavior during stress tests
# Rate limiting is working correctly

# To adjust rate limits in service, edit .env:
RATE_LIMIT_REQUESTS=200  # Increase from 100
RATE_LIMIT_WINDOW=60     # Time window in seconds

# Restart service after changes
python start.py

# Add delay between requests in custom tests
import time
time.sleep(0.1)  # 100ms delay between requests
```

### 6. Invalid Entity ID or Service Not Found (404)

**Symptom**:

```
❌ Get Specific Entity: 404 (0.123s)
   ❌ Error: Entity not found
```

**Causes**:

- Entity ID doesn't exist in Home Assistant
- Typo in entity ID
- Entity was removed or renamed
- Service domain doesn't exist

**Solutions**:

```bash
# List all entities to find correct ID
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8000/api/v1/states/all | jq '.states[].entity_id'

# Search for specific entity pattern
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8000/api/v1/states/all | grep "sensor.temperature"

# Verify entity exists in Home Assistant UI
# Go to Developer Tools -> States
# Search for entity

# Update test with valid entity ID
# In test script, change to existing entity:
"/api/v1/states/binary_sensor.samba_backup_running",  # Use valid entity
```

### 7. Data Validation Failures

**Symptom**:

```
❌ Get All Services: 200 (0.456s)
   ❌ Error: AssertionError: 'count' not in response
```

**Causes**:

- Response format changed
- API returned unexpected structure
- Service returned error wrapped in 200 response

**Solutions**:

```python
# Inspect actual response structure
import httpx
response = httpx.get(
    "http://127.0.0.1:8000/api/v1/services/all",
    headers={"Authorization": "Bearer test-api-key-12345"}
)
print(response.json())

# Check service logs for errors
tail -f app.log

# Verify Home Assistant API is returning expected format
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/services

# Update validation if response format intentionally changed
def _validate_services_response(self, data: Any):
    # Adjust validation to match actual response structure
    assert isinstance(data, dict)
    # ... update assertions
```

### 8. Performance Degradation

**Symptom**:

```
✅ Response Time Performance: 200 (3.456s)
   📊 Performance: ⚠️  Slow
```

**Causes**:

- Cache not working
- Home Assistant slow to respond
- Network latency
- Service under heavy load
- Large dataset causing slowdown

**Solutions**:

```python
# Check cache is enabled
# In .env:
CACHE_TTL=300  # 5 minutes cache

# Verify cache is working by comparing times
# First request should be slower, subsequent faster

# Check Home Assistant performance directly
time curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/states

# Monitor service resource usage
htop  # Linux
top   # Mac
# Check CPU and memory usage

# Increase cache TTL if appropriate
CACHE_TTL=600  # 10 minutes

# Consider implementing additional caching layers
# Or reducing data transferred
```

### 9. Import Errors / Missing Dependencies

**Symptom**:

```
ModuleNotFoundError: No module named 'httpx'
```

**Causes**:

- Dependencies not installed
- Wrong Python environment
- Virtual environment not activated

**Solutions**:

```bash
# Install required dependencies
pip install httpx

# Or install all project dependencies
pip install -r requirements.txt

# Check Python version (3.9+ required)
python --version

# Verify httpx is installed
python -c "import httpx; print(httpx.__version__)"

# If using virtual environment, activate it first
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Then run tests
python test_complete_ha_bridge.py
```

### 10. Integration Tests Failing

**Symptom**:

```
❌ Data Consistency (Bridge vs HA): 200 (1.234s)
   📊 bridge_entities: 1186
   📊 ha_entities: 1190
   📊 match: False
```

**Causes**:

- Entity count mismatch (expected - HA state changes)
- Timing issue (entities added/removed between requests)
- Cache serving stale data

**Solutions**:

```python
# Small mismatches are normal due to timing
# This is not necessarily a failure

# To force fresh data, clear cache
# Restart bridge service
pkill -f "python start.py"
python start.py

# Or wait for cache to expire (CACHE_TTL seconds)
# Then run integration test again

# Adjust test tolerance if needed
# In test script:
difference = abs(bridge_count - ha_count)
success = (difference <= 5)  # Allow small variance

# Check what entities are different
# Query both and compare:
diff <(curl -s "http://127.0.0.1:8000/api/v1/states/all" | jq -r '.states[].entity_id' | sort) \
     <(curl -sk "https://ha-url:8123/api/states" | jq -r '.[].entity_id' | sort)
```

### 11. Stress Tests Causing Service Issues

**Symptom**:

```
❌ Rapid Fire Load Test: Multiple timeouts
   📊 errors: 15/50
```

**Causes**:

- Service overwhelmed by rapid requests
- Resource exhaustion (memory, CPU)
- Connection pool exhaustion
- Rate limiting triggered

**Solutions**:

```python
# This stress test is designed to find limits
# Some failures are expected under extreme load

# Increase service resources
# In docker-compose.yml:
resources:
  limits:
    memory: 1G
    cpus: '2'

# Increase connection pool size
# In ha_client.py:
limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20
)

# Reduce stress test intensity
# In test script, change:
for i in range(25):  # Reduce from 50 to 25

# Add delay between requests
time.sleep(0.01)  # 10ms delay

# Monitor service during stress test
htop  # Watch CPU and memory usage
```

### 13. Batch States Endpoint Validation Error

**Symptom**:

```
❌ Batch States Request: 400 (0.123s)
   ❌ Error: State value is required
```

**Causes**:

- FastAPI validation issue with StateResponse model
- Request/response serialization problem
- Pydantic model validation conflict

**Solutions**:

```python
# This is a known issue requiring investigation
# Single state endpoint works correctly
# Batch endpoint has validation error

# Workaround: Use individual state requests
# Instead of batch endpoint, make multiple individual calls

# Check if issue is resolved in latest version
# Monitor service logs for detailed error information

# Temporary fix: Use individual state endpoints
for entity_id in entity_ids:
    response = requests.get(
        f"http://127.0.0.1:8000/api/v1/states/{entity_id}",
        headers={"Authorization": "Bearer test-api-key-12345"}
    )
```

### 14. Port Conflict Resolution Issues

**Symptom**:

```
⚠ Port 8000 is in use by PID 12345
✗ Port 8000 is still in use after cleanup attempt
```

**Causes**:

- Previous service instance still running
- Process terminated but port in TIME_WAIT state
- Multiple service instances started
- Other application using port 8000

**Solutions**:

```bash
# Use automated startup with port conflict resolution
python start.py --auto-accept-alt-port

# Or specify alternative port
python start.py --port 8001

# Manual port cleanup
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9

# Check for TIME_WAIT state
netstat -an | grep TIME_WAIT

# Wait for OS to release port (usually 2-4 minutes)
# Or use alternative port
```

### 15. Missing check_connection Method Error

**Symptom**:

```
{"error": "'HomeAssistantClient' object has no attribute 'check_connection'", "event": "Failed to check HA connection"}
```

**Causes**:

- Missing method in HomeAssistantClient class
- Code version mismatch
- Incomplete implementation

**Solutions**:

```python
# Add missing method to HomeAssistantClient
async def check_connection(self) -> bool:
    """Check if Home Assistant is reachable."""
    try:
        client = await self._get_client()
        response = await client.get("/api/")
        return response.status_code == 200
    except Exception as e:
        logger.warning("HA connection check failed", error=str(e))
        return False

# Restart service after adding method
python start.py
```

### 16. Authentication Header Format Issues

**Symptom**:

```
❌ API Request: 401 (0.045s)
   ❌ Error: Invalid or missing API key
```

**Causes**:

- Wrong authentication header format
- Missing Bearer prefix
- Incorrect header name

**Solutions**:

```python
# CORRECT format:
headers = {'Authorization': 'Bearer test-api-key-12345'}

# INCORRECT formats:
headers = {'X-API-Key': 'test-api-key-12345'}  # Wrong header
headers = {'Authorization': 'test-api-key-12345'}  # Missing Bearer

# Verify API key in .env file
cat .env | grep API_KEYS

# Test with curl
curl -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/states/all
```

### 17. WebSocket Connection Timeout

**Symptom**:

```
{"error": "timed out during opening handshake", "ws_url": "wss://raspberrypieha.duckdns.org:8123/api/websocket"}
```

**Causes**:

- Home Assistant WebSocket server slow to respond
- Network latency issues
- SSL/TLS handshake problems
- HA server overloaded

**Solutions**:

```python
# This is not critical - service works without WebSocket
# WebSocket provides real-time updates but is optional

# Check HA WebSocket directly
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/websocket

# Increase WebSocket timeout in configuration
WEBSOCKET_TIMEOUT=30  # Increase from default

# Check HA server performance
# Monitor HA logs for WebSocket issues

# Service will continue with polling-based updates
# WebSocket reconnection happens automatically
```

## Test Mode Specific Issues

### Quick Mode Issues

Usually indicates core service problems. If quick tests fail:

1. Verify service is running
2. Check authentication
3. Verify HA connectivity
4. Review service logs

### Full Mode Issues

If full tests fail but quick tests pass:

- Performance issues
- Caching problems
- Concurrent request handling issues

### Stress Mode Issues

Expected to find limits. If stress tests fail:

- Normal to have some failures under extreme load
- Indicates where service limits are
- Use to tune performance parameters

### Integration Mode Issues

If integration tests fail:

- Direct HA connectivity problem
- Token expired or invalid
- Network/SSL issues
- Data consistency timing issues

## Debugging Tips

### Enable Verbose Logging

```python
# In test script, add verbose output
import logging
logging.basicConfig(level=logging.DEBUG)

# Or modify print_result to always show details
self.print_result(result, verbose=True)
```

### Inspect Raw Responses

```python
# Add response inspection
status, elapsed, data, error = self.make_request(...)
print(f"Raw response: {data}")
print(f"Error details: {error}")
```

### Test Individual Endpoints

```python
# Test single endpoint in isolation
from test_complete_ha_bridge import TestConfig, HABridgeComprehensiveTester

config = TestConfig()
with HABridgeComprehensiveTester(config) as tester:
    result = tester.test_endpoint(
        "Debug Test",
        "Debug",
        "GET",
        "/api/v1/services/all",
        requires_auth=True
    )
    print(f"Status: {result.status_code}")
    print(f"Data: {result.data}")
    print(f"Error: {result.error}")
```

### Check Service Health Manually

```bash
# Test each endpoint manually
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
curl http://127.0.0.1:8000/metrics

curl -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/services/all

curl -H "Authorization: Bearer test-api-key-12345" \
  http://127.0.0.1:8000/api/v1/states/all
```

### Review Service Logs

```bash
# Check for errors in service logs
tail -f app.log

# Search for specific errors
grep -i error app.log
grep -i exception app.log

# Check access logs
grep "api/v1" app.log | tail -20
```

### Network Diagnostics

```bash
# Test HA connectivity
ping raspberrypieha.duckdns.org
curl -I https://raspberrypieha.duckdns.org:8123

# Check DNS resolution
nslookup raspberrypieha.duckdns.org

# Test with verbose curl
curl -v -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-ha-url:8123/api/

# Check firewall rules
sudo iptables -L  # Linux
# Or check Windows Firewall settings
```

## Getting Help

If issues persist after trying these solutions:

1. **Collect Information**:

   - Test output (full error messages)
   - Service logs
   - Environment configuration (.env with secrets redacted)
   - Test report JSON file
   - System information (OS, Python version)

2. **Check Documentation**:

   - README.md
   - TEST_SUITE_GUIDE.md
   - Service API documentation

3. **Verify Configuration**:

   - Compare working configuration examples
   - Ensure all required environment variables set
   - Check for typos in URLs and tokens

4. **Create Minimal Reproduction**:
   - Isolate specific failing test
   - Try with minimal configuration
   - Test with curl to rule out test script issues

## Performance Optimization Tips

If tests pass but performance is slower than expected:

1. **Enable Caching**: Ensure CACHE_TTL is set appropriately
2. **Optimize HA**: Check Home Assistant performance
3. **Network**: Use wired connection instead of WiFi
4. **Resources**: Allocate more CPU/memory to service
5. **Concurrent Limits**: Tune connection pool settings
6. **Data Size**: Consider filtering/pagination for large datasets

## Known Limitations

1. **Rate Limiting**: By design, rapid requests will be limited
2. **Cache Timing**: First request slower than subsequent (normal)
3. **HA Sync Delay**: Small entity count differences are normal
4. **Network Variance**: Response times vary with network conditions
5. **Concurrent Tests**: May not work in all environments (async support)

## Success Indicators

Your service is healthy if:

- ✅ Success rate: 100% in quick mode
- ✅ Success rate: ≥95% in full mode
- ✅ Average response time: <1.0s
- ✅ All authentication tests pass
- ✅ No connection errors
- ✅ Entity counts match HA (±5 entities)
- ✅ Service stable under load
