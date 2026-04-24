#!/usr/bin/env python3

import sys
import threading
import os
import json
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ================= GRAPH COMPONENT =================
class GraphWidget(FigureCanvas):
    def __init__(self):
        self.figure = Figure(figsize=(3, 3), facecolor='#000000')
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.low = 0
        self.medium = 0
        self.high = 0
        self.update_graph()

    def update_graph(self):
        self.ax.clear()
        labels = ['Low', 'Med', 'High']
        values = [self.low, self.medium, self.high]
        bars = self.ax.bar(labels, values)
        colors = ['#00ff88', '#ffaa00', '#ff3333']
        for bar, color in zip(bars, colors):
            bar.set_color(color)

        self.ax.set_facecolor('#000000')
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.set_title("Severity Analytics", color='white', fontsize=10)
        self.figure.tight_layout()
        self.draw()

# ================= ROS2 NODE =================
class GUINode(Node):
    def __init__(self, gui):
        super().__init__('gui_node')
        self.gui = gui
        
        # Publisher: sends "road_name,distance,velocity"
        self.publisher_ = self.create_publisher(String, '/cmd_move', 10)

        # Subscribers
        self.create_subscription(String, '/damage/img_captured', self.image_callback, 10)
        self.create_subscription(String, '/road_damage/detections', self.report_callback, 10)
        
        self.get_logger().info("✅ GUI Node has been started.")

    def image_callback(self, msg):
        self.get_logger().info(f"📸 Image received: {msg.data}")
        self.gui.image_signal.emit(msg.data)

    def report_callback(self, msg):
        self.get_logger().info(f"📋 Final report received: {msg.data}")
        self.gui.report_signal.emit(msg.data)

