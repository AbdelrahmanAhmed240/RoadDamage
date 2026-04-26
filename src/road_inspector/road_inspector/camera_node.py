#!/usr/bin/env python3
import sys
import threading
import os
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import requests
from rclpy.qos import QoSProfile, DurabilityPolicy 

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.phone_ip = "192.168.1.11"
        self.video_url = f"http://{self.phone_ip}:8080/video"
        self.api_url = f"http://{self.phone_ip}:8080/settings/video_recording?set="

        self.bridge = CvBridge()
        self.cap = None
        self.is_active = False
        self.capture_thread = None

        self.qos_profile = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)

        self.create_subscription(String, '/system/state', self.state_callback, self.qos_profile)
        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.ready_pub = self.create_publisher(String, '/camera/ready', 10)

    def state_callback(self, msg):
        if msg.data == "ACTIVE" and not self.is_active:
            self.start_camera_hardware()
        elif msg.data == "IDLE" and self.is_active:
            self.stop_camera_hardware()

    def start_camera_hardware(self):
        try:
            os.system("adb shell monkey -p com.pas.webcam -c android.intent.category.LAUNCHER 1")
            time.sleep(1.2)

            for _ in range(3):
                os.system("adb shell input swipe 540 1800 540 100 100")
            time.sleep(0.8)

            os.system("adb shell input tap 540 2000")

            connected = False
            for _ in range(15):
                self.cap = cv2.VideoCapture(self.video_url)
                if self.cap.isOpened():
                    ret, _ = self.cap.read()
                    if ret:
                        connected = True
                        break
                if self.cap:
                    self.cap.release()
                time.sleep(1)

            if connected:
                # Request better resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

                self.is_active = True
                self.capture_thread = threading.Thread(target=self.stream_loop, daemon=True)
                self.capture_thread.start()

                self.ready_pub.publish(String(data="READY"))

                try:
                    requests.get(self.api_url + "on", timeout=1)
                except:
                    pass
        except Exception as e:
            self.get_logger().error(str(e))

    def stream_loop(self):
        while self.is_active and rclpy.ok():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

                h, w = frame.shape[:2]
                scale = 720 / h
                frame = cv2.resize(frame, (int(w * scale), 720))

                self.image_pub.publish(self.bridge.cv2_to_imgmsg(frame, "bgr8"))
            else:
                time.sleep(0.001)

    def stop_camera_hardware(self):
        self.is_active = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
            self.capture_thread = None
        if self.cap:
            self.cap.release()
            self.cap = None
        try:
            requests.get(self.api_url + "off", timeout=0.5)
        except:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    finally:
        node.stop_camera_hardware()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()