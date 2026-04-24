#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2, json, os
from ultralytics import YOLO

# Configuration from AI Integration Guide [cite: 78-83]
CLASS_NAMES  = ['longitudinal_crack', 'transverse_crack', 'alligator_crack', 'pothole']
CLASS_COLORS = [(46,34,231), (235,152,52), (50,205,50), (18,153,255)]
CONF_DROP    = 0.25  # Optimal threshold [cite: 161]
CONF_LOW     = 0.40
CONF_MEDIUM  = 0.60

# Updated path based on your folder structure [cite: 84]
# Check your folder and find the actual .pt file inside it
# It is likely named 'best.pt' or 'rdd2022_yolov8n_v5_best.pt'
# Try this path - note the 'weights' subfolder which is common in YOLO exports
# Updated path to the folder that contains the actual model data
MODEL_PATH = '/home/boda240/Damage_Road/src/road_inspector/road_inspector/models/rdd2022_yolov8n_v5_best.pt/best'
class RoadDamageNode(Node):
    def __init__(self):
        super().__init__('ai_node') # Updated node name
        
        # Load the YOLO model [cite: 88]
        # Since it's a folder, Ultralytics will load the required data inside automatically
        self.model = YOLO(MODEL_PATH)
        self.bridge = CvBridge()
        self.frame_id = 0

        # Subscribers and Publishers [cite: 91-97]
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.callback, 10)
        self.pub_json = self.create_publisher(String, '/road_damage/detections', 10)
        self.pub_img  = self.create_publisher(Image, '/road_damage/image', 10)

        self.get_logger().info("AI Node started. Ready for road inspection!")

    def get_severity(self, conf):
        """Maps confidence to severity levels as per guide [cite: 98-101]."""
        if conf >= CONF_MEDIUM: return 'high'
        elif conf >= CONF_LOW:  return 'medium'
        else:                   return 'low'

    def callback(self, msg):
        # 1. Convert ROS Image to OpenCV BGR
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        
        # 2. Run Inference (must use imgsz=640)
        result = self.model.predict(frame, imgsz=640, conf=CONF_DROP, device='cuda', verbose=False)[0]

        detections = []
        annotated = frame.copy()

        # Counter variables for your specific JSON request
        pothole_count = 0
        crack_count = 0

        # 3. Process Detections
        for box in result.boxes:
            conf = float(box.conf[0])
            if conf < CONF_DROP: continue
            
            cls = int(box.cls[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            sev = self.get_severity(conf)
            
            # Increment counts based on class name
            if CLASS_NAMES[cls] == 'pothole':
                pothole_count += 1
            else:
                crack_count += 1

            detections.append({
                'class': CLASS_NAMES[cls],
                'confidence': round(conf, 4),
                'severity': sev,
                'bbox': [x1, y1, x2, y2]
            })

            # Draw Annotations
            color = CLASS_COLORS[cls]
            label = f"{CLASS_NAMES[cls]} {conf:.2f} [{sev}]"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, label, (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 4. Publish Results with your requested structure
        if detections:
            dom = max(detections, key=lambda d: d['confidence'])
            
            # Calculations for the summary
            damage_percentage = min((len(detections) * 10), 100) # Logic: 10% per detection
            correct_percentage = 100 - damage_percentage
            
            payload = {
                "damaged": True,
                "pothole_count": pothole_count,
                "crack_count": crack_count,
                "damage_percentage": damage_percentage,
                "correct_percentage": correct_percentage,
                "severity": dom['severity'].upper(),
                "road_condition": f"{damage_percentage}% Damaged: {pothole_count} Holes, {crack_count} Cracks detected."
            }
            
            # Also keep your original detections list inside the payload if needed
            payload['detections'] = detections
            payload['frame_id'] = self.frame_id
            
            self.pub_json.publish(String(data=json.dumps(payload)))
        
        else:
            # Optional: Publish empty state if no damage found
            empty_payload = {
                "damaged": False,
                "pothole_count": 0,
                "crack_count": 0,
                "damage_percentage": 0,
                "correct_percentage": 100,
                "severity": "NONE",
                "road_condition": "Road is clear."
            }
            self.pub_json.publish(String(data=json.dumps(empty_payload)))

        # Always publish the annotated image to the dashboard topic
        img_msg = self.bridge.cv2_to_imgmsg(annotated, 'bgr8')
        self.pub_img.publish(img_msg)
        self.frame_id += 1
        
def main(args=None):
    rclpy.init(args=args)
    node = RoadDamageNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()