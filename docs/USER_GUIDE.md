# Home Assistant Bridge Service - User Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Common Use Cases](#common-use-cases)
5. [Integration Examples](#integration-examples)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## Quick Start

### Prerequisites

- Home Assistant Bridge Service running (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md))
- Valid API key
- Python 3.9+ or curl/HTTP client

### Basic Setup

```bash
# Service URL (default)
BASE_URL="http://127.0.0.1:8000"

# Your API key (from .env file)
API_KEY="test-api-key-12345"

# Test connection
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/health
```

### Python Setup

```python
import requests

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "test-api-key-12345"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Test connection
response = requests.get(f"{BASE_URL}/health", headers=HEADERS)
print(response.json())
```

## Authentication

### API Key Format

**Correct Format:**
```bash
Authorization: Bearer your-api-key-here
```

**Incorrect Formats:**
```bash
# Wrong header name
X-API-Key: your-api-key-here

# Missing Bearer prefix
Authorization: your-api-key-here
```

### Getting API Keys

API keys are configured in the `.env` file:

```bash
# .env file
API_KEYS=["test-api-key-12345","your-second-key","your-third-key"]
```

### Rate Limiting

- **Default**: 100 requests per 60-second window per API key
- **Per IP**: Additional rate limiting per client IP
- **Headers**: Rate limit info included in response headers

```python
# Check rate limit headers
response = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
print("Rate limit:", response.headers.get("X-RateLimit-Limit"))
print("Remaining:", response.headers.get("X-RateLimit-Remaining"))
```

## API Endpoints

### Core Endpoints

#### Health Check
```bash
# No authentication required
curl $BASE_URL/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1761237022.5392349,
  "version": "1.0.0",
  "ha_connected": true,
  "websocket": {
    "connected": true,
    "reconnect_attempts": 0,
    "subscriptions": 3
  },
  "metrics_enabled": true,
  "websocket_enabled": true
}
```

#### Service Status
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/status
```

#### Metrics (Prometheus Format)
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/metrics
```

### States Management

#### Get All States
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/api/v1/states/all
```

**Python Example:**
```python
response = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
states = response.json()

for state in states:
    print(f"{state['entity_id']}: {state['state']}")
```

#### Get Specific State
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/api/v1/states/light.bedroom_lamp
```

**Python Example:**
```python
entity_id = "light.bedroom_lamp"
response = requests.get(f"{BASE_URL}/api/v1/states/{entity_id}", headers=HEADERS)
state = response.json()

print(f"Entity: {state['entity_id']}")
print(f"State: {state['state']}")
print(f"Attributes: {state['attributes']}")
```

#### Set State
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "on", "attributes": {"brightness": 255}}' \
  $BASE_URL/api/v1/states/light.bedroom_lamp
```

**Python Example:**
```python
entity_id = "light.bedroom_lamp"
data = {
    "state": "on",
    "attributes": {"brightness": 255}
}

response = requests.post(
    f"{BASE_URL}/api/v1/states/{entity_id}",
    headers=HEADERS,
    json=data
)
```

### Services Management

#### Get All Services
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/api/v1/services/all
```

#### Get Services by Domain
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/api/v1/services/domain/light
```

#### Call Service
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "light.bedroom_lamp"}' \
  $BASE_URL/api/v1/services/light/turn_on
```

**Python Example:**
```python
service_data = {"entity_id": "light.bedroom_lamp"}
response = requests.post(
    f"{BASE_URL}/api/v1/services/light/turn_on",
    headers=HEADERS,
    json=service_data
)
```

### Configuration

#### Get Home Assistant Configuration
```bash
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/api/v1/config
```

## Common Use Cases

### 1. Turn On/Off Lights

```python
def control_light(entity_id, action="toggle"):
    """Control a light entity."""
    if action == "on":
        service = "turn_on"
    elif action == "off":
        service = "turn_off"
    else:
        service = "toggle"
    
    response = requests.post(
        f"{BASE_URL}/api/v1/services/light/{service}",
        headers=HEADERS,
        json={"entity_id": entity_id}
    )
    return response.json()

# Usage
control_light("light.bedroom_lamp", "on")
control_light("light.living_room", "off")
```

### 2. Get All Light States

```python
def get_all_lights():
    """Get states of all light entities."""
    response = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
    states = response.json()
    
    lights = [state for state in states if state['entity_id'].startswith('light.')]
    return lights

# Usage
lights = get_all_lights()
for light in lights:
    print(f"{light['entity_id']}: {light['state']}")
```

### 3. Monitor Sensor Values

