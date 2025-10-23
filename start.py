#!/usr/bin/env python3
"""
Home Assistant Bridge Service Startup Script

This script provides an easy way to start the service with proper configuration.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if all requirements are installed."""
    try:
        import fastapi
        import httpx
        import structlog
        import prometheus_client

        print("All required packages are installed")
        return True
    except ImportError as e:
        print("Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if env_file.exists():
        print(".env file found")
        return True
    else:
        print(".env file not found")
        print("Please copy env.example to .env and configure it")
        return False


def main():
    """Main startup function."""
    print("Starting Home Assistant Bridge Service")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check environment file
    if not check_env_file():
        sys.exit(1)

    # Start the service
    print("\n[*] Starting service...")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n[!] Service stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n[X] Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