# ================= DASHBOARD UI =================
class Dashboard(QWidget):
    image_signal = pyqtSignal(str)
    report_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 Road Inspection System")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("QWidget { background-color: #000000; color: white; }")

        self.setup_ui()
        self.image_signal.connect(self.update_image)
        self.report_signal.connect(self.update_report)
        self.node = None
        self.score = 100

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # --- LEFT: Mission Control ---
        left = QVBoxLayout()
        title = QLabel("MISSION SETUP")
        title.setStyleSheet("font-weight: bold; font-size: 18px; color: #1a73e8; margin-bottom: 10px;")
        
        self.road_name_input = QLineEdit()
        self.road_name_input.setPlaceholderText("Road Name")
        self.road_name_input.setStyleSheet("background-color: #111; padding: 10px; border: 1px solid #333;")

        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("Distance (m)")
        self.distance_input.setStyleSheet("background-color: #111; padding: 10px; border: 1px solid #333;")

        self.velocity_input = QLineEdit()
        self.velocity_input.setPlaceholderText("Velocity (m/s)")
        self.velocity_input.setStyleSheet("background-color: #111; padding: 10px; border: 1px solid #333;")

        self.start_button = QPushButton("🚀 START MISSION")
        self.start_button.setStyleSheet("background-color: #1a73e8; font-weight: bold; height: 45px; border-radius: 5px;")
        self.start_button.clicked.connect(self.send_command)

        # --- FIX STARTS HERE ---
        # Initialize the actual button widget
        self.clear_btn_widget = QPushButton("🧹 RESET DASHBOARD")
        self.clear_btn_widget.setStyleSheet("background-color: #333; height: 35px; border-radius: 5px;")
        self.clear_btn_widget.clicked.connect(self.clear_button) # Connect to your method
        # --- FIX ENDS HERE ---

        self.status_label = QLabel("Status: System Ready")
        self.status_label.setStyleSheet("color: #00ff88; font-family: Consolas; font-size: 13px;")

        left.addWidget(title)
        left.addWidget(self.road_name_input)
        left.addWidget(self.distance_input)
        left.addWidget(self.velocity_input)
        left.addWidget(self.start_button)
        left.addWidget(self.clear_btn_widget) # Add the widget, not the method
        left.addStretch()
        left.addWidget(self.status_label)
        
        # --- MIDDLE: Analysis Display ---
        middle = QVBoxLayout()
        
        self.image_label = QLabel("LIVE CAMERA FEED / DETECTION")
        self.image_label.setFixedSize(600, 350)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #1a73e8; background-color: #050505;")

        self.score_label = QLabel("Road Quality Index: 100%")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ff88; margin-top: 10px;")

        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        self.report_box.setStyleSheet("background-color: #080808; border: 1px solid #333; font-family: Consolas; font-size: 14px; padding: 10px;")
        self.report_box.setPlaceholderText("Awaiting final mission analysis...")

        middle.addWidget(self.image_label)
        middle.addWidget(self.score_label)
        middle.addWidget(self.report_box)

        # --- Right Panel: Gallery & Analytics ---
        right = QVBoxLayout()
        self.gallery = QListWidget()
        self.gallery.setFixedWidth(250)
        self.gallery.setStyleSheet("background-color: #050505; border: 1px solid #222;")
        
        self.graph = GraphWidget()
        
        right.addWidget(QLabel("DAMAGE GALLERY"))
        right.addWidget(self.gallery)
        right.addWidget(self.graph)

        main_layout.addLayout(left, 1)
        main_layout.addLayout(middle, 3)
        main_layout.addLayout(right, 1)
        self.setLayout(main_layout)

    def update_report(self, json_string):
        try:
            # Parse the new payload structure
            data = json.loads(json_string)
            
            damaged = data.get("damaged", False)
            pothole_count = data.get("pothole_count", 0)
            crack_count = data.get("crack_count", 0)
            damage_percent = data.get("damage_percentage", 0)
            correct_percent = data.get("correct_percentage", 100)
            severity = data.get("severity", "LOW").upper()
            condition = data.get("road_condition", "Normal")

            # Update Analytics Graph based on severity
            if damaged:
                if severity == "HIGH":
                    self.graph.high += 1
                elif severity == "MEDIUM":
                    self.graph.medium += 1
                else:
                    self.graph.low += 1
            
            # Update the Quality Index using your correct_percentage
            self.score = correct_percent
            self.graph.update_graph()
            self.update_score_ui()

            # Output the specific data to the Report Box
            timestamp = datetime.now().strftime("%H:%M:%S")
            report_html = (
                f"<p style='color:#1a73e8;'><b>[{timestamp}] DETECTION LOG</b></p>"
                f"<p><b>STATUS:</b> <span style='color:{'#ff3333' if damaged else '#00ff88'};'>"
                f"{'DAMAGED' if damaged else 'CLEAR'}</span></p>"
                f"<p><b>DETAILS:</b> {condition}</p>"
                f"<p><b>POTHOLES:</b> {pothole_count} | <b>CRACKS:</b> {crack_count}</p>"
                f"<p><b>DAMAGE AREA:</b> {damage_percent}%</p>"
                f"<p><b>SEVERITY:</b> {severity}</p>"
                f"<hr style='border: 0.5px solid #333;'>"
            )
            
            self.report_box.append(report_html)
            
            # Auto-scroll to bottom
            self.report_box.verticalScrollBar().setValue(
                self.report_box.verticalScrollBar().maximum()
            )
            
            self.status_label.setText(f"Status: {severity} Damage Detected" if damaged else "Status: Road Clear")

        except Exception as e:
            self.report_box.append(f"<p style='color:red;'>Error parsing report: {e}</p>")
            
    def update_score_ui(self):
        self.score = max(0, self.score)
        color = "#00ff88" if self.score > 70 else "#ffaa00" if self.score > 40 else "#ff3333"
        self.score_label.setText(f"Road Quality Index: {self.score}%")
        self.score_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")

    def send_command(self):
        road = self.road_name_input.text()
        d = self.distance_input.text()
        v = self.velocity_input.text()
        if self.node:
            msg = String()
            msg.data = f"{road},{d},{v}"
            self.node.publisher_.publish(msg)
            self.status_label.setText(f"Status: Moving on {road}...")
            self.start_button.setEnabled(False)

    def update_image(self, path):
        if os.path.exists(path):
            pixmap = QPixmap(path).scaled(600, 350, Qt.KeepAspectRatio)
            self.image_label.setPixmap(pixmap)
            self.gallery.addItem(QListWidgetItem(QIcon(path), os.path.basename(path)))

    def clear_button(self):
        self.report_box.clear()
        self.gallery.clear()
        self.graph.low = self.graph.medium = self.graph.high = 0
        self.graph.update_graph()
        self.score = 100
        self.update_score_ui()
        self.image_label.setPixmap(QPixmap()) # Clear image
        self.image_label.setText("Waiting for Mission...")

def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    node = GUINode(dashboard)
    dashboard.node = node
    
    # Run ROS2 in a background thread to keep GUI responsive
    thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    thread.start()

    dashboard.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()