```python
def get_sensor_value(sensor_id):
    """Get current value of a sensor."""
    response = requests.get(f"{BASE_URL}/api/v1/states/{sensor_id}", headers=HEADERS)
    state = response.json()
    return state['state']

# Usage
temperature = get_sensor_value("sensor.temperature")
print(f"Current temperature: {temperature}°C")
```

### 4. Batch Operations (Workaround)

Since the batch endpoint has a known issue, use individual requests:

```python
import asyncio
import aiohttp

async def get_multiple_states(entity_ids):
    """Get multiple entity states concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for entity_id in entity_ids:
            task = session.get(
                f"{BASE_URL}/api/v1/states/{entity_id}",
                headers=HEADERS
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        results = {}
        
        for i, response in enumerate(responses):
            data = await response.json()
            results[entity_ids[i]] = data
        
        return results

# Usage
entity_ids = ["light.bedroom_lamp", "sensor.temperature", "switch.outlet"]
states = await get_multiple_states(entity_ids)
```

## Integration Examples

### 1. AI Assistant Integration

```python
class HomeAssistantController:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def turn_on_lights(self, room=None):
        """Turn on lights in a specific room or all lights."""
        if room:
            entity_id = f"light.{room}_lamp"
            self._call_service("light", "turn_on", {"entity_id": entity_id})
        else:
            # Turn on all lights
            lights = self._get_entities_by_domain("light")
            for light in lights:
                if light['state'] == 'off':
                    self._call_service("light", "turn_on", {"entity_id": light['entity_id']})
    
    def get_room_temperature(self, room):
        """Get temperature for a specific room."""
        sensor_id = f"sensor.{room}_temperature"
        state = self._get_state(sensor_id)
        return state['state']
    
    def _get_state(self, entity_id):
        response = requests.get(f"{self.base_url}/api/v1/states/{entity_id}", headers=self.headers)
        return response.json()
    
    def _call_service(self, domain, service, service_data):
        response = requests.post(
            f"{self.base_url}/api/v1/services/{domain}/{service}",
            headers=self.headers,
            json=service_data
        )
        return response.json()
    
    def _get_entities_by_domain(self, domain):
        response = requests.get(f"{self.base_url}/api/v1/states/all", headers=self.headers)
        states = response.json()
        return [state for state in states if state['entity_id'].startswith(f"{domain}.")]

# Usage
ha = HomeAssistantController("http://127.0.0.1:8000", "test-api-key-12345")
ha.turn_on_lights("bedroom")
temp = ha.get_room_temperature("living")
```

### 2. Webhook Integration

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook/ha', methods=['POST'])
def ha_webhook():
    """Webhook endpoint for Home Assistant control."""
    data = request.json
    
    # Extract command from webhook
    action = data.get('action')
    entity = data.get('entity')
    
    if action == 'turn_on':
        response = requests.post(
            f"{BASE_URL}/api/v1/services/light/turn_on",
            headers=HEADERS,
            json={"entity_id": entity}
        )
    elif action == 'turn_off':
        response = requests.post(
            f"{BASE_URL}/api/v1/services/light/turn_off",
            headers=HEADERS,
            json={"entity_id": entity}
        )
    
    return jsonify({"status": "success", "response": response.json()})

if __name__ == '__main__':
    app.run(port=5000)
```

### 3. Scheduled Tasks

```python
import schedule
import time

def morning_routine():
    """Morning automation routine."""
    # Turn on bedroom light
    requests.post(
        f"{BASE_URL}/api/v1/services/light/turn_on",
        headers=HEADERS,
        json={"entity_id": "light.bedroom_lamp"}
    )
    
    # Check temperature
    temp_response = requests.get(
        f"{BASE_URL}/api/v1/states/sensor.temperature",
        headers=HEADERS
    )
    temp = temp_response.json()['state']
    print(f"Good morning! Temperature: {temp}°C")

def evening_routine():
    """Evening automation routine."""
    # Turn off all lights
    lights_response = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
    lights = [state for state in lights_response.json() if state['entity_id'].startswith('light.')]
    
    for light in lights:
        if light['state'] == 'on':
            requests.post(
                f"{BASE_URL}/api/v1/services/light/turn_off",
                headers=HEADERS,
                json={"entity_id": light['entity_id']}
            )

# Schedule tasks
schedule.every().day.at("07:00").do(morning_routine)
schedule.every().day.at("22:00").do(evening_routine)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors (401)
```bash
# Check API key format
curl -H "Authorization: Bearer your-api-key" $BASE_URL/health

# Verify API key in .env file
grep API_KEYS .env
```

