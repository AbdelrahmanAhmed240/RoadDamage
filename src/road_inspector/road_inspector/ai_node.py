#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import json
import cv2
from ultralytics import YOLO

class RoadDamageLogic(Node):
    def __init__(self):
        super().__init__('ai_node')
        model_path = '/home/boda240/Damage_Road/src/road_inspector/road_inspector/models/rdd2022_yolov8n_v5_best.onnx'
        self.model = YOLO(model_path, task='detect')
        self.bridge = CvBridge()
        
        # Core Counters
        self.total_frames = 0
        self.pothole_total = 0
        self.crack_total = 0
        self.highest_conf = 0.0

        self.last_detection_time = self.get_clock().now().nanoseconds / 1e9
        self.cooldown_period = 1.5 

        self.pub_gallery = self.create_publisher(Image, '/road_damage/gallery', 10)
        self.pub_final = self.create_publisher(String, '/road_damage/final_report', 10)
        self.create_subscription(String, '/system/state', self.state_monitor, 10)
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.callback, 10)
        self.get_logger().info("✅ AI Logic Node Cleaned & Active.")

    def callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            self.total_frames += 1
            results = self.model.predict(frame, imgsz=640, device='cuda', verbose=False)[0]
            
            if len(results.boxes) > 0:
                current_time = self.get_clock().now().nanoseconds / 1e9
                if (current_time - self.last_detection_time) > self.cooldown_period:
                    for box in results.boxes:
                        cls = int(box.cls[0])
                        self.highest_conf = max(self.highest_conf, float(box.conf[0]))
                        if cls == 3: self.pothole_total += 1
                        else: self.crack_total += 1
                    
                    self.last_detection_time = current_time
                    annotated_img = results.plot()
                    self.pub_gallery.publish(self.bridge.cv2_to_imgmsg(annotated_img, 'bgr8'))
                    
        except Exception as e:
            self.get_logger().error(f"Inference error: {e}")
            
    def state_monitor(self, msg):
        if msg.data == "IDLE" and self.total_frames > 0:
            self.send_final_report()
            self.total_frames = 0
            self.pothole_total = 0
            self.crack_total = 0
            self.highest_conf = 0.0

    def send_final_report(self):
        total_issues = self.pothole_total + self.crack_total
        quality_score = max(0, 100 - (total_issues * 5)) 
        severity = "CRITICAL" if self.highest_conf > 0.7 else "MEDIUM" if self.highest_conf > 0.4 else "LOW"

        payload = {
            "damaged": total_issues > 0,
            "pothole_count": self.pothole_total,
            "crack_count": self.crack_total,
            "damage_percentage": quality_score,
            "correct_percentage": quality_score,
            "severity": severity,
            "road_condition": f"Analysis complete. Identified {total_issues} unique issues."
        }
        self.pub_final.publish(String(data=json.dumps(payload)))

def main(args=None):
    rclpy.init(args=args)
    node = RoadDamageLogic()
    try: rclpy.spin(node)
    except KeyboardInterrupt: node.send_final_report()
    finally:
        node.destroy_node()
        rclpy.shutdown()