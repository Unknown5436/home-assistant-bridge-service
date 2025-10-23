"""
Main Control Window for HA Bridge Control UI
Modern dark mode interface for managing the bridge service
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QTextEdit,
    QGroupBox,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

from ui.service_controller import ServiceController
from ui.startup_manager import StartupManager
from app.config.ui_config import ui_config

logger = logging.getLogger(__name__)


class LogViewer(QTextEdit):
    """Custom log viewer with auto-scroll and filtering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        # Note: setMaximumBlockCount is not available in PyQt6
        # We'll handle log limiting differently

        # Setup styling
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
        """
        )

    def append_log(self, message: str):
        """Append a log message"""
        self.append(message)
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        """Clear all logs"""
        self.clear()


class ServiceStatusWidget(QWidget):
    """Widget showing service status and controls"""

    def __init__(self, service_controller: ServiceController, parent=None):
        super().__init__(parent)
        self.service_controller = service_controller
        self.setup_ui()

        # Setup status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # Update every 2 seconds

        # Initial update
        self.update_status()

    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)

        # Status group
        status_group = QGroupBox("Service Status")
        status_layout = QGridLayout(status_group)

        # Status indicator
        self.status_label = QLabel("Unknown")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)

        # Service URL
        self.url_label = QLabel("http://127.0.0.1:8000")
        self.url_label.setStyleSheet("color: #007acc;")
        status_layout.addWidget(QLabel("URL:"), 1, 0)
        status_layout.addWidget(self.url_label, 1, 1)

        # Uptime
        self.uptime_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Uptime:"), 2, 0)
        status_layout.addWidget(self.uptime_label, 2, 1)

        # PID
        self.pid_label = QLabel("N/A")
        status_layout.addWidget(QLabel("PID:"), 3, 0)
        status_layout.addWidget(self.pid_label, 3, 1)

        layout.addWidget(status_group)

        # Control buttons
        control_group = QGroupBox("Service Control")
        control_layout = QHBoxLayout(control_group)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_service)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_service)
        control_layout.addWidget(self.stop_btn)

        self.restart_btn = QPushButton("Restart")
        self.restart_btn.clicked.connect(self.restart_service)
        control_layout.addWidget(self.restart_btn)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        control_layout.addWidget(self.test_btn)

        layout.addWidget(control_group)

        # Connection test result
        self.test_result = QLabel("")
        self.test_result.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        layout.addWidget(self.test_result)

    def update_status(self):
        """Update service status display"""
        try:
            status = self.service_controller.get_service_status()

            # Update status label
            if status["running"]:
                if status["health"]:
                    self.status_label.setText("Running")
                    self.status_label.setStyleSheet(
                        "color: #4ec9b0; font-weight: bold; font-size: 12pt;"
                    )
                else:
                    self.status_label.setText("Running (Unhealthy)")
                    self.status_label.setStyleSheet(
                        "color: #f48771; font-weight: bold; font-size: 12pt;"
                    )
            else:
                self.status_label.setText("Stopped")
                self.status_label.setStyleSheet(
                    "color: #f48771; font-weight: bold; font-size: 12pt;"
                )

            # Update other fields
            self.uptime_label.setText(status.get("uptime", "N/A"))
            self.pid_label.setText(str(status.get("pid", "N/A")))

            # Update button states
            self.start_btn.setEnabled(not status["running"])
            self.stop_btn.setEnabled(status["running"])
            self.restart_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    def start_service(self):
        """Start the service"""
        result = self.service_controller.start_service()
        if result["success"]:
            self.test_result.setText(f"✓ {result['message']}")
            self.test_result.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        else:
            self.test_result.setText(f"✗ {result['message']}")
            self.test_result.setStyleSheet("color: #f48771; font-size: 10pt;")

    def stop_service(self):
        """Stop the service"""
        result = self.service_controller.stop_service()
        if result["success"]:
            self.test_result.setText(f"✓ {result['message']}")
            self.test_result.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        else:
            self.test_result.setText(f"✗ {result['message']}")
            self.test_result.setStyleSheet("color: #f48771; font-size: 10pt;")

    def restart_service(self):
        """Restart the service"""
        result = self.service_controller.restart_service()
        if result["success"]:
            self.test_result.setText(f"✓ {result['message']}")
            self.test_result.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        else:
            self.test_result.setText(f"✗ {result['message']}")
            self.test_result.setStyleSheet("color: #f48771; font-size: 10pt;")

    def test_connection(self):
        """Test connection to service"""
        self.test_result.setText("Testing connection...")
        self.test_result.setStyleSheet("color: #007acc; font-size: 10pt;")

        result = self.service_controller.test_connection()
        if result["success"]:
            self.test_result.setText(f"✓ {result['message']}")
            self.test_result.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        else:
            self.test_result.setText(f"✗ {result['message']}")
            self.test_result.setStyleSheet("color: #f48771; font-size: 10pt;")


class CacheControlWidget(QWidget):
    """Widget for controlling cache settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)

        # Cache control group
        cache_group = QGroupBox("Caching Settings")
        cache_layout = QGridLayout(cache_group)

        # Bulk endpoint section label
        bulk_label = QLabel("Bulk Endpoints (✓ Recommended - Less HA Server Strain):")
        bulk_label.setStyleSheet("color: #4ec9b0; font-weight: bold; margin-top: 5px;")
        cache_layout.addWidget(bulk_label, 0, 0, 1, 2)

        # States API caching (/all)
        self.states_cache = QCheckBox("States API Caching (/all)")
        self.states_cache.stateChanged.connect(self.on_cache_changed)
        cache_layout.addWidget(self.states_cache, 1, 0)

        self.states_ttl = QLabel("TTL: 300s")
        self.states_ttl.setStyleSheet("color: #808080;")
        cache_layout.addWidget(self.states_ttl, 1, 1)

        # Services API caching (/all)
        self.services_cache = QCheckBox("Services API Caching (/all)")
        self.services_cache.stateChanged.connect(self.on_cache_changed)
        cache_layout.addWidget(self.services_cache, 2, 0)

        self.services_ttl = QLabel("TTL: 300s")
        self.services_ttl.setStyleSheet("color: #808080;")
        cache_layout.addWidget(self.services_ttl, 2, 1)

        # Config API caching
        self.config_cache = QCheckBox("Config API Caching")
        self.config_cache.stateChanged.connect(self.on_cache_changed)
        cache_layout.addWidget(self.config_cache, 3, 0)

        self.config_ttl = QLabel("TTL: 300s")
        self.config_ttl.setStyleSheet("color: #808080;")
        cache_layout.addWidget(self.config_ttl, 3, 1)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #404040;")
        cache_layout.addWidget(separator, 4, 0, 1, 2)

        # Individual endpoint section label with warning
        individual_label = QLabel("Individual Endpoints (⚠ Use with Caution):")
        individual_label.setStyleSheet("color: #f48771; font-weight: bold; margin-top: 5px;")
        cache_layout.addWidget(individual_label, 5, 0, 1, 2)

        # Individual states caching
        self.states_individual_cache = QCheckBox("Individual State Lookups (/states/{id})")
        self.states_individual_cache.stateChanged.connect(self.on_cache_changed)
        cache_layout.addWidget(self.states_individual_cache, 6, 0)

        states_warning = QLabel("⚠ May delay state updates")
        states_warning.setStyleSheet("color: #f48771; font-size: 8pt; font-style: italic;")
        cache_layout.addWidget(states_warning, 6, 1)

        # Individual services caching
        self.services_individual_cache = QCheckBox("Individual Service Lookups (/services/{domain})")
        self.services_individual_cache.stateChanged.connect(self.on_cache_changed)
        cache_layout.addWidget(self.services_individual_cache, 7, 0)

        services_warning = QLabel("⚠ May show stale services")
        services_warning.setStyleSheet("color: #f48771; font-size: 8pt; font-style: italic;")
        cache_layout.addWidget(services_warning, 7, 1)

        # Info note
        info_note = QLabel(
            "ⓘ Disabling caching increases strain on your Home Assistant server (more frequent requests). "
            "Individual endpoint caching reduces server load but may show stale data. "
            "Bulk endpoints are most efficient when uncached."
        )
        info_note.setStyleSheet("color: #808080; font-size: 8pt; margin-top: 10px;")
        info_note.setWordWrap(True)
        cache_layout.addWidget(info_note, 8, 0, 1, 2)

        layout.addWidget(cache_group)

        # Apply button
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """
        )
        layout.addWidget(self.apply_btn)

        # Status message
        self.status_msg = QLabel("")
        self.status_msg.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        layout.addWidget(self.status_msg)

    def load_settings(self):
        """Load current cache settings"""
        try:
            settings = ui_config.get_all_settings()
            
            # Block signals during initial load to prevent "Settings changed" message
            self.states_cache.blockSignals(True)
            self.services_cache.blockSignals(True)
            self.config_cache.blockSignals(True)
            self.states_individual_cache.blockSignals(True)
            self.services_individual_cache.blockSignals(True)
            
            # Set checkbox states
            self.states_cache.setChecked(settings.cache.states_enabled)
            self.services_cache.setChecked(settings.cache.services_enabled)
            self.config_cache.setChecked(settings.cache.config_enabled)
            self.states_individual_cache.setChecked(settings.cache.states_individual_enabled)
            self.services_individual_cache.setChecked(settings.cache.services_individual_enabled)
            
            # Re-enable signals
            self.states_cache.blockSignals(False)
            self.services_cache.blockSignals(False)
            self.config_cache.blockSignals(False)
            self.states_individual_cache.blockSignals(False)
            self.services_individual_cache.blockSignals(False)
        except Exception as e:
            logger.error(f"Failed to load cache settings: {e}")

    def on_cache_changed(self):
        """Handle cache setting changes"""
        self.status_msg.setText("Settings changed - click Apply to save")
        self.status_msg.setStyleSheet("color: #f48771; font-size: 10pt;")

    def apply_changes(self):
        """Apply cache setting changes"""
        try:
            # Save settings
            ui_config.set_cache_setting("states", self.states_cache.isChecked())
            ui_config.set_cache_setting("services", self.services_cache.isChecked())
            ui_config.set_cache_setting("config", self.config_cache.isChecked())
            ui_config.set_cache_setting("states_individual", self.states_individual_cache.isChecked())
            ui_config.set_cache_setting("services_individual", self.services_individual_cache.isChecked())

            self.status_msg.setText("✓ Settings saved successfully - Restart service to apply")
            self.status_msg.setStyleSheet("color: #4ec9b0; font-size: 10pt;")

        except Exception as e:
            logger.error(f"Failed to apply cache settings: {e}")
            self.status_msg.setText(f"✗ Failed to save settings: {e}")
            self.status_msg.setStyleSheet("color: #f48771; font-size: 10pt;")


class StartupControlWidget(QWidget):
    """Widget for controlling startup settings"""

    def __init__(self, startup_manager: StartupManager, parent=None):
        super().__init__(parent)
        self.startup_manager = startup_manager
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)

        # Startup control group
        startup_group = QGroupBox("Startup Settings")
        startup_layout = QVBoxLayout(startup_group)

        # Run on login checkbox
        self.startup_checkbox = QCheckBox("Run on Windows Startup")
        self.startup_checkbox.stateChanged.connect(self.on_startup_changed)
        startup_layout.addWidget(self.startup_checkbox)

        # Startup behavior dropdown
        behavior_layout = QHBoxLayout()
        behavior_layout.addWidget(QLabel("Startup Behavior:"))

        self.behavior_combo = QComboBox()
        self.behavior_combo.addItems(
            ["Minimized to Tray", "Show Window", "Show Window then Minimize"]
        )
        self.behavior_combo.currentTextChanged.connect(self.on_behavior_changed)
        behavior_layout.addWidget(self.behavior_combo)
        behavior_layout.addStretch()

        startup_layout.addLayout(behavior_layout)

        layout.addWidget(startup_group)

        # Status message
        self.status_msg = QLabel("")
        self.status_msg.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
        layout.addWidget(self.status_msg)

    def load_settings(self):
        """Load current startup settings"""
        try:
            settings = ui_config.get_all_settings()
            self.startup_checkbox.setChecked(settings.startup.run_on_login)

            behavior_map = {
                "minimized": "Minimized to Tray",
                "show_window": "Show Window",
                "show_then_minimize": "Show Window then Minimize",
            }
            behavior = behavior_map.get(
                settings.startup.startup_behavior, "Minimized to Tray"
            )
            self.behavior_combo.setCurrentText(behavior)

        except Exception as e:
            logger.error(f"Failed to load startup settings: {e}")

    def on_startup_changed(self):
        """Handle startup checkbox change"""
        try:
            enabled = self.startup_checkbox.isChecked()
            if self.startup_manager.toggle_startup():
                status = "enabled" if enabled else "disabled"
                self.status_msg.setText(f"✓ Startup {status} successfully")
                self.status_msg.setStyleSheet("color: #4ec9b0; font-size: 10pt;")
            else:
                self.status_msg.setText("✗ Failed to toggle startup setting")
                self.status_msg.setStyleSheet("color: #f48771; font-size: 10pt;")
        except Exception as e:
            logger.error(f"Failed to toggle startup: {e}")
            self.status_msg.setText(f"✗ Error: {e}")
            self.status_msg.setStyleSheet("color: #f48771; font-size: 10pt;")

    def on_behavior_changed(self):
        """Handle startup behavior change"""
        try:
            behavior_map = {
                "Minimized to Tray": "minimized",
                "Show Window": "show_window",
                "Show Window then Minimize": "show_then_minimize",
            }
            behavior = behavior_map.get(self.behavior_combo.currentText(), "minimized")
            ui_config.set_startup_setting("startup_behavior", behavior)

            self.status_msg.setText("✓ Startup behavior updated")
            self.status_msg.setStyleSheet("color: #4ec9b0; font-size: 10pt;")

        except Exception as e:
            logger.error(f"Failed to update startup behavior: {e}")
            self.status_msg.setText(f"✗ Error: {e}")
            self.status_msg.setStyleSheet("color: #f48771; font-size: 10pt;")


class MainWindow(QMainWindow):
    """Main control window with dark theme"""

    def __init__(
        self,
        service_controller: ServiceController,
        startup_manager: StartupManager,
        parent=None,
    ):
        super().__init__(parent)
        self.service_controller = service_controller
        self.startup_manager = startup_manager

        self.setup_ui()
        self.setup_dark_theme()
        self.load_window_settings()

        # Setup log refresh timer
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.refresh_logs)
        self.log_timer.start(5000)  # Refresh every 5 seconds

    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("HA Bridge Control Panel")
        self.setMinimumSize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left panel (controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Service status widget
        self.service_widget = ServiceStatusWidget(self.service_controller)
        left_layout.addWidget(self.service_widget)

        # Cache control widget
        self.cache_widget = CacheControlWidget()
        left_layout.addWidget(self.cache_widget)

        # Startup control widget
        self.startup_widget = StartupControlWidget(self.startup_manager)
        left_layout.addWidget(self.startup_widget)

        left_layout.addStretch()

        # Right panel (logs)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Logs group
        logs_group = QGroupBox("Service Logs")
        logs_layout = QVBoxLayout(logs_group)

        # Log controls
        log_controls = QHBoxLayout()

        self.auto_refresh = QCheckBox("Auto-refresh")
        self.auto_refresh.setChecked(True)
        self.auto_refresh.stateChanged.connect(self.toggle_auto_refresh)
        log_controls.addWidget(self.auto_refresh)

        self.clear_logs_btn = QPushButton("Clear Logs")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        log_controls.addWidget(self.clear_logs_btn)

        log_controls.addStretch()

        logs_layout.addLayout(log_controls)

        # Log viewer
        self.log_viewer = LogViewer()
        logs_layout.addWidget(self.log_viewer)

        right_layout.addWidget(logs_group)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])  # Equal sizes

        main_layout.addWidget(splitter)

        # Load initial logs
        self.refresh_logs()

    def setup_dark_theme(self):
        """Apply dark theme styling"""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #007acc;
            }
            
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #505050;
                border-color: #707070;
            }
            
            QPushButton:pressed {
                background-color: #303030;
            }
            
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #808080;
                border-color: #404040;
            }
            
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            
            QCheckBox::indicator:unchecked {
                border: 2px solid #606060;
                background-color: #2d2d2d;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                border: 2px solid #007acc;
                background-color: #007acc;
                border-radius: 3px;
            }
            
            QComboBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }
            
            QComboBox:hover {
                border-color: #707070;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #606060;
                selection-background-color: #007acc;
            }
            
            QLabel {
                color: #e0e0e0;
            }
        """
        )

    def load_window_settings(self):
        """Load window position and size from settings"""
        try:
            settings = ui_config.get_all_settings()
            if settings.window.last_position and settings.window.last_size:
                self.move(*settings.window.last_position)
                self.resize(*settings.window.last_size)
        except Exception as e:
            logger.error(f"Failed to load window settings: {e}")

    def save_window_settings(self):
        """Save window position and size to settings"""
        try:
            ui_config.update_window_settings(
                (self.pos().x(), self.pos().y()),
                (self.size().width(), self.size().height()),
            )
        except Exception as e:
            logger.error(f"Failed to save window settings: {e}")

    def refresh_logs(self):
        """Refresh the log viewer"""
        try:
            logs = self.service_controller.get_service_logs(50)  # Last 50 lines
            if logs:
                # Clear and add new logs
                self.log_viewer.clear()
                for log in logs:
                    self.log_viewer.append_log(log)
        except Exception as e:
            logger.error(f"Failed to refresh logs: {e}")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh of logs"""
        if self.auto_refresh.isChecked():
            self.log_timer.start(5000)
        else:
            self.log_timer.stop()

    def clear_logs(self):
        """Clear service logs"""
        if self.service_controller.clear_logs():
            self.log_viewer.clear_logs()

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_window_settings()
        event.accept()