#### 2. Connection Refused
```bash
# Check if service is running
curl $BASE_URL/health

# Check service logs
tail -f service.log
```

#### 3. Slow Response Times
```python
# Check if caching is working
import time

start = time.time()
response1 = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
time1 = time.time() - start

start = time.time()
response2 = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
time2 = time.time() - start

print(f"First request: {time1:.2f}s")
print(f"Second request: {time2:.2f}s (should be faster)")
```

#### 4. Batch States Endpoint Issue
```python
# Known issue: Use individual requests instead
def get_multiple_states_safe(entity_ids):
    """Safe way to get multiple states."""
    results = {}
    for entity_id in entity_ids:
        try:
            response = requests.get(f"{BASE_URL}/api/v1/states/{entity_id}", headers=HEADERS)
            results[entity_id] = response.json()
        except Exception as e:
            results[entity_id] = {"error": str(e)}
    return results
```

### Debugging Tips

#### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use requests debugging
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

#### Check Service Health
```python
def check_service_health():
    """Comprehensive service health check."""
    try:
        # Basic health check
        health = requests.get(f"{BASE_URL}/health").json()
        print(f"Service Status: {health['status']}")
        print(f"HA Connected: {health['ha_connected']}")
        print(f"WebSocket: {health['websocket']['connected']}")
        
        # Test API key
        test_response = requests.get(f"{BASE_URL}/api/v1/states/all", headers=HEADERS)
        print(f"API Test: {test_response.status_code}")
        
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
```

## Best Practices

### 1. Error Handling
```python
def safe_api_call(endpoint, method="GET", data=None):
    """Make API calls with proper error handling."""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", headers=HEADERS, json=data)
        
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection failed - is the service running?"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2. Caching Strategy
```python
import time
from functools import lru_cache

class CachedHAClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds
    
    def _is_cache_valid(self, key):
        """Check if cached data is still valid."""
        if key not in self._cache:
            return False
        
        cached_time, _ = self._cache[key]
        return time.time() - cached_time < self._cache_ttl
    
    def get_state(self, entity_id, use_cache=True):
        """Get entity state with caching."""
        if use_cache and self._is_cache_valid(entity_id):
            return self._cache[entity_id][1]
        
        response = requests.get(f"{self.base_url}/api/v1/states/{entity_id}", headers=self.headers)
        data = response.json()
        
        if use_cache:
            self._cache[entity_id] = (time.time(), data)
        
        return data
```

### 3. Rate Limiting
```python
import time
from collections import defaultdict

class RateLimitedClient:
    def __init__(self, base_url, api_key, max_requests=100, window=60):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def _can_make_request(self):
        """Check if we can make a request without hitting rate limit."""
        now = time.time()
        key = int(now // self.window)
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < self.window]
        
        return len(self.requests[key]) < self.max_requests
    
    def _record_request(self):
        """Record a request for rate limiting."""
        now = time.time()
        key = int(now // self.window)
        self.requests[key].append(now)
    
    def get(self, endpoint):
        """Make a GET request with rate limiting."""
        if not self._can_make_request():
            time.sleep(1)  # Wait before retrying
        
        self._record_request()
        return requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
```

### 4. Async Operations
```python
import asyncio
import aiohttp

class AsyncHAClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def get_multiple_states(self, entity_ids):
        """Get multiple states concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for entity_id in entity_ids:
                task = session.get(
                    f"{self.base_url}/api/v1/states/{entity_id}",
                    headers=self.headers
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            results = {}
            
            for i, response in enumerate(responses):
                data = await response.json()
                results[entity_ids[i]] = data
            
            return results

# Usage
async def main():
    client = AsyncHAClient("http://127.0.0.1:8000", "test-api-key-12345")
    entity_ids = ["light.bedroom_lamp", "sensor.temperature", "switch.outlet"]
    states = await client.get_multiple_states(entity_ids)
    print(states)

asyncio.run(main())
```

## Additional Resources

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed troubleshooting guide
- [TEST_SUITE_GUIDE.md](TEST_SUITE_GUIDE.md) - Comprehensive testing guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production deployment guide
- [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) - Technical overview

## Support

For additional help:

1. Check the troubleshooting guide
2. Review service logs
3. Test with curl commands
4. Verify configuration settings
5. Check Home Assistant connectivity

Remember: The service is designed to be robust and handle errors gracefully. Most issues are configuration-related and can be resolved by checking the basics: service running, API key correct, and Home Assistant accessible.