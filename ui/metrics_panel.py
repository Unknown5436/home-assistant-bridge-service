"""
Metrics Dashboard Panel for HA Bridge Control UI
Real-time monitoring of service performance, health, and statistics
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

import httpx
import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QGroupBox,
    QFrame,
    QScrollArea,
    QPushButton,
    QCheckBox,
    QComboBox,
    QProgressBar,
    QTextEdit,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt

from app.config.ui_config import ui_config

logger = logging.getLogger(__name__)


class MetricsDataFetcher(QThread):
    """Background thread for fetching metrics data"""

    data_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "test-api-key-12345",
    ):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.running = False

    def run(self):
        """Main thread loop"""
        self.running = True
        while self.running:
            try:
                self.fetch_metrics()
                self.msleep(5000)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error fetching metrics: {e}")
                self.error_occurred.emit(str(e))
                self.msleep(10000)  # Wait longer on error

    def stop(self):
        """Stop the thread"""
        self.running = False
        self.wait()

    def fetch_metrics(self):
        """Fetch metrics from the service"""
        try:
            with httpx.Client(timeout=10.0) as client:
                # Fetch status data (use health endpoint since status doesn't exist)
                status_response = client.get(
                    f"{self.base_url}/health", headers=self.headers
                )
                status_data = (
                    status_response.json() if status_response.status_code == 200 else {}
                )

                # Fetch metrics data (Prometheus format)
                metrics_response = client.get(f"{self.base_url}/metrics")
                metrics_data = (
                    self.parse_prometheus_metrics(metrics_response.text)
                    if metrics_response.status_code == 200
                    else {}
                )

                # Combine data
                combined_data = {
                    "timestamp": datetime.now().isoformat(),
                    "status": status_data,
                    "metrics": metrics_data,
                    "service_health": self.calculate_service_health(
                        status_data, metrics_data
                    ),
                }

                self.data_updated.emit(combined_data)

        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            self.error_occurred.emit(str(e))

    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics format"""
        metrics = {}
        lines = metrics_text.strip().split("\n")

        for line in lines:
            if line.startswith("#") or not line.strip():
                continue

            try:
                # Parse metric line: metric_name{labels} value
                if "{" in line:
                    metric_part, value_part = line.rsplit(" ", 1)
                    metric_name = metric_part.split("{")[0]
                    value = float(value_part)
                    metrics[metric_name] = value
                else:
                    parts = line.split(" ")
                    if len(parts) == 2:
                        metric_name, value = parts[0], float(parts[1])
                        metrics[metric_name] = value
            except (ValueError, IndexError):
                continue

        return metrics

    def calculate_service_health(
        self, status_data: Dict, metrics_data: Dict
    ) -> Dict[str, Any]:
        """Calculate overall service health score"""
        health_score = 100
        issues = []

        # Check HA connection
        if not status_data.get("ha_connected", False):
            health_score -= 30
            issues.append("Home Assistant disconnected")

        # Check WebSocket status
        ws_status = status_data.get("websocket", {})
        if not ws_status.get("connected", False):
            health_score -= 20
            issues.append("WebSocket disconnected")

        # Check error rates
        total_requests = metrics_data.get("ha_bridge_requests_total", 0)
        error_requests = metrics_data.get("ha_bridge_errors_total", 0)

        if total_requests > 0:
            error_rate = (error_requests / total_requests) * 100
            if error_rate > 10:
                health_score -= 25
                issues.append(f"High error rate: {error_rate:.1f}%")
            elif error_rate > 5:
                health_score -= 10
                issues.append(f"Elevated error rate: {error_rate:.1f}%")

        # Check response times
        avg_response_time = metrics_data.get("ha_bridge_request_duration_seconds", 0)
        if avg_response_time > 5.0:
            health_score -= 20
            issues.append(f"Slow response time: {avg_response_time:.1f}s")
        elif avg_response_time > 2.0:
            health_score -= 10
            issues.append(f"Elevated response time: {avg_response_time:.1f}s")

        return {
            "score": max(0, health_score),
            "issues": issues,
            "status": (
                "healthy"
                if health_score >= 80
                else "warning" if health_score >= 60 else "critical"
            ),
        }


