#!/usr/bin/env python3
"""
Home Assistant Bridge Service Stop Script

This script cleanly stops a running service instance.
"""

import sys
import subprocess
import time
from pathlib import Path


def read_pid_file() -> int:
    """Read the PID from the pid file."""
    pid_file = Path("service.pid")
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except Exception:
            pass
    return None


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        else:
            import os
            import signal
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    except Exception:
        return False


def kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            import os
            import signal
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
        return True
    except Exception as e:
        print(f"✗ Failed to kill process: {e}")
        return False


def cleanup_pid_file():
    """Remove the PID file."""
    pid_file = Path("service.pid")
    if pid_file.exists():
        pid_file.unlink()
        print("✓ Cleaned up service.pid file")


def main():
    """Main stop function."""
    print("╔" + "═" * 48 + "╗")
    print("║  Home Assistant Bridge Service - Stop         ║")
    print("╚" + "═" * 48 + "╝")
    print()

    # Read PID from file
    pid = read_pid_file()
    
    if not pid:
        print("✗ No service.pid file found")
        print("  Service may not be running or was started manually")
        
        # Try to find and kill any uvicorn processes
        print()
        print("⚠ Searching for running uvicorn processes...")
        
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True
                )
                
                # Look for processes with uvicorn
                found_any = False
                for line in result.stdout.split('\n'):
                    if 'uvicorn' in line.lower() or '8000' in line:
                        found_any = True
                        print(f"  Found: {line.strip()}")
                
                if found_any:
                    print()
                    response = input("  Kill all python processes? (y/n): ").strip().lower()
                    if response == 'y':
                        subprocess.run(["taskkill", "/F", "/IM", "python.exe"], check=False)
                        print("✓ Killed all Python processes")
                else:
                    print("  No uvicorn processes found")
                    
            except Exception as e:
                print(f"  Error searching for processes: {e}")
        
        sys.exit(1)

    print(f"📋 Found service PID: {pid}")
    
    # Check if process is running
    if not is_process_running(pid):
        print(f"✗ Process {pid} is not running")
        cleanup_pid_file()
        sys.exit(0)

    print(f"■ Stopping process {pid}...")
    
    if kill_process(pid):
        # Wait a moment and verify
        time.sleep(1)
        if not is_process_running(pid):
            print(f"✓ Service stopped successfully")
            cleanup_pid_file()
        else:
            print(f"⚠ Process may still be running")
    else:
        print(f"✗ Failed to stop service")
        sys.exit(1)


if __name__ == "__main__":
    main()

