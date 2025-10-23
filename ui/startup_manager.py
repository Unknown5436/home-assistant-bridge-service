"""
Windows Startup Manager for HA Bridge Control UI
Handles adding/removing the application from Windows startup
"""

import os
import sys
import winreg
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StartupManager:
    """Manages Windows startup registry entries"""

    def __init__(self, app_name: str = "HABridgeService"):
        self.app_name = app_name
        self.registry_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.startup_folder = self._get_startup_folder()

    def _get_startup_folder(self) -> Path:
        """Get the Windows startup folder path"""
        try:
            # Get user's startup folder
            startup_folder = (
                Path(os.environ.get("APPDATA", ""))
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Startup"
            )
            return startup_folder
        except Exception as e:
            logger.error(f"Failed to get startup folder: {e}")
            return (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Startup"
            )

    def _get_app_path(self) -> str:
        """Get the full path to the UI launcher"""
        try:
            # Get the path to ui_launcher.py
            current_dir = Path(__file__).parent.parent  # Go up from ui/ to project root
            launcher_path = current_dir / "ui_launcher.py"

            # Use pythonw.exe to run without console window
            pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
            return f'"{pythonw_path}" "{launcher_path}" --minimized'

        except Exception as e:
            logger.error(f"Failed to get app path: {e}")
            return ""

    def is_startup_enabled(self) -> bool:
        """Check if the application is set to run on startup"""
        try:
            # Check registry
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, self.app_name)
                    return bool(value)
                except FileNotFoundError:
                    # Key doesn't exist
                    return False

        except Exception as e:
            logger.error(f"Failed to check startup status: {e}")
            return False

    def enable_startup(self) -> bool:
        """Enable startup on Windows login"""
        try:
            app_path = self._get_app_path()
            if not app_path:
                logger.error("Failed to get application path")
                return False

            # Add to registry
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, app_path)

            logger.info("Startup enabled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to enable startup: {e}")
            return False

    def disable_startup(self) -> bool:
        """Disable startup on Windows login"""
        try:
            # Remove from registry
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_SET_VALUE
            ) as key:
                try:
                    winreg.DeleteValue(key, self.app_name)
                    logger.info("Startup disabled successfully")
                    return True
                except FileNotFoundError:
                    # Value doesn't exist, which is fine
                    logger.info("Startup was not enabled")
                    return True

        except Exception as e:
            logger.error(f"Failed to disable startup: {e}")
            return False

    def toggle_startup(self) -> bool:
        """Toggle startup setting"""
        if self.is_startup_enabled():
            return self.disable_startup()
        else:
            return self.enable_startup()

    def get_startup_info(self) -> dict:
        """Get detailed startup information"""
        info = {
            "enabled": self.is_startup_enabled(),
            "app_name": self.app_name,
            "registry_key": self.registry_key,
            "startup_folder": str(self.startup_folder),
            "app_path": self._get_app_path(),
        }

        # Try to get the actual registry value
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, self.app_name)
                    info["registry_value"] = value
                except FileNotFoundError:
                    info["registry_value"] = None
        except Exception as e:
            info["registry_error"] = str(e)

        return info

    def create_startup_shortcut(self) -> bool:
        """Alternative method: Create shortcut in startup folder"""
        try:
            import winshell
            from win32com.client import Dispatch

            app_path = self._get_app_path()
            if not app_path:
                return False

            # Create shortcut
            shortcut_path = self.startup_folder / f"{self.app_name}.lnk"
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = app_path.split('"')[1]  # Remove quotes
            shortcut.Arguments = "--minimized"
            shortcut.WorkingDirectory = str(Path(__file__).parent.parent)
            shortcut.save()

            logger.info(f"Created startup shortcut: {shortcut_path}")
            return True

        except ImportError:
            logger.warning("winshell not available, using registry method only")
            return False
        except Exception as e:
            logger.error(f"Failed to create startup shortcut: {e}")
            return False

    def remove_startup_shortcut(self) -> bool:
        """Remove shortcut from startup folder"""
        try:
            shortcut_path = self.startup_folder / f"{self.app_name}.lnk"
            if shortcut_path.exists():
                shortcut_path.unlink()
                logger.info("Removed startup shortcut")
                return True
            return True  # Already removed

        except Exception as e:
            logger.error(f"Failed to remove startup shortcut: {e}")
            return False


# Test function
def test_startup_manager():
    """Test the startup manager functionality"""
    manager = StartupManager()

    print("Startup Manager Test")
    print("=" * 50)

    # Get current status
    info = manager.get_startup_info()
    print(f"Current startup status: {info['enabled']}")
    print(f"App name: {info['app_name']}")
    print(f"Registry key: {info['registry_key']}")
    print(f"App path: {info['app_path']}")

    # Test toggle
    print("\nTesting startup toggle...")
    if manager.toggle_startup():
        print("✓ Startup toggled successfully")
    else:
        print("✗ Failed to toggle startup")

    # Check new status
    new_status = manager.is_startup_enabled()
    print(f"New startup status: {new_status}")


if __name__ == "__main__":
    test_startup_manager()
