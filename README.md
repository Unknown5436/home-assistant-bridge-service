# Home Assistant Bridge Service

A secure FastAPI-based intermediary service that enables Cursor AI to interact with Home Assistant's API. The service provides a robust, performant, and maintainable interface for home automation control.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)

## ✨ Features

- **🔐 Secure Authentication** - API key-based authentication with rate limiting
- **🚀 RESTful API** - Clean, well-documented endpoints for Home Assistant interaction
- **⚡ Real-time Updates** - WebSocket support for live state changes
- **💾 Intelligent Caching** - In-memory caching with TTL for improved performance
- **📊 Metrics & Monitoring** - Prometheus metrics for observability
- **🐳 Docker Support** - Easy deployment with Docker and Docker Compose
- **🧪 Comprehensive Testing** - Unit and integration tests included
- **🔄 Batch Operations** - Efficient bulk operations for multiple entities
- **🖥️ Control Panel UI** - Modern desktop application for service management
- **⚙️ Granular Cache Control** - Fine-tuned caching with HA server strain warnings

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Home Assistant instance with API access
- Docker (optional, for containerized deployment)
- PyQt6 (for control panel UI - automatically installed)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Unknown5436/home-assistant-bridge-service.git
   cd home-assistant-bridge-service
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
   # Start the service (handles port conflicts automatically)
   python start.py
   
   # Stop the service
   python stop.py
   ```

   The `start.py` script will automatically detect if port 8000 is in use and offer to terminate the conflicting process.

5. **Launch the Control Panel (Optional):**

   ```bash
   # Show main window
   python ui_launcher.py --startup-mode show_window

   # Start minimized to system tray
   python ui_launcher.py --minimized

   # Auto-start service and show window
   python ui_launcher.py --auto-start-service --startup-mode show_window
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t ha-bridge .
docker run -p 8000:8000 --env-file .env ha-bridge
```

## 🖥️ Control Panel UI

The service includes a modern desktop control panel for easy management:

### Features

- **Service Status Monitoring** - Real-time status, uptime, and PID display
- **Service Controls** - Start, stop, restart, and test connection
- **Cache Management** - Granular control over caching with Home Assistant server strain warnings
- **Startup Configuration** - Windows login startup and behavior settings
- **Real-time Logs** - Live service logs with auto-refresh
- **System Tray Integration** - Background operation with status icon
- **Modern Dark Theme** - Clean, professional interface

### Usage

```bash
# Launch with main window visible
python ui_launcher.py --startup-mode show_window

# Start minimized to system tray
python ui_launcher.py --minimized

# Auto-start service if not running
python ui_launcher.py --auto-start-service

# Show all options
python ui_launcher.py --help
```

### Cache Control

The UI provides detailed cache management:

- **Bulk Endpoints** (Recommended) - `/all` endpoints with efficient caching
- **Individual Endpoints** (Use with Caution) - Per-entity caching with warnings
- **Home Assistant Server Strain** - Clear warnings about increased server load
- **Real-time Application** - Changes require service restart

For detailed UI documentation, see [UI_README.md](UI_README.md).

## ⚙️ Configuration

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

## 📚 API Documentation

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

## 🏗️ Architecture

### Components

1. **FastAPI Application** - Main web framework
2. **Authentication Middleware** - API key validation and rate limiting
3. **Home Assistant Client** - REST API client for HA communication
4. **WebSocket Client** - Real-time updates from HA
5. **Cache Manager** - In-memory caching with TTL
6. **Metrics Collector** - Prometheus metrics for monitoring
7. **Route Handlers** - API endpoint implementations
8. **Control Panel UI** - PyQt6 desktop application for service management
9. **UI Configuration Manager** - Dynamic settings management
10. **Service Controller** - Process lifecycle management
11. **Startup Manager** - Windows startup integration

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

## 📊 Monitoring

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

## 🧪 Development

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

## 🔧 Troubleshooting

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

4. **Port 8000 already in use:**

   The service will automatically detect port conflicts. When running `python start.py`, you'll be prompted to kill the conflicting process. Alternatively:
   
   ```bash
   # Use stop.py to cleanly shutdown
   python stop.py
   
   # Or manually kill the process (Windows)
   netstat -ano | findstr :8000
   taskkill /PID <pid> /F
   
   # Or manually kill the process (Linux/Mac)
   lsof -i :8000
   kill <pid>
   ```

5. **Service call API returns 404 errors:**

   Ensure you're using the correct endpoint format with proper JSON structure:
   
   ```json
   POST /api/v1/services/{domain}/{service}
   {
     "service_data": {
       "entity_id": "light.bedroom_ceiling_fan"
     }
   }
   ```

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub
4. Check Home Assistant community forums for HA-specific issues

## 🌟 Features Roadmap

- [x] Desktop control panel UI
- [x] Granular cache management
- [x] System tray integration
- [x] Windows startup management
- [ ] Redis caching backend
- [ ] Database persistence for metrics
- [ ] Advanced automation triggers
- [ ] Multi-instance HA support
- [ ] GraphQL API support
- [ ] Mobile app integration
- [ ] Voice control integration

---

**Made with ❤️ for the Home Assistant community**
