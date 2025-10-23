"""
HA Bridge Control UI Launcher
Entry point for the control panel application
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.tray_app import SystemTrayApp
from ui.service_controller import ServiceController
from ui.startup_manager import StartupManager
from app.config.ui_config import ui_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("ui.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def setup_dark_theme(app: QApplication):
    """Apply dark theme to the entire application"""
    app.setStyle("Fusion")

    # Create dark palette
    palette = QPalette()

    # Window colors
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))

    # Base colors
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))

    # Text colors
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))

    # Button colors
    palette.setColor(QPalette.ColorRole.Button, QColor(64, 64, 64))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 224))

    # Highlight colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 204))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Disabled colors
    palette.setColor(QPalette.ColorRole.WindowText, QColor(128, 128, 128))
    palette.setColor(QPalette.ColorRole.Text, QColor(128, 128, 128))

    app.setPalette(palette)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="HA Bridge Control Panel")
    parser.add_argument(
        "--minimized", action="store_true", help="Start minimized to system tray"
    )
    parser.add_argument(
        "--startup-mode",
        choices=["minimized", "show_window", "show_then_minimize"],
        default="minimized",
        help="Startup behavior mode",
    )
    parser.add_argument(
        "--auto-start-service",
        action="store_true",
        help="Automatically start the bridge service if not running",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser.parse_args()


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []

    try:
        import PyQt6
    except ImportError:
        missing_deps.append("PyQt6")

    try:
        import psutil
    except ImportError:
        missing_deps.append("psutil")

    if missing_deps:
        error_msg = f"Missing required dependencies: {', '.join(missing_deps)}\n"
        error_msg += "Please install them with: pip install " + " ".join(missing_deps)

        # Try to show error in GUI if possible
        try:
            app = QApplication([])
            QMessageBox.critical(None, "Missing Dependencies", error_msg)
        except:
            pass

        print(error_msg)
        sys.exit(1)


def main():
    """Main application entry point"""
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Enable debug logging if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled")

        # Check dependencies
        check_dependencies()

        # Create QApplication
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed

        # Set application properties
        app.setApplicationName("HA Bridge Control Panel")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("HA Bridge")

        # Apply dark theme
        setup_dark_theme(app)

        # Initialize components
        logger.info("Initializing HA Bridge Control Panel...")

        service_controller = ServiceController(str(project_root))
        startup_manager = StartupManager()

        # Load UI settings
        settings = ui_config.get_all_settings()
        logger.info(f"Loaded UI settings: {settings}")

        # Clear logs on startup if enabled
        if settings.logs.clear_on_startup:
            logger.info("Clearing logs on startup...")
            
            # Clear service logs
            service_logs_cleared = service_controller.clear_logs()
            if service_logs_cleared:
                logger.info("Service logs cleared successfully")
            else:
                logger.warning("Service logs could not be cleared (file may be locked)")
            
            # Also clear UI log
            ui_log_file = project_root / "ui.log"
            if ui_log_file.exists():
                try:
                    # Use truncation approach for UI log too
                    with open(ui_log_file, 'w', encoding='utf-8') as f:
                        f.truncate(0)
                    logger.info("UI log cleared successfully")
                except PermissionError as e:
                    logger.warning(f"UI log could not be cleared - file is locked: {e}")
                except Exception as e:
                    logger.error(f"Failed to clear UI log: {e}")

        # Auto-start service if requested and not running
        if args.auto_start_service or settings.service.auto_start:
            status = service_controller.get_service_status()
            if not status["running"]:
                logger.info("Auto-starting bridge service...")
                result = service_controller.start_service()
                if result["success"]:
                    logger.info("Bridge service started successfully")
                else:
                    logger.warning(f"Failed to auto-start service: {result['message']}")

        # Create system tray app
        tray_app = SystemTrayApp()

        # Show main window based on startup mode
        startup_behavior = args.startup_mode or settings.startup.startup_behavior

        if not args.minimized and startup_behavior != "minimized":
            logger.info("Showing main control window")
            tray_app.show_control_panel()

            # Minimize after showing if requested
            if startup_behavior == "show_then_minimize":
                # Delay minimization to allow window to show first
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(
                    2000,
                    lambda: (
                        tray_app.main_window.hide()
                        if hasattr(tray_app, "main_window")
                        else None
                    ),
                )

        logger.info("HA Bridge Control Panel started successfully")
        logger.info(f"Startup behavior: {startup_behavior}")
        logger.info(
            f"Service auto-start: {args.auto_start_service or settings.service.auto_start}"
        )

        # Show system tray
        tray_app.show()

        # Run application
        sys.exit(app.exec())

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

        # Try to show error in GUI
        try:
            if "app" in locals():
                QMessageBox.critical(
                    None, "Fatal Error", f"Application failed to start:\n{e}"
                )
        except:
            pass

        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
