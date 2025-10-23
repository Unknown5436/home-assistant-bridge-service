# HA Bridge Control UI

A modern, dark-mode system tray application for managing the Home Assistant Bridge Service.

## Features

- **System Tray Integration**: Runs in the system tray with colored status indicators
- **Service Control**: Start, stop, and restart the bridge service
- **Cache Management**: Enable/disable caching for different API endpoints
- **Startup Control**: Configure Windows startup behavior
- **Live Logs**: View service logs in real-time with filtering
- **Metrics Dashboard**: Real-time performance monitoring with charts and health indicators
- **Modern Dark UI**: Clean, minimalist dark theme interface
- **Real-time Monitoring**: Automatic service status updates

## Quick Start

### Prerequisites

- Python 3.7+
- PyQt6
- psutil
- matplotlib (for metrics charts)
- numpy (for data processing)
- All bridge service dependencies

### Installation

1. Install UI dependencies:

```bash
pip install PyQt6 psutil Pillow matplotlib numpy
```

2. Run the control panel:

```bash
python ui_launcher.py
```

### Command Line Options

```bash
python ui_launcher.py [options]

Options:
  --minimized              Start minimized to system tray
  --startup-mode MODE      Startup behavior (minimized/show_window/show_then_minimize)
  --auto-start-service     Automatically start bridge service if not running
  --debug                  Enable debug logging
```

## Usage

### System Tray

- **Left-click**: Show context menu
- **Double-click**: Open control panel window
- **Right-click**: Show context menu

### Control Panel

The main window provides:

1. **Service Status Section**

   - Real-time service status (Running/Stopped)
   - Service URL and uptime
   - Control buttons (Start/Stop/Restart/Test)

2. **Cache Control Section**

   - Toggle caching for States API
   - Toggle caching for Services API
   - Toggle caching for Config API
   - Apply changes button

3. **Startup Settings Section**

   - Enable/disable Windows startup
   - Choose startup behavior

4. **Logs Viewer Section**
   - Real-time service logs
   - Auto-refresh toggle
   - Clear logs button

### Configuration

Settings are automatically saved to `ui_settings.json`:

```json
{
  "cache": {
    "states_enabled": true,
    "services_enabled": true,
    "config_enabled": true
  },
  "startup": {
    "run_on_login": false,
    "startup_behavior": "minimized"
  },
  "window": {
    "last_position": [100, 100],
    "last_size": [800, 600]
  },
  "service": {
    "auto_start": true
  }
}
```

## Metrics Dashboard

The UI now includes a comprehensive metrics dashboard accessible via the "Metrics Dashboard" tab.

### Features

- **Real-time Performance Monitoring**: Live charts showing response times, request rates, and error rates
- **Service Health Overview**: Overall health score with connection status indicators
- **Key Metrics Display**: Response time, request rate, error rate, cache hit rate, and uptime
- **Interactive Charts**: Switch between different chart types (Response Time, Request Rate, Error Rate, Cache Hit Rate)
- **Issue Detection**: Automatic detection and display of service issues
- **Auto-refresh**: Configurable automatic data refresh every 5 seconds

### Chart Types

1. **Response Time**: Shows average response time over time with target lines
2. **Request Rate**: Displays requests per minute with trend analysis
3. **Error Rate**: Monitors error percentage with warning/critical thresholds
4. **Cache Hit Rate**: Tracks cache performance with target indicators

### Health Indicators

- **Health Score**: 0-100 score based on multiple factors
- **HA Connection**: Real-time Home Assistant connection status
- **WebSocket Status**: WebSocket connection monitoring
- **Issue Alerts**: Automatic detection of performance issues

### Usage

1. **Access**: Click the "Metrics Dashboard" tab in the main window
2. **Auto-refresh**: Toggle auto-refresh on/off as needed
3. **Manual Refresh**: Use "Refresh Now" button for immediate updates
4. **Chart Selection**: Choose different chart types from the dropdown
5. **Issue Monitoring**: Check the "Recent Issues" section for alerts

### Data Sources

The dashboard fetches data from:

- `/status` endpoint: Service status and connection information
- `/metrics` endpoint: Prometheus-formatted metrics data

## Architecture

### Components

- **`ui_launcher.py`**: Main entry point with command line parsing
- **`ui/tray_app.py`**: System tray application with menu
- **`ui/main_window.py`**: Main control panel window with tabbed interface
- **`ui/metrics_panel.py`**: Real-time metrics dashboard component
- **`ui/service_controller.py`**: Service management (start/stop/restart)
- **`ui/startup_manager.py`**: Windows startup management
- **`ui/assets/icons/`**: System tray icons
- **`app/config/ui_config.py`**: UI settings management

### Integration

The UI integrates with the bridge service through:

1. **Dynamic Caching**: Cache settings are read from UI config and applied to API endpoints
2. **Service Control**: Direct process management for start/stop/restart
3. **Configuration**: Persistent settings storage and retrieval
4. **Monitoring**: Real-time status updates and log viewing

## Development

### Testing

Run the component test suite:

```bash
python test_ui_components.py
```

### Adding Features

1. **New UI Components**: Add to `ui/` directory
2. **Service Integration**: Extend `ServiceController` class
3. **Settings**: Add to `UISettings` dataclass in `ui_config.py`
4. **Icons**: Add to `ui/assets/icons/` directory

### Debugging

Enable debug logging:

```bash
python ui_launcher.py --debug
```

Logs are written to `ui.log` and console output.

## Troubleshooting

### Common Issues

1. **Missing Dependencies**

   - Error: `ModuleNotFoundError: No module named 'PyQt6'`
   - Solution: `pip install PyQt6 psutil`

2. **Service Won't Start**

   - Check if port 8000 is available
   - Verify Home Assistant connection settings
   - Check service logs in the UI

3. **System Tray Not Showing**

   - Ensure system tray is enabled in Windows
   - Check if antivirus is blocking the application

4. **Startup Not Working**
   - Run as administrator to modify registry
   - Check Windows startup folder permissions

### Log Files

- **UI Logs**: `ui.log`
- **Service Logs**: `service.log`
- **Bridge Logs**: Check bridge service logs

## License

Same as the main HA Bridge project.
