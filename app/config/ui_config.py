"""
UI Configuration Management for HA Bridge Control Panel
Handles loading/saving UI settings and cache configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheSettings:
    """Cache configuration settings"""

    states_enabled: bool = True
    services_enabled: bool = True
    config_enabled: bool = True
    states_individual_enabled: bool = (
        False  # Individual state lookups - disabled by default
    )
    services_individual_enabled: bool = (
        False  # Individual service lookups - disabled by default
    )


@dataclass
class StartupSettings:
    """Startup behavior settings"""

    run_on_login: bool = False
    startup_behavior: str = (
        "minimized"  # "minimized", "show_window", "show_then_minimize"
    )


@dataclass
class WindowSettings:
    """Window state settings"""

    last_position: list = None
    last_size: list = None

    def __post_init__(self):
        if self.last_position is None:
            self.last_position = [100, 100]
        if self.last_size is None:
            self.last_size = [800, 600]


@dataclass
class ServiceSettings:
    """Service control settings"""

    auto_start: bool = True


@dataclass
class LogSettings:
    """Log management settings"""

    clear_on_startup: bool = False  # Clear logs when starting the UI


@dataclass
class UISettings:
    """Complete UI settings structure"""

    cache: CacheSettings = None
    startup: StartupSettings = None
    window: WindowSettings = None
    service: ServiceSettings = None
    logs: LogSettings = None

    def __post_init__(self):
        if self.cache is None:
            self.cache = CacheSettings()
        if self.startup is None:
            self.startup = StartupSettings()
        if self.window is None:
            self.window = WindowSettings()
        if self.service is None:
            self.service = ServiceSettings()
        if self.logs is None:
            self.logs = LogSettings()


class UIConfigManager:
    """Manages UI configuration loading and saving"""

    def __init__(self, config_file: str = "ui_settings.json"):
        self.config_file = Path(config_file)
        self.settings = UISettings()
        self.load_settings()

    def load_settings(self) -> UISettings:
        """Load settings from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Convert dict data back to dataclasses
                cache_data = data.get("cache", {})
                startup_data = data.get("startup", {})
                window_data = data.get("window", {})
                service_data = data.get("service", {})
                logs_data = data.get("logs", {})

                self.settings = UISettings(
                    cache=CacheSettings(**cache_data),
                    startup=StartupSettings(**startup_data),
                    window=WindowSettings(**window_data),
                    service=ServiceSettings(**service_data),
                    logs=LogSettings(**logs_data),
                )

                logger.info("UI settings loaded successfully")
            else:
                logger.info("No UI settings file found, using defaults")
                self.save_settings()  # Create default file

        except Exception as e:
            logger.error(f"Failed to load UI settings: {e}")
            self.settings = UISettings()  # Use defaults

        return self.settings

    def save_settings(self) -> bool:
        """Save settings to JSON file"""
        try:
            # Convert dataclasses to dict for JSON serialization
            data = {
                "cache": asdict(self.settings.cache),
                "startup": asdict(self.settings.startup),
                "window": asdict(self.settings.window),
                "service": asdict(self.settings.service),
                "logs": asdict(self.settings.logs),
            }

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info("UI settings saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save UI settings: {e}")
            return False

    def get_cache_setting(self, cache_type: str) -> bool:
        """Get cache setting for specific type"""
        if cache_type == "states":
            return self.settings.cache.states_enabled
        elif cache_type == "services":
            return self.settings.cache.services_enabled
        elif cache_type == "config":
            return self.settings.cache.config_enabled
        elif cache_type == "states_individual":
            return self.settings.cache.states_individual_enabled
        elif cache_type == "services_individual":
            return self.settings.cache.services_individual_enabled
        else:
            logger.warning(f"Unknown cache type: {cache_type}")
            return True

    def set_cache_setting(self, cache_type: str, enabled: bool) -> bool:
        """Set cache setting for specific type"""
        try:
            if cache_type == "states":
                self.settings.cache.states_enabled = enabled
            elif cache_type == "services":
                self.settings.cache.services_enabled = enabled
            elif cache_type == "config":
                self.settings.cache.config_enabled = enabled
            elif cache_type == "states_individual":
                self.settings.cache.states_individual_enabled = enabled
            elif cache_type == "services_individual":
                self.settings.cache.services_individual_enabled = enabled
            else:
                logger.warning(f"Unknown cache type: {cache_type}")
                return False

            return self.save_settings()

        except Exception as e:
            logger.error(f"Failed to set cache setting: {e}")
            return False

    def get_startup_setting(self, setting: str) -> Any:
        """Get startup setting"""
        if setting == "run_on_login":
            return self.settings.startup.run_on_login
        elif setting == "startup_behavior":
            return self.settings.startup.startup_behavior
        else:
            logger.warning(f"Unknown startup setting: {setting}")
            return None

    def set_startup_setting(self, setting: str, value: Any) -> bool:
        """Set startup setting"""
        try:
            if setting == "run_on_login":
                self.settings.startup.run_on_login = value
            elif setting == "startup_behavior":
                self.settings.startup.startup_behavior = value
            else:
                logger.warning(f"Unknown startup setting: {setting}")
                return False

            return self.save_settings()

        except Exception as e:
            logger.error(f"Failed to set startup setting: {e}")
            return False

    def update_window_settings(self, position: tuple, size: tuple) -> bool:
        """Update window position and size"""
        try:
            self.settings.window.last_position = list(position)
            self.settings.window.last_size = list(size)
            return self.save_settings()
        except Exception as e:
            logger.error(f"Failed to update window settings: {e}")
            return False

    def get_log_setting(self, setting: str) -> Any:
        """Get log setting"""
        if setting == "clear_on_startup":
            return self.settings.logs.clear_on_startup
        else:
            logger.warning(f"Unknown log setting: {setting}")
            return None

    def set_log_setting(self, setting: str, value: bool) -> bool:
        """Set log setting"""
        try:
            if setting == "clear_on_startup":
                self.settings.logs.clear_on_startup = value
            else:
                logger.warning(f"Unknown log setting: {setting}")
                return False

            return self.save_settings()

        except Exception as e:
            logger.error(f"Failed to set log setting: {e}")
            return False

    def get_all_settings(self) -> UISettings:
        """Get all current settings"""
        return self.settings

    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        try:
            self.settings = UISettings()
            return self.save_settings()
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            return False

    def get_groupbox_style(self) -> str:
        """Get styling for QGroupBox widgets"""
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """

    def get_button_style(self) -> str:
        """Get styling for QPushButton widgets"""
        return """
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """

    def get_label_style(self) -> str:
        """Get styling for QLabel widgets"""
        return """
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
        """


# Global instance for easy access
ui_config = UIConfigManager()
