#!/usr/bin/env python3
"""
Test script for the Metrics Dashboard
Verifies that the metrics panel can be created and displays correctly
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

# Add the project root to the path
sys.path.insert(0, ".")

from ui.metrics_panel import MetricsPanel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWindow(QMainWindow):
    """Test window for the metrics panel"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metrics Dashboard Test")
        self.setGeometry(100, 100, 1200, 800)

        # Create metrics panel
        self.metrics_panel = MetricsPanel()
        self.setCentralWidget(self.metrics_panel)

        # Setup auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.test_data_update)
        self.timer.start(10000)  # Update every 10 seconds

        logger.info("Test window created successfully")

    def test_data_update(self):
        """Test data update functionality"""
        logger.info("Testing metrics data update...")
        # The metrics panel will handle its own data fetching
        pass


def main():
    """Main test function"""
    app = QApplication(sys.argv)

    # Apply dark theme
    app.setStyleSheet(
        """
        QMainWindow {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
    """
    )

    # Create test window
    window = TestWindow()
    window.show()

    logger.info("Starting metrics dashboard test...")
    logger.info(
        "Note: The dashboard will show connection errors if the bridge service is not running"
    )
    logger.info(
        "This is expected behavior - the dashboard is designed to handle service unavailability gracefully"
    )

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
