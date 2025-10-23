"""
System Tray Application for HA Bridge Control UI
Provides system tray icon with context menu and status monitoring
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox, QWidget
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QAction, QPixmap

from ui.service_controller import ServiceController
from ui.startup_manager import StartupManager

logger = logging.getLogger(__name__)


class ServiceMonitor(QObject):
    """Monitors service status in background thread"""

    status_changed = pyqtSignal(dict)

    def __init__(self, service_controller: ServiceController):
        super().__init__()
        self.service_controller = service_controller
        self.last_status = None

    def check_status(self):
        """Check service status and emit signal if changed"""
        try:
            status = self.service_controller.get_service_status()

            # Only emit if status actually changed
            if status != self.last_status:
                self.status_changed.emit(status)
                self.last_status = status

        except Exception as e:
            logger.error(f"Service monitor error: {e}")


class SystemTrayApp(QSystemTrayIcon):
    """System tray application with service control"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize components
        self.service_controller = ServiceController()
        self.startup_manager = StartupManager()

        # Setup tray icon
        self.setup_tray_icon()
        self.setup_menu()

        # Setup monitoring
        self.monitor = ServiceMonitor(self.service_controller)
        self.monitor.status_changed.connect(self.on_status_changed)

        # Start monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor.check_status)
        self.monitor_timer.start(5000)  # Check every 5 seconds

        # Initial status check
        self.monitor.check_status()

        # Connect signals
        self.activated.connect(self.on_tray_activated)

    def setup_tray_icon(self):
        """Setup the tray icon"""
        try:
            # Load icons
            icons_dir = Path(__file__).parent / "assets" / "icons"
            self.icon_active = QIcon(str(icons_dir / "tray_icon_active.png"))
            self.icon_inactive = QIcon(str(icons_dir / "tray_icon_inactive.png"))
            self.icon_unknown = QIcon(str(icons_dir / "tray_icon_unknown.png"))

            # Set initial icon
            self.setIcon(self.icon_unknown)
            self.setToolTip("HA Bridge Service - Unknown")

        except Exception as e:
            logger.error(f"Failed to setup tray icon: {e}")
            # Fallback to system icon
            self.setIcon(
                QApplication.style().standardIcon(
                    QApplication.style().StandardPixmap.SP_ComputerIcon
                )
            )

    def setup_menu(self):
        """Setup the context menu"""
        self.menu = QMenu()

        # Show Control Panel action
        self.show_action = QAction("Show Control Panel", self)
        self.show_action.triggered.connect(self.show_control_panel)
        self.menu.addAction(self.show_action)

        # Service status
        self.status_action = QAction("Service Status: Unknown", self)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # Service control actions
        self.start_action = QAction("Start Service", self)
        self.start_action.triggered.connect(self.start_service)
        self.menu.addAction(self.start_action)

        self.stop_action = QAction("Stop Service", self)
        self.stop_action.triggered.connect(self.stop_service)
        self.menu.addAction(self.stop_action)

        self.restart_action = QAction("Restart Service", self)
        self.restart_action.triggered.connect(self.restart_service)
        self.menu.addAction(self.restart_action)

        self.menu.addSeparator()

        # Startup control
        self.startup_action = QAction("Run on Startup", self)
        self.startup_action.setCheckable(True)
        self.startup_action.triggered.connect(self.toggle_startup)
        self.menu.addAction(self.startup_action)

        self.menu.addSeparator()

        # Exit action
        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.exit_action)

        # Set the menu
        self.setContextMenu(self.menu)

    def on_status_changed(self, status: dict):
        """Handle service status changes"""
        try:
            # Update icon
            if status["running"]:
                if status["health"]:
                    self.setIcon(self.icon_active)
                    tooltip = f"HA Bridge Service - Running (PID: {status['pid']})"
                else:
                    self.setIcon(self.icon_inactive)
                    tooltip = "HA Bridge Service - Running but unhealthy"
            else:
                self.setIcon(self.icon_inactive)
                tooltip = "HA Bridge Service - Stopped"

            self.setToolTip(tooltip)

            # Update menu
            if status["running"]:
                status_text = f"Service Status: Running (PID: {status['pid']})"
                if status["uptime"]:
                    status_text += f" - Uptime: {status['uptime']}"
            else:
                status_text = "Service Status: Stopped"

            self.status_action.setText(status_text)

            # Update action states
            self.start_action.setEnabled(not status["running"])
            self.stop_action.setEnabled(status["running"])
            self.restart_action.setEnabled(True)

            # Update startup status
            startup_enabled = self.startup_manager.is_startup_enabled()
            self.startup_action.setChecked(startup_enabled)

        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_control_panel()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click - show menu
            self.contextMenu().exec()

    def show_control_panel(self):
        """Show the main control panel window"""
        try:
            # Import here to avoid circular imports
            from ui.main_window import MainWindow

            if not hasattr(self, "main_window") or self.main_window is None:
                self.main_window = MainWindow(
                    self.service_controller, self.startup_manager
                )

            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

        except Exception as e:
            logger.error(f"Failed to show control panel: {e}")
            QMessageBox.critical(None, "Error", f"Failed to open control panel: {e}")

    def start_service(self):
        """Start the service"""
        try:
            result = self.service_controller.start_service()
            if result["success"]:
                self.showMessage(
                    "Service Started",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            else:
                self.showMessage(
                    "Start Failed",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000,
                )
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self.showMessage(
                "Error",
                f"Failed to start service: {e}",
                QSystemTrayIcon.MessageIcon.Critical,
                5000,
            )

    def stop_service(self):
        """Stop the service"""
        try:
            result = self.service_controller.stop_service()
            if result["success"]:
                self.showMessage(
                    "Service Stopped",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            else:
                self.showMessage(
                    "Stop Failed",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000,
                )
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            self.showMessage(
                "Error",
                f"Failed to stop service: {e}",
                QSystemTrayIcon.MessageIcon.Critical,
                5000,
            )

    def restart_service(self):
        """Restart the service"""
        try:
            result = self.service_controller.restart_service()
            if result["success"]:
                self.showMessage(
                    "Service Restarted",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            else:
                self.showMessage(
                    "Restart Failed",
                    result["message"],
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000,
                )
        except Exception as e:
            logger.error(f"Failed to restart service: {e}")
            self.showMessage(
                "Error",
                f"Failed to restart service: {e}",
                QSystemTrayIcon.MessageIcon.Critical,
                5000,
            )

    def toggle_startup(self):
        """Toggle startup setting"""
        try:
            if self.startup_manager.toggle_startup():
                startup_enabled = self.startup_manager.is_startup_enabled()
                status = "enabled" if startup_enabled else "disabled"
                self.showMessage(
                    "Startup Setting",
                    f"Startup {status} successfully",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            else:
                self.showMessage(
                    "Startup Error",
                    "Failed to toggle startup setting",
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000,
                )
        except Exception as e:
            logger.error(f"Failed to toggle startup: {e}")
            self.showMessage(
                "Error",
                f"Failed to toggle startup: {e}",
                QSystemTrayIcon.MessageIcon.Critical,
                5000,
            )

    def exit_app(self):
        """Exit the application"""
        try:
            # Stop monitoring
            if hasattr(self, "monitor_timer"):
                self.monitor_timer.stop()

            # Close main window if open
            if hasattr(self, "main_window") and self.main_window:
                self.main_window.close()

            # Exit application
            QApplication.quit()

        except Exception as e:
            logger.error(f"Error during exit: {e}")
            QApplication.quit()

    def show_notification(
        self,
        title: str,
        message: str,
        icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ):
        """Show a system notification"""
        self.showMessage(title, message, icon_type, 3000)
