#!/usr/bin/env python3
"""
Home Assistant Bridge Service Startup Script

This script provides an easy way to start the service with proper configuration.
"""

import os
import sys
import subprocess
import socket
import time
import signal
from pathlib import Path


def check_requirements():
    """Check if all requirements are installed."""
    try:
        import fastapi
        import httpx
        import structlog
        import prometheus_client

        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("  Please run: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")
        return True
    else:
        print("✗ .env file not found")
        print("  Please copy env.example to .env and configure it")
        return False


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_process_on_port(port: int) -> int:
    """Find the PID of the process using the specified port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.split('\n'):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        return int(pid)
    except Exception:
        pass
    return None


def kill_process_on_port(port: int) -> bool:
    """Kill the process using the specified port."""
    pid = find_process_on_port(port)
    if pid:
        try:
            print(f"⚠ Port {port} is in use by PID {pid}")
            response = input(f"  Kill process {pid}? (y/n): ").strip().lower()
            if response == 'y':
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
                else:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                print(f"✓ Killed process {pid}")
                return True
            else:
                print("  Startup cancelled by user")
                return False
        except Exception as e:
            print(f"✗ Failed to kill process: {e}")
            return False
    return True


def write_pid_file(pid: int):
    """Write the process PID to a file for tracking."""
    pid_file = Path("service.pid")
    pid_file.write_text(str(pid))
    print(f"✓ Service PID {pid} written to service.pid")


def read_pid_file() -> int:
    """Read the PID from the pid file."""
    pid_file = Path("service.pid")
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except Exception:
            pass
    return None


def cleanup_pid_file():
    """Remove the PID file."""
    pid_file = Path("service.pid")
    if pid_file.exists():
        pid_file.unlink()


def main():
    """Main startup function."""
    print("╔" + "═" * 48 + "╗")
    print("║  Home Assistant Bridge Service - Startup      ║")
    print("╚" + "═" * 48 + "╝")
    print()

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check environment file
    if not check_env_file():
        sys.exit(1)

    # Check if port is in use
    port = 8000
    if is_port_in_use(port):
        print()
        if not kill_process_on_port(port):
            sys.exit(1)
        # Wait a moment for port to be released
        time.sleep(2)
        if is_port_in_use(port):
            print(f"✗ Port {port} is still in use")
            sys.exit(1)

    # Start the service
    print()
    print("▶ Starting service on http://0.0.0.0:8000")
    print("  Press CTRL+C to stop")
    print()
    
    process = None
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
                "--reload",
            ]
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Write PID file
        write_pid_file(process.pid)
        
        # Wait for process to complete
        process.wait()
        
    except KeyboardInterrupt:
        print()
        print("■ Service stopped by user")
        if process:
            process.terminate()
            process.wait(timeout=5)
    except Exception as e:
        print(f"✗ Service failed: {e}")
        sys.exit(1)
    finally:
        cleanup_pid_file()


if __name__ == "__main__":
    main()
