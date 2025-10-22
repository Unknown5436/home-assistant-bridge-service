# Home Assistant Bridge Service

A secure FastAPI-based intermediary service that enables Cursor AI to interact with Home Assistant's API. The service provides a robust, performant, and maintainable interface for home automation control.

## Features

- **RESTful API** - Clean, well-documented endpoints for Home Assistant interaction
- **Secure Authentication** - API key-based authentication with rate limiting
- **Real-time Updates** - WebSocket support for live state changes
- **Caching Layer** - In-memory caching for improved performance
- **Metrics & Monitoring** - Prometheus metrics for observability
- **Docker Support** - Easy deployment with Docker and Docker Compose
- **Comprehensive Testing** - Unit and integration tests included

## Quick Start

### Prerequisites

- Python 3.11+
- Home Assistant instance with API access
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd ha-bridge
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**

   ```bash
   cp env.example .env
   # Edit .env with your Home Assistant settings
   ```

4. **Run the service:**
   ```bash
   python -m app.main
   ```

### Docker Deployment

1. **Build and run with Docker Compose:**

   ```bash
   docker-compose up -d
   ```

2. **Or build manually:**
   ```bash
   docker build -t ha-bridge .
   docker run -p 8000:8000 --env-file .env ha-bridge
   ```

## Configuration

### Environment Variables

| Variable              | Description                            | Default                           |
| --------------------- | -------------------------------------- | --------------------------------- |
| `HA_URL`              | Home Assistant URL                     | `http://homeassistant.local:8123` |
| `HA_TOKEN`            | Home Assistant long-lived access token | Required                          |
| `API_KEYS`            | List of valid API keys                 | Required                          |
| `CACHE_TTL`           | Cache time-to-live in seconds          | `300`                             |
| `RATE_LIMIT_REQUESTS` | Requests per window                    | `100`                             |
| `RATE_LIMIT_WINDOW`   | Rate limit window in seconds           | `60`                              |
| `METRICS_ENABLED`     | Enable Prometheus metrics              | `true`                            |
| `WEBSOCKET_ENABLED`   | Enable WebSocket support               | `true`                            |

### Home Assistant Setup

1. **Create a Long-lived Access Token:**

   - Go to Home Assistant → Profile → Long-lived access tokens
   - Create a new token and copy it to your `.env` file

2. **Configure API Keys:**
   - Add your API keys to the `API_KEYS` environment variable
   - Use these keys in the `Authorization: Bearer <key>` header

## API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

All API endpoints (except `/health`, `/metrics`) require authentication:

```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/api/v1/states/
```

### Core Endpoints

#### States

- `GET /api/v1/states/` - Get all entity states
- `GET /api/v1/states/{entity_id}` - Get specific entity state
- `POST /api/v1/states/{entity_id}` - Update entity state
- `GET /api/v1/states/group/{group_id}` - Get group states
- `POST /api/v1/states/group/{group_id}/batch` - Batch update group states

#### Services

- `GET /api/v1/services/` - Get available services
- `POST /api/v1/services/{domain}/{service}` - Call service
- `POST /api/v1/services/batch` - Batch call services
- `GET /api/v1/services/{domain}` - Get domain services

#### Configuration

- `GET /api/v1/config/` - Get HA configuration
- `GET /api/v1/config/health` - Check HA connection health

#### System

- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Detailed service status

### Example Usage

#### Get All States

```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/api/v1/states/
```

#### Turn On a Light

```bash
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"state": "on"}' \
     http://localhost:8000/api/v1/states/light.living_room
```

#### Call a Service

```bash
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"entity_id": "light.living_room"}' \
     http://localhost:8000/api/v1/services/light/turn_on
```

#### Batch Operations

```bash
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '[
       {"entity_id": "light.living_room", "state": "on"},
       {"entity_id": "light.kitchen", "state": "off"}
     ]' \
     http://localhost:8000/api/v1/states/group/lights/batch
```

## Architecture

### Components

1. **FastAPI Application** - Main web framework
2. **Authentication Middleware** - API key validation and rate limiting
3. **Home Assistant Client** - REST API client for HA communication
4. **WebSocket Client** - Real-time updates from HA
5. **Cache Manager** - In-memory caching with TTL
6. **Metrics Collector** - Prometheus metrics for monitoring
7. **Route Handlers** - API endpoint implementations

### Security Features

- **API Key Authentication** - Bearer token validation
- **Rate Limiting** - Per-API-key and per-IP rate limiting
- **Request Validation** - Pydantic models for input validation
- **Error Handling** - Secure error responses without sensitive data
- **CORS Support** - Configurable cross-origin resource sharing

### Performance Features

- **Caching** - TTL-based caching for frequently accessed data
- **Async Operations** - Full async/await support for better concurrency
- **Connection Pooling** - HTTPX client with connection reuse
- **Batch Operations** - Efficient bulk operations for multiple entities

## Monitoring

### Health Checks

The service provides several health check endpoints:

- `/health` - Basic health status
- `/status` - Detailed service status
- `/metrics` - Prometheus metrics

### Metrics

Prometheus metrics are available at `/metrics`:

- Request counts and latencies
- Error rates and types
- Cache hit/miss ratios
- WebSocket connection status
- Rate limit statistics

### Logging

Structured JSON logging with configurable levels:

```json
{
  "timestamp": "2023-01-01T00:00:00Z",
  "level": "info",
  "message": "Request completed",
  "method": "GET",
  "endpoint": "/api/v1/states/",
  "status_code": 200,
  "duration": 0.123
}
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

The project follows Python best practices:

- Type hints throughout
- Pydantic models for validation
- Async/await for I/O operations
- Structured logging
- Comprehensive error handling
- Security-first design

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Troubleshooting

### Common Issues

1. **Connection to Home Assistant fails:**

   - Check `HA_URL` is correct and accessible
   - Verify `HA_TOKEN` is valid and has proper permissions
   - Ensure Home Assistant is running and API is enabled

2. **Authentication errors:**

   - Verify API key is in the `API_KEYS` list
   - Check Authorization header format: `Bearer <key>`
   - Ensure rate limits aren't exceeded

3. **WebSocket connection issues:**
   - Check if WebSocket is enabled in Home Assistant
   - Verify network connectivity
   - Check firewall settings

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python -m app.main
```

### Logs

View logs in Docker:

```bash
docker-compose logs -f ha-bridge
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub
4. Check Home Assistant community forums for HA-specific issues
