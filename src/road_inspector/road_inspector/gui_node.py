#!/usr/bin/env python3

import sys
import threading
import os
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ================= GRAPH COMPONENT =================
class GraphWidget(FigureCanvas):
    def __init__(self):
        self.figure = Figure(facecolor='#000000')
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.low = 0
        self.medium = 0
        self.high = 0
        self.update_graph()

    def update_graph(self):
        self.ax.clear()
        labels = ['Low', 'Medium', 'High']
        values = [self.low, self.medium, self.high]
        bars = self.ax.bar(labels, values)
        colors = ['#00ff88', '#ffaa00', '#ff3333']
        for bar, color in zip(bars, colors):
            bar.set_color(color)

        self.ax.set_facecolor('#000000')
        self.ax.set_title("Damage Analytics", color='white')
        self.ax.tick_params(colors='white')
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
        self.create_subscription(String, '/road/final_report', self.report_callback, 10)

    def image_callback(self, msg):
        self.gui.image_signal.emit(msg.data)

    def report_callback(self, msg):
        self.gui.report_signal.emit(msg.data)

# ================= DASHBOARD UI =================
class Dashboard(QWidget):
    image_signal = pyqtSignal(str)
    report_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 Road Inspection System")
        self.setGeometry(100, 100, 1300, 750)
        self.setStyleSheet("QWidget { background-color: #000000; color: white; }")

        self.setup_ui()
        self.image_signal.connect(self.update_image)
        self.report_signal.connect(self.update_report)
        self.node = None
        self.score = 100

    def setup_ui(self):
        # --- Left Panel: Mission Control ---
        left = QVBoxLayout()
        header = QLabel("MISSION SETUP")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #1a73e8;")
        
        self.road_name_input = QLineEdit()
        self.road_name_input.setPlaceholderText("Road Name (e.g., Cairo Road)")
        self.road_name_input.setStyleSheet("background-color: #111; padding: 8px;")

        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("Distance (meters)")
        self.distance_input.setStyleSheet("background-color: #111; padding: 8px;")

        self.velocity_input = QLineEdit()
        self.velocity_input.setPlaceholderText("Velocity (m/s)")
        self.velocity_input.setStyleSheet("background-color: #111; padding: 8px;")

        self.start_button = QPushButton("🚀 START MISSION")
        self.start_button.setStyleSheet("background-color: #1a73e8; font-weight: bold; height: 40px;")
        self.start_button.clicked.connect(self.send_command)

        self.clear_button = QPushButton("🧹 RESET DASHBOARD")
        self.clear_button.setStyleSheet("background-color: #333; height: 30px;")
        self.clear_button.clicked.connect(self.clear_report)

        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 14px;")

        left.addWidget(header)
        left.addWidget(self.road_name_input)
        left.addWidget(self.distance_input)
        left.addWidget(self.velocity_input)
        left.addWidget(self.start_button)
        left.addWidget(self.clear_button)
        left.addStretch()
        left.addWidget(self.status_label)

        # --- Middle Panel: Image & Report ---
        middle = QVBoxLayout()
        self.image_label = QLabel("Waiting for Detections...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(500, 300)
        self.image_label.setStyleSheet("border: 1px solid #333;")

        self.score_label = QLabel("Road Quality: 100")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("font-size: 20px; color: #00ff88;")

        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        self.report_box.setStyleSheet("background-color: #050505; border: 1px solid #222;")

        middle.addWidget(self.image_label)
        middle.addWidget(self.score_label)
        middle.addWidget(self.report_box)

        # --- Right Panel: Gallery & Analytics ---
        right = QVBoxLayout()
        self.gallery = QListWidget()
        self.gallery.setFixedWidth(280)
        self.gallery.itemClicked.connect(self.display_selected_image)
        
        self.graph = GraphWidget()
        
        right.addWidget(QLabel("DAMAGE GALLERY"))
        right.addWidget(self.gallery)
        right.addWidget(self.graph)

        # --- Main Layout ---
        main = QHBoxLayout()
        main.addLayout(left, 1)
        main.addLayout(middle, 2)
        main.addLayout(right, 1)
        self.setLayout(main)

    def send_command(self):
        road = self.road_name_input.text().strip()
        d = self.distance_input.text().strip()
        v = self.velocity_input.text().strip()

        # Simple validation for Road Name and Numbers
        if not road or not d.replace('.','',1).isdigit() or not v.replace('.','',1).isdigit():
            self.status_label.setText("Status: Error! Check Inputs")
            self.status_label.setStyleSheet("color: #ff3333;")
            return

        msg = String()
        msg.data = f"{road},{d},{v}"
        self.node.publisher_.publish(msg)

        # Lock UI
        self.clear_report()
        self.status_label.setText(f"Status: INSPECTING {road}...")
        self.status_label.setStyleSheet("color: #ffaa00;")
        self.start_button.setEnabled(False)

    def update_image(self, path):
        if os.path.exists(path):
            item = QListWidgetItem(path)
            item.setIcon(QIcon(path))
            self.gallery.addItem(item)
            # Display immediately
            self.display_selected_image(item)

    def display_selected_image(self, item):
        path = item.text()
        pixmap = QPixmap(path).scaled(500, 300, Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

    def update_report(self, text):
        # Update analytics based on report keywords
        if "High" in text:
            self.graph.high += 1
            self.score -= 15
        elif "Medium" in text:
            self.graph.medium += 1
            self.score -= 10
        elif "Low" in text:
            self.graph.low += 1
            self.score -= 5

        self.graph.update_graph()
        self.update_score_ui()

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.report_box.append(f"<b>[{timestamp}]</b> {text}")
        
        # Mission Complete Logic
        self.status_label.setText("Status: Mission Complete")
        self.status_label.setStyleSheet("color: #00ff88;")
        self.start_button.setEnabled(True)

    def update_score_ui(self):
        self.score = max(0, self.score)
        color = "#00ff88" if self.score > 70 else "#ffaa00" if self.score > 40 else "#ff3333"
        self.score_label.setText(f"Road Quality: {self.score}")
        self.score_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")

    def clear_report(self):
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