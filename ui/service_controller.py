"""
Service Controller for HA Bridge
Handles starting, stopping, and monitoring the bridge service
"""

import subprocess
import psutil
import time
import os
import signal
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ServiceController:
    """Controls the HA Bridge service process"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.pid_file = self.project_root / "service.pid"
        self.log_file = self.project_root / "service.log"
        self.start_script = self.project_root / "start.py"
        self.service_url = "http://127.0.0.1:8000"
        self.process: Optional[psutil.Process] = None
        self.start_time: Optional[datetime] = None
        self._ws_status_cache: Optional[Dict[str, Any]] = None
        self._ws_status_cache_time: Optional[datetime] = None
        self._ws_cache_ttl = timedelta(seconds=5)  # Cache WebSocket status for 5 seconds

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        status = {
            "running": False,
            "pid": None,
            "uptime": None,
            "health": False,
            "url": self.service_url,
            "error": None,
        }

        try:
            # Check if PID file exists and process is running
            if self.pid_file.exists():
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())

                try:
                    self.process = psutil.Process(pid)
                    if (
                        self.process.is_running()
                        and self.process.status() != psutil.STATUS_ZOMBIE
                    ):
                        status["running"] = True
                        status["pid"] = pid

                        # Calculate uptime
                        create_time = datetime.fromtimestamp(self.process.create_time())
                        status["uptime"] = str(datetime.now() - create_time).split(".")[
                            0
                        ]

                        # Check health endpoint
                        status["health"] = self._check_health()

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process doesn't exist or we can't access it
                    self._cleanup_pid_file()

        except (ValueError, FileNotFoundError):
            # PID file doesn't exist or is invalid
            pass

        return status

    def _check_health(self) -> bool:
        """Check if service is responding to health endpoint"""
        try:
            import requests

            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _cleanup_pid_file(self):
        """Remove stale PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.info("Cleaned up stale PID file")
        except Exception as e:
            logger.error(f"Failed to cleanup PID file: {e}")

    def start_service(self) -> Dict[str, Any]:
        """Start the bridge service"""
        result = {"success": False, "message": "", "pid": None}

        try:
            # Check if already running
            status = self.get_service_status()
            if status["running"]:
                result["message"] = "Service is already running"
                result["pid"] = status["pid"]
                return result

            # Start the service
            if not self.start_script.exists():
                result["message"] = f"Start script not found: {self.start_script}"
                return result

            # Start process
            with open(self.log_file, "a", encoding="utf-8", errors="replace") as log_f:
                # Set environment to prevent encoding issues
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                process = subprocess.Popen(
                    ["python", str(self.start_script)],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.project_root),
                    env=env,
                    creationflags=(
                        subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                    ),
                )

            # Save PID
            with open(self.pid_file, "w") as f:
                f.write(str(process.pid))

            # Wait a moment for startup
            time.sleep(2)

            # Verify it started
            status = self.get_service_status()
            if status["running"]:
                result["success"] = True
                result["message"] = "Service started successfully"
                result["pid"] = status["pid"]
                self.start_time = datetime.now()
            else:
                result["message"] = "Service failed to start"
                self._cleanup_pid_file()

        except Exception as e:
            result["message"] = f"Failed to start service: {str(e)}"
            logger.error(f"Service start error: {e}")

        return result

    def stop_service(self) -> Dict[str, Any]:
        """Stop the bridge service gracefully"""
        result = {"success": False, "message": ""}

        try:
            status = self.get_service_status()
            if not status["running"]:
                result["message"] = "Service is not running"
                return result

            # Get the process
            if self.pid_file.exists():
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())

                try:
                    process = psutil.Process(pid)

                    # Try graceful shutdown first
                    if os.name == "nt":
                        # Windows
                        process.terminate()
                    else:
                        # Unix
                        process.send_signal(signal.SIGTERM)

                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        # Force kill if graceful shutdown failed
                        process.kill()
                        process.wait()

                    result["success"] = True
                    result["message"] = "Service stopped successfully"

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    result["message"] = "Service process not found or access denied"

            # Cleanup
            self._cleanup_pid_file()

        except Exception as e:
            result["message"] = f"Failed to stop service: {str(e)}"
            logger.error(f"Service stop error: {e}")

        return result

    def restart_service(self) -> Dict[str, Any]:
        """Restart the bridge service"""
        result = {"success": False, "message": ""}

        try:
            # Stop first
            stop_result = self.stop_service()
            if (
                not stop_result["success"]
                and "not running" not in stop_result["message"]
            ):
                result["message"] = f"Failed to stop service: {stop_result['message']}"
                return result

            # Wait a moment
            time.sleep(1)

            # Start again
            start_result = self.start_service()
            if start_result["success"]:
                result["success"] = True
                result["message"] = "Service restarted successfully"
            else:
                result["message"] = (
                    f"Failed to restart service: {start_result['message']}"
                )

        except Exception as e:
            result["message"] = f"Failed to restart service: {str(e)}"
            logger.error(f"Service restart error: {e}")

        return result

    def get_service_logs(self, lines: int = 100) -> List[str]:
        """Get recent service logs"""
        logs = []

        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                    logs = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    logs = [line.rstrip() for line in logs]
            else:
                logs = ["No log file found"]

        except Exception as e:
            logs = [f"Error reading logs: {str(e)}"]
            logger.error(f"Failed to read logs: {e}")

        return logs

    def clear_logs(self) -> bool:
        """Clear service logs by truncating them (handles file locking gracefully)"""
        try:
            if self.log_file.exists():
                # Try to truncate the file instead of deleting it
                # This is less likely to fail due to file locking
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.truncate(0)
                logger.info("Service logs cleared")
                return True
            return True  # File doesn't exist, consider it "cleared"
        except PermissionError as e:
            logger.warning(f"Cannot clear logs - file is locked by another process: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            return False

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the service"""
        result = {
            "success": False,
            "message": "",
            "response_time": None,
            "status_code": None,
        }

        try:
            import requests

            start_time = time.time()
            response = requests.get(f"{self.service_url}/health", timeout=10)
            response_time = time.time() - start_time

            result["response_time"] = round(response_time * 1000, 2)  # ms
            result["status_code"] = response.status_code

            if response.status_code == 200:
                result["success"] = True
                result["message"] = (
                    f"Connection successful ({result['response_time']}ms)"
                )
            else:
                result["message"] = (
                    f"Service responded with status {response.status_code}"
                )

        except requests.exceptions.ConnectionError:
            result["message"] = "Connection refused - service may not be running"
        except requests.exceptions.Timeout:
            result["message"] = "Connection timeout - service may be overloaded"
        except Exception as e:
            result["message"] = f"Connection test failed: {str(e)}"

        return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get detailed service information"""
        status = self.get_service_status()
        info = {
            "status": status,
            "project_root": str(self.project_root),
            "start_script": str(self.start_script),
            "log_file": str(self.log_file),
            "pid_file": str(self.pid_file),
        }

        if status["running"] and self.process:
            try:
                info["memory_usage"] = (
                    self.process.memory_info().rss / 1024 / 1024
                )  # MB
                info["cpu_percent"] = self.process.cpu_percent()
                info["num_threads"] = self.process.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return info

    def get_websocket_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status from service (with caching)."""
        # Check if cache is still valid
        now = datetime.now()
        if (
            self._ws_status_cache is not None
            and self._ws_status_cache_time is not None
            and (now - self._ws_status_cache_time) < self._ws_cache_ttl
        ):
            return self._ws_status_cache
        
        # Cache expired or doesn't exist, fetch new status
        try:
            import requests

            response = requests.get(f"{self.service_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                ws_status = data.get(
                    "websocket",
                    {"connected": False, "error": "WebSocket info not available"},
                )
                # Update cache
                self._ws_status_cache = ws_status
                self._ws_status_cache_time = now
                return ws_status
        except Exception as e:
            logger.error(f"Failed to get WebSocket status: {e}")

        error_status = {"connected": False, "error": "Service not responding"}
        # Cache error status too to avoid repeated timeouts
        self._ws_status_cache = error_status
        self._ws_status_cache_time = now
        return error_status
