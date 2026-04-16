#!/usr/bin/env python3

import sys
import threading
import os
import json
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import requests

# --- ADDED IMPORTS FOR QoS ---
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

        # --- FIX: MATCHING QoS PROFILE ---
        # This ensures the node receives the "ACTIVE" state even if it starts late
        self.qos_profile = QoSProfile(
            depth=10,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # Apply the qos_profile to the subscription
        self.create_subscription(
            String, 
            '/system/state', 
            self.state_callback, 
            self.qos_profile
        )
        
        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.ready_pub = self.create_publisher(String, '/camera/ready', 10)

        self.get_logger().info("📷 Camera Node Initialized. Waiting for ACTIVE state...")

    def state_callback(self, msg):
        if msg.data == "ACTIVE" and not self.is_active:
            self.start_camera_hardware()
        elif msg.data == "IDLE" and self.is_active:
            self.stop_camera_hardware()

    def start_camera_hardware(self):
        self.get_logger().info("🚀 High-Speed Launch Initialized...")
        try:
            # A. Launch App
            os.system("adb shell monkey -p com.pas.webcam -c android.intent.category.LAUNCHER 1")
            time.sleep(1.2)

            # B. FAST TRIPLE FLICK
            os.system("adb shell input swipe 540 1800 540 100 100")
            os.system("adb shell input swipe 540 1800 540 100 100")
            os.system("adb shell input swipe 540 1800 540 100 100")
            time.sleep(0.8)

            # C. THE CLICK
            target_x = 540
            target_y = 2000 
            os.system(f"adb shell input tap {target_x} {target_y}")

            # D. WAIT FOR NETWORK
            # Instead of a flat sleep, we loop to find the connection ASAP
            connected = False
            for i in range(10):  # Try for 5 seconds total
                self.get_logger().info(f"🔄 Connection attempt {i+1}...")
                self.cap = cv2.VideoCapture(self.video_url)
                if self.cap.isOpened():
                    connected = True
                    break
                time.sleep(0.5)

            # E. CONNECT OPENCV
            if connected:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.is_active = True
                self.timer = self.create_timer(0.033, self.publish_frame)
                
                # Signal Navigation Node to START MOVING
                self.ready_pub.publish(String(data="READY"))
                self.get_logger().info("✅ Camera Ready. Signal sent to Navigation.")
                
                try:
                    requests.get(self.api_url + "on", timeout=1.0)
                except:
                    pass
            else:
                self.get_logger().error("❌ Stream unreachable after retries.")

        except Exception as e:
            self.get_logger().error(f"❌ Automation Error: {e}")

    def stop_camera_hardware(self):
        self.get_logger().info("💤 Stopping Camera...")
        self.is_active = False
        if hasattr(self, 'timer'):
            self.timer.cancel()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        try:
            requests.get(self.api_url + "off", timeout=0.5)
        except:
            pass

    def publish_frame(self):
        if self.is_active and self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                # Performance Fix: Resize to avoid network lag
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

                msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
                self.image_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_camera_hardware()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()