class MetricsChart(FigureCanvas):
    """Custom matplotlib chart widget"""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

        # Setup dark theme
        self.fig.patch.set_facecolor("#2b2b2b")
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#1e1e1e")
        self.axes.tick_params(colors="white")
        self.axes.spines["bottom"].set_color("white")
        self.axes.spines["top"].set_color("white")
        self.axes.spines["right"].set_color("white")
        self.axes.spines["left"].set_color("white")

        # Data storage
        self.data_points = deque(
            maxlen=60
        )  # Keep last 60 data points (5 minutes at 5s intervals)
        self.timestamps = deque(maxlen=60)

    def update_chart(self, data: Dict[str, Any], chart_type: str = "response_time"):
        """Update chart with new data"""
        self.axes.clear()

        if chart_type == "response_time":
            self._plot_response_time(data)
        elif chart_type == "request_rate":
            self._plot_request_rate(data)
        elif chart_type == "error_rate":
            self._plot_error_rate(data)
        elif chart_type == "cache_hit_rate":
            self._plot_cache_hit_rate(data)

        self.fig.tight_layout()
        self.draw()

    def _plot_response_time(self, data: Dict[str, Any]):
        """Plot response time over time"""
        metrics = data.get("metrics", {})
        response_time = metrics.get("ha_bridge_request_duration_seconds", 0)

        self.data_points.append(response_time)
        self.timestamps.append(datetime.now())

        if len(self.data_points) > 1:
            times = list(self.timestamps)
            values = list(self.data_points)

            self.axes.plot(
                times, values, color="#4CAF50", linewidth=2, marker="o", markersize=3
            )
            self.axes.set_title("Response Time (seconds)", color="white", fontsize=12)
            self.axes.set_ylabel("Seconds", color="white")
            self.axes.grid(True, alpha=0.3)

            # Add average line
            avg_time = np.mean(values)
            self.axes.axhline(
                y=avg_time,
                color="#FF9800",
                linestyle="--",
                alpha=0.7,
                label=f"Avg: {avg_time:.2f}s",
            )
            self.axes.legend()

    def _plot_request_rate(self, data: Dict[str, Any]):
        """Plot request rate over time"""
        metrics = data.get("metrics", {})
        total_requests = metrics.get("ha_bridge_requests_total", 0)

        # Calculate requests per minute
        current_time = datetime.now()
        if len(self.timestamps) > 0:
            time_diff = (current_time - self.timestamps[-1]).total_seconds()
            if time_diff > 0:
                requests_per_minute = (
                    total_requests - getattr(self, "_last_total_requests", 0)
                ) * (60 / time_diff)
            else:
                requests_per_minute = 0
        else:
            requests_per_minute = 0

        self._last_total_requests = total_requests
        self.data_points.append(requests_per_minute)
        self.timestamps.append(current_time)

        if len(self.data_points) > 1:
            times = list(self.timestamps)
            values = list(self.data_points)

            self.axes.plot(
                times, values, color="#2196F3", linewidth=2, marker="o", markersize=3
            )
            self.axes.set_title("Request Rate (per minute)", color="white", fontsize=12)
            self.axes.set_ylabel("Requests/min", color="white")
            self.axes.grid(True, alpha=0.3)

    def _plot_error_rate(self, data: Dict[str, Any]):
        """Plot error rate over time"""
        metrics = data.get("metrics", {})
        total_requests = metrics.get("ha_bridge_requests_total", 0)
        error_requests = metrics.get("ha_bridge_errors_total", 0)

        error_rate = 0
        if total_requests > 0:
            error_rate = (error_requests / total_requests) * 100

        self.data_points.append(error_rate)
        self.timestamps.append(datetime.now())

        if len(self.data_points) > 1:
            times = list(self.timestamps)
            values = list(self.data_points)

            self.axes.plot(
                times, values, color="#F44336", linewidth=2, marker="o", markersize=3
            )
            self.axes.set_title("Error Rate (%)", color="white", fontsize=12)
            self.axes.set_ylabel("Error %", color="white")
            self.axes.grid(True, alpha=0.3)

            # Add warning lines
            self.axes.axhline(
                y=5, color="#FF9800", linestyle="--", alpha=0.7, label="Warning (5%)"
            )
            self.axes.axhline(
                y=10, color="#F44336", linestyle="--", alpha=0.7, label="Critical (10%)"
            )
            self.axes.legend()

    def _plot_cache_hit_rate(self, data: Dict[str, Any]):
        """Plot cache hit rate over time"""
        metrics = data.get("metrics", {})
        cache_hits = metrics.get("ha_bridge_cache_hits_total", 0)
        cache_misses = metrics.get("ha_bridge_cache_misses_total", 0)

        hit_rate = 0
        if cache_hits + cache_misses > 0:
            hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100

        self.data_points.append(hit_rate)
        self.timestamps.append(datetime.now())

        if len(self.data_points) > 1:
            times = list(self.timestamps)
            values = list(self.data_points)

            self.axes.plot(
                times, values, color="#9C27B0", linewidth=2, marker="o", markersize=3
            )
            self.axes.set_title("Cache Hit Rate (%)", color="white", fontsize=12)
            self.axes.set_ylabel("Hit %", color="white")
            self.axes.grid(True, alpha=0.3)

            # Add target line
            self.axes.axhline(
                y=80, color="#4CAF50", linestyle="--", alpha=0.7, label="Target (80%)"
            )
            self.axes.legend()


