#!/usr/bin/env python3
import sys
import threading
import json
from datetime import datetime
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon, QImage
from sensor_msgs.msg import Image 
from cv_bridge import CvBridge
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QSizePolicy

class GraphWidget(FigureCanvas):
    def __init__(self):
        self.figure = Figure(figsize=(3, 3), facecolor='#000000')
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.low = self.medium = self.high = 0
        self.update_graph()

    def update_graph(self):
        self.ax.clear()
        labels, values = ['Low', 'Med', 'High'], [self.low, self.medium, self.high]
        bars = self.ax.bar(labels, values, color=['#00ff88', '#ffaa00', '#ff3333'])
        self.ax.set_facecolor('#000000')
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.set_ylim(0, max(5, max(values) + 1))
        self.ax.set_title("Severity Analytics", color='white', fontsize=10)
        self.figure.tight_layout()
        self.draw()

class GUINode(Node):
    def __init__(self, gui):
        super().__init__('gui_node')
        self.gui = gui
        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(String, '/cmd_move', 10)
        self.create_subscription(Image, '/road_damage/gallery', lambda m: self.gui.image_signal.emit(m), 10)
        self.create_subscription(String, '/road_damage/final_report', lambda m: self.gui.report_signal.emit(m.data), 10)

class Dashboard(QWidget):
    image_signal = pyqtSignal(object) 
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

        self.clear_btn_widget = QPushButton("🧹 RESET DASHBOARD")
        self.clear_btn_widget.setStyleSheet("background-color: #333; height: 35px; border-radius: 5px;")
        self.clear_btn_widget.clicked.connect(self.clear_button)

        self.status_label = QLabel("Status: System Ready")
        self.status_label.setStyleSheet("color: #00ff88; font-family: Consolas; font-size: 13px;")

        left.addWidget(title); left.addWidget(self.road_name_input); left.addWidget(self.distance_input)
        left.addWidget(self.velocity_input); left.addWidget(self.start_button); left.addWidget(self.clear_btn_widget)
        left.addStretch(); left.addWidget(self.status_label)
        
        middle = QVBoxLayout()
        self.image_label = QLabel("LIVE CAMERA FEED / DETECTION")
        self.image_label.setMinimumSize(600, 350)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #1a73e8; background-color: #050505;")
        
        self.score_label = QLabel("Road Quality Index: 100%")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ff88; margin-top: 10px;")

        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        self.report_box.setStyleSheet("background-color: #080808; border: 1px solid #333; font-family: Consolas; font-size: 14px; padding: 10px;")

        middle.addWidget(self.image_label)
        middle.addWidget(self.score_label); middle.addWidget(self.report_box)
        self.image_label.setScaledContents(False)
        self.image_label.setAlignment(Qt.AlignCenter)

        right = QVBoxLayout()
        self.gallery = QListWidget()
        self.gallery.setFixedWidth(250)
        self.gallery.setStyleSheet("background-color: #050505; border: 1px solid #222;")
        self.gallery.itemClicked.connect(self.on_item_clicked) 
        self.graph = GraphWidget()
        right.addWidget(QLabel("DAMAGE GALLERY")); right.addWidget(self.gallery); right.addWidget(self.graph)

        main_layout.addLayout(left, 1); main_layout.addLayout(middle, 3); main_layout.addLayout(right, 1)
        self.setLayout(main_layout)
    
    def update_report(self, json_string):
        try:
            data = json.loads(json_string)
            damaged, sev = data.get("damaged", False), data.get("severity", "LOW").upper()
            if damaged:
                if sev in ["CRITICAL", "HIGH"]: self.graph.high += 1
                elif sev == "MEDIUM": self.graph.medium += 1
                else: self.graph.low += 1
            self.score = data.get("correct_percentage", 100)
            self.graph.update_graph(); self.update_score_ui()

            report_html = (f"<p style='color:#1a73e8;'><b>[{datetime.now().strftime('%H:%M:%S')}] DETECTION LOG</b></p>"
                           f"<p><b>STATUS:</b> <span style='color:{'#ff3333' if damaged else '#00ff88'};'>{'DAMAGED' if damaged else 'CLEAR'}</span></p>"
                           f"<p><b>DETAILS:</b> {data.get('road_condition')}</p>"
                           f"<p><b>POTHOLES:</b> {data.get('pothole_count')} | <b>CRACKS:</b> {data.get('crack_count')}</p>"
                           f"<p><b>DAMAGE AREA:</b> {data.get('damage_percentage')}%</p>"
                           f"<p><b>SEVERITY:</b> {sev}</p><hr style='border: 0.5px solid #333;'>")
            self.report_box.append(report_html)
            self.report_box.verticalScrollBar().setValue(self.report_box.verticalScrollBar().maximum())
        except Exception as e: print(f"Report error: {e}")
            
    def update_score_ui(self):
        self.score = max(0, self.score)
        color = "#00ff88" if self.score > 70 else "#ffaa00" if self.score > 40 else "#ff3333"
        self.score_label.setText(f"Road Quality Index: {self.score}%")
        self.score_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")

    def send_command(self):
        try:
            road, d, v = self.road_name_input.text(), self.distance_input.text(), self.velocity_input.text()
            if self.node and road and d and v:
                self.node.publisher_.publish(String(data=f"{road},{d},{v}"))
                self.status_label.setText(f"Status: 🟢 Mission {road} Started")
                self.start_button.setEnabled(False)
        except Exception: self.status_label.setText("Status: ❌ Error in input")

    def update_image(self, msg):
        try:
            cv_img = CvBridge().imgmsg_to_cv2(msg, 'bgr8')
            h, w, c = cv_img.shape
            print(f"Incoming image: {w}x{h}")

            q_img = QImage(cv_img.data, w, h, 3 * w, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)

            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

            item = QListWidgetItem(f"Detection {self.gallery.count() + 1}")
            item.setData(Qt.UserRole, pixmap)

            item.setIcon(QIcon(
                pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ))

            self.gallery.addItem(item)
            self.gallery.scrollToBottom()

        except Exception as e:
            print(e)


    def on_item_clicked(self, item):
        pixmap = item.data(Qt.UserRole)
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled)
          
    def clear_button(self):
        self.report_box.clear(); self.gallery.clear()
        self.graph.low = self.graph.medium = self.graph.high = 0
        self.graph.update_graph(); self.score = 100; self.update_score_ui()
        self.image_label.clear(); self.image_label.setText("Waiting for Mission..."); self.start_button.setEnabled(True)

def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    node = GUINode(dashboard)
    dashboard.node = node
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    dashboard.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()