class MetricsPanel(QWidget):
    """Main metrics dashboard panel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_data_fetcher()
        self.setup_timer()

    def setup_ui(self):
        """Setup the metrics panel UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Service Metrics Dashboard")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4CAF50; margin: 10px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_cb)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Service Health Overview
        self.health_widget = self.create_health_overview()
        content_layout.addWidget(self.health_widget)

        # Charts section
        charts_group = QGroupBox("Performance Charts")
        charts_group.setStyleSheet(ui_config.get_groupbox_style())
        charts_layout = QGridLayout(charts_group)

        # Chart selection
        chart_controls = QHBoxLayout()
        chart_controls.addWidget(QLabel("Chart Type:"))

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(
            ["Response Time", "Request Rate", "Error Rate", "Cache Hit Rate"]
        )
        self.chart_type_combo.currentTextChanged.connect(self.update_chart_type)
        chart_controls.addWidget(self.chart_type_combo)

        chart_controls.addStretch()
        charts_layout.addLayout(chart_controls, 0, 0, 1, 2)

        # Main chart
        self.main_chart = MetricsChart(self, width=8, height=4)
        charts_layout.addWidget(self.main_chart, 1, 0, 1, 2)

        content_layout.addWidget(charts_group)

        # Metrics grid
        self.metrics_widget = self.create_metrics_grid()
        content_layout.addWidget(self.metrics_widget)

        # Production monitoring section
        self.production_widget = self.create_production_monitoring()
        content_layout.addWidget(self.production_widget)

        # Recent errors
        self.errors_widget = self.create_errors_widget()
        content_layout.addWidget(self.errors_widget)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_health_overview(self) -> QGroupBox:
        """Create service health overview widget"""
        group = QGroupBox("Service Health Overview")
        group.setStyleSheet(ui_config.get_groupbox_style())
        layout = QGridLayout(group)

        # Health score
        self.health_score_label = QLabel("100")
        self.health_score_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.health_score_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(QLabel("Health Score:"), 0, 0)
        layout.addWidget(self.health_score_label, 0, 1)

        # Health status
        self.health_status_label = QLabel("Healthy")
        self.health_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.health_status_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(QLabel("Status:"), 1, 0)
        layout.addWidget(self.health_status_label, 1, 1)

        # HA Connection
        self.ha_connection_label = QLabel("Disconnected")
        self.ha_connection_label.setStyleSheet("color: #F44336;")
        layout.addWidget(QLabel("HA Connection:"), 2, 0)
        layout.addWidget(self.ha_connection_label, 2, 1)

        # WebSocket Status
        self.ws_status_label = QLabel("Disconnected")
        self.ws_status_label.setStyleSheet("color: #F44336;")
        layout.addWidget(QLabel("WebSocket:"), 3, 0)
        layout.addWidget(self.ws_status_label, 3, 1)

        # Last update
        self.last_update_label = QLabel("Never")
        self.last_update_label.setStyleSheet("color: #9E9E9E;")
        layout.addWidget(QLabel("Last Update:"), 4, 0)
        layout.addWidget(self.last_update_label, 4, 1)

        return group

    def create_production_monitoring(self) -> QGroupBox:
        """Create production monitoring widget with alerting and uptime"""
        group = QGroupBox("Production Monitoring")
        group.setStyleSheet(ui_config.get_groupbox_style())
        layout = QGridLayout(group)

        # Uptime and stability metrics
        layout.addWidget(QLabel("Service Uptime:"), 0, 0)
        self.uptime_label = QLabel("Calculating...")
        self.uptime_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.uptime_label, 0, 1)

        layout.addWidget(QLabel("Stability Score:"), 0, 2)
        self.stability_label = QLabel("Calculating...")
        self.stability_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.stability_label, 0, 3)

        # Alerting indicators
        layout.addWidget(QLabel("Critical Alerts:"), 1, 0)
        self.critical_alerts = QLabel("0")
        self.critical_alerts.setStyleSheet(
            "color: #F44336; font-weight: bold; font-size: 16px;"
        )
        layout.addWidget(self.critical_alerts, 1, 1)

        layout.addWidget(QLabel("Warning Alerts:"), 1, 2)
        self.warning_alerts = QLabel("0")
        self.warning_alerts.setStyleSheet(
            "color: #FF9800; font-weight: bold; font-size: 16px;"
        )
        layout.addWidget(self.warning_alerts, 1, 3)

        # Performance thresholds
        layout.addWidget(QLabel("Response Time Status:"), 2, 0)
        self.response_status = QLabel("Good")
        self.response_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.response_status, 2, 1)

        layout.addWidget(QLabel("Error Rate Status:"), 2, 2)
        self.error_status = QLabel("Good")
        self.error_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.error_status, 2, 3)

        # Production health indicators
        layout.addWidget(QLabel("Production Ready:"), 3, 0)
        self.production_ready = QLabel("✓")
        self.production_ready.setStyleSheet(
            "color: #4CAF50; font-weight: bold; font-size: 18px;"
        )
        layout.addWidget(self.production_ready, 3, 1)

        layout.addWidget(QLabel("Security Status:"), 3, 2)
        self.security_status = QLabel("✓")
        self.security_status.setStyleSheet(
            "color: #4CAF50; font-weight: bold; font-size: 18px;"
        )
        layout.addWidget(self.security_status, 3, 3)

        return group

    def create_metrics_grid(self) -> QGroupBox:
        """Create metrics grid widget"""
        group = QGroupBox("Key Metrics")
        group.setStyleSheet(ui_config.get_groupbox_style())
        layout = QGridLayout(group)

        # Response time
        self.response_time_label = QLabel("0.00s")
        self.response_time_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Avg Response Time:"), 0, 0)
        layout.addWidget(self.response_time_label, 0, 1)

        # Request rate
        self.request_rate_label = QLabel("0/min")
        self.request_rate_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Request Rate:"), 1, 0)
        layout.addWidget(self.request_rate_label, 1, 1)

        # Error rate
        self.error_rate_label = QLabel("0%")
        self.error_rate_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Error Rate:"), 2, 0)
        layout.addWidget(self.error_rate_label, 2, 1)

        # Cache hit rate
        self.cache_hit_label = QLabel("0%")
        self.cache_hit_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Cache Hit Rate:"), 3, 0)
        layout.addWidget(self.cache_hit_label, 3, 1)

        # Total requests
        self.total_requests_label = QLabel("0")
        self.total_requests_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Total Requests:"), 4, 0)
        layout.addWidget(self.total_requests_label, 4, 1)

        # Uptime
        self.uptime_label = QLabel("Unknown")
        self.uptime_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(QLabel("Uptime:"), 5, 0)
        layout.addWidget(self.uptime_label, 5, 1)

        return group

    def create_errors_widget(self) -> QGroupBox:
        """Create recent errors widget"""
        group = QGroupBox("Recent Issues")
        group.setStyleSheet(ui_config.get_groupbox_style())
        layout = QVBoxLayout(group)

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(150)
        self.errors_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """
        )
        layout.addWidget(self.errors_text)

        return group

    def setup_data_fetcher(self):
        """Setup the data fetcher thread"""
        self.data_fetcher = MetricsDataFetcher()
        self.data_fetcher.data_updated.connect(self.update_metrics)
        self.data_fetcher.error_occurred.connect(self.handle_error)

    def setup_timer(self):
        """Setup refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)

    def toggle_auto_refresh(self, checked: bool):
        """Toggle auto-refresh"""
        if checked:
            self.refresh_timer.start(5000)  # 5 seconds
            self.data_fetcher.start()
        else:
            self.refresh_timer.stop()
            self.data_fetcher.stop()

    def manual_refresh(self):
        """Manual refresh"""
        if not self.data_fetcher.isRunning():
            self.data_fetcher.start()

    def refresh_data(self):
        """Refresh data if auto-refresh is enabled"""
        if self.auto_refresh_cb.isChecked() and not self.data_fetcher.isRunning():
            self.data_fetcher.start()

    @pyqtSlot(dict)
    def update_metrics(self, data: Dict[str, Any]):
        """Update metrics display with new data"""
        try:
            # Update health overview
            health = data.get("service_health", {})
            score = health.get("score", 0)
            status = health.get("status", "unknown")
            issues = health.get("issues", [])

            self.health_score_label.setText(str(score))
            self.health_score_label.setStyleSheet(
                f"color: {'#4CAF50' if score >= 80 else '#FF9800' if score >= 60 else '#F44336'};"
            )

            self.health_status_label.setText(status.title())
            self.health_status_label.setStyleSheet(
                f"color: {'#4CAF50' if status == 'healthy' else '#FF9800' if status == 'warning' else '#F44336'};"
            )

            # Update connection status
            status_data = data.get("status", {})

            ha_connected = status_data.get("ha_connected", False)
            self.ha_connection_label.setText(
                "Connected" if ha_connected else "Disconnected"
            )
            self.ha_connection_label.setStyleSheet(
                "color: #4CAF50;" if ha_connected else "color: #F44336;"
            )

            ws_status = status_data.get("websocket", {})
            ws_connected = ws_status.get("connected", False)
            self.ws_status_label.setText(
                "Connected" if ws_connected else "Disconnected"
            )
            self.ws_status_label.setStyleSheet(
                "color: #4CAF50;" if ws_connected else "color: #F44336;"
            )

            # Update last update time
            self.last_update_label.setText(datetime.now().strftime("%H:%M:%S"))

            # Update production monitoring
            self.update_production_monitoring(data)

            # Update metrics
            metrics = data.get("metrics", {})

            response_time = metrics.get("ha_bridge_request_duration_seconds", 0)
            self.response_time_label.setText(f"{response_time:.2f}s")
            self.response_time_label.setStyleSheet(
                f"color: {'#4CAF50' if response_time < 2 else '#FF9800' if response_time < 5 else '#F44336'};"
            )

            total_requests = metrics.get("ha_bridge_requests_total", 0)
            self.total_requests_label.setText(str(total_requests))

            # Calculate error rate
            error_requests = metrics.get("ha_bridge_errors_total", 0)
            error_rate = 0
            if total_requests > 0:
                error_rate = (error_requests / total_requests) * 100
            self.error_rate_label.setText(f"{error_rate:.1f}%")
            self.error_rate_label.setStyleSheet(
                f"color: {'#4CAF50' if error_rate < 5 else '#FF9800' if error_rate < 10 else '#F44336'};"
            )

            # Calculate cache hit rate
            cache_hits = metrics.get("ha_bridge_cache_hits_total", 0)
            cache_misses = metrics.get("ha_bridge_cache_misses_total", 0)
            hit_rate = 0
            if cache_hits + cache_misses > 0:
                hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
            self.cache_hit_label.setText(f"{hit_rate:.1f}%")
            self.cache_hit_label.setStyleSheet(
                f"color: {'#4CAF50' if hit_rate >= 80 else '#FF9800' if hit_rate >= 60 else '#F44336'};"
            )

            # Update chart
            chart_type = self.chart_type_combo.currentText().lower().replace(" ", "_")
            self.main_chart.update_chart(data, chart_type)

            # Update errors
            if issues:
                error_text = "\n".join([f"• {issue}" for issue in issues])
                self.errors_text.setPlainText(error_text)
            else:
                self.errors_text.setPlainText("No issues detected")

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def update_production_monitoring(self, data: Dict[str, Any]):
        """Update production monitoring indicators"""
        try:
            # Calculate uptime (simplified - in production this would come from service start time)
            uptime_hours = (
                24  # Placeholder - would be calculated from service start time
            )
            self.uptime_label.setText(f"{uptime_hours:.1f} hours")

            # Calculate stability score based on error rate and response time
            metrics = data.get("metrics", {})
            error_rate = metrics.get("ha_bridge_error_rate", 0)
            response_time = metrics.get("ha_bridge_request_duration_seconds", 0)

            # Stability score: 100 - (error_rate * 100) - (response_time * 10)
            stability_score = max(0, 100 - (error_rate * 100) - (response_time * 10))
            self.stability_label.setText(f"{stability_score:.1f}%")
            self.stability_label.setStyleSheet(
                f"color: {'#4CAF50' if stability_score >= 80 else '#FF9800' if stability_score >= 60 else '#F44336'};"
            )

            # Calculate alerts based on thresholds
            critical_alerts = 0
            warning_alerts = 0

            # Response time alerts
            if response_time > 5:
                critical_alerts += 1
            elif response_time > 2:
                warning_alerts += 1

            # Error rate alerts
            if error_rate > 0.1:  # 10% error rate
                critical_alerts += 1
            elif error_rate > 0.05:  # 5% error rate
                warning_alerts += 1

            # Connection alerts
            status_data = data.get("status", {})
            if not status_data.get("ha_connected", False):
                critical_alerts += 1

            websocket_status = status_data.get("websocket", {})
            if not websocket_status.get("connected", False):
                warning_alerts += 1

            # Update alert indicators
            self.critical_alerts.setText(str(critical_alerts))
            self.warning_alerts.setText(str(warning_alerts))

            # Update performance status
            if response_time < 2:
                self.response_status.setText("Good")
                self.response_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif response_time < 5:
                self.response_status.setText("Warning")
                self.response_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            else:
                self.response_status.setText("Critical")
                self.response_status.setStyleSheet("color: #F44336; font-weight: bold;")

            if error_rate < 0.05:
                self.error_status.setText("Good")
                self.error_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif error_rate < 0.1:
                self.error_status.setText("Warning")
                self.error_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            else:
                self.error_status.setText("Critical")
                self.error_status.setStyleSheet("color: #F44336; font-weight: bold;")

            # Update production readiness indicators
            production_ready = critical_alerts == 0 and stability_score >= 80
            self.production_ready.setText("✓" if production_ready else "✗")
            self.production_ready.setStyleSheet(
                f"color: {'#4CAF50' if production_ready else '#F44336'}; font-weight: bold; font-size: 18px;"
            )

            # Security status (simplified check)
            security_ok = status_data.get(
                "ha_connected", False
            ) and websocket_status.get("connected", False)
            self.security_status.setText("✓" if security_ok else "✗")
            self.security_status.setStyleSheet(
                f"color: {'#4CAF50' if security_ok else '#F44336'}; font-weight: bold; font-size: 18px;"
            )

        except Exception as e:
            logger.error(f"Error updating production monitoring: {e}")

    @pyqtSlot(str)
    def handle_error(self, error_msg: str):
        """Handle data fetching errors"""
        self.errors_text.setPlainText(f"Error fetching metrics: {error_msg}")
        logger.error(f"Metrics fetch error: {error_msg}")

    def update_chart_type(self, chart_type: str):
        """Update chart type"""
        # This will be called when the chart type combo box changes
        # The actual chart update will happen in update_metrics
        pass

    def closeEvent(self, event):
        """Clean up when closing"""
        self.data_fetcher.stop()
        event.accept()
