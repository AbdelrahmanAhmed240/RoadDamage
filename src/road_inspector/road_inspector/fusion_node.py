#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class FinalFusionNode(Node):
    def __init__(self):
        super().__init__('final_fusion_node')

        # 1. Subscribers (Waiting for the "Final" summaries from AI and IMU)
        self.ai_sub = self.create_subscription(String, '/damage/detection', self.ai_callback, 10)
        self.imu_sub = self.create_subscription(String, '/imu/data', self.imu_callback, 10)

        # 2. Publisher for GUI
        self.gui_pub = self.create_publisher(String, '/road/final_report', 10)

        # 3. Storage for the two summaries
        self.final_ai_data = None
        self.final_imu_data = None

        self.get_logger().info("🏁 Final Road Analysis Node is active. Waiting for mission summaries...")

    def imu_callback(self, msg):
        self.final_imu_data = json.loads(msg.data)
        self.get_logger().info("📥 Received Final IMU Summary.")
        self.check_and_merge()

    def ai_callback(self, msg):
        self.final_ai_data = json.loads(msg.data)
        self.get_logger().info("📥 Received Final AI Summary.")
        self.check_and_merge()

    def check_and_merge(self):
        # Only process if both nodes have sent their final "Averaged" results
        if self.final_ai_data is not None and self.final_imu_data is not None:
            self.generate_final_verdict()

    def generate_final_verdict(self):
        # Extract variables from the summaries
        ai_damaged = self.final_ai_data.get('damaged', False)
        imu_balance = self.final_imu_data.get('road_balance', 'STABLE')
        
        # Determine the Final Condition based on your requirements
        if ai_damaged and imu_balance == "STABLE":
            condition = "Balanced but have pothole"
        elif ai_damaged and imu_balance == "UNSTABLE":
            condition = "Unbalanced Deep Pothole"
        elif not ai_damaged and imu_balance == "UNSTABLE":
            condition = "Unbalanced and dont have any pothole"
        else:
            condition = "Road Clear & Balanced"

        # Build the merged response for the GUI
        final_response = {
            "damaged": ai_damaged,
            "type": self.final_ai_data.get('type', 'none'),
            "confidence": self.final_ai_data.get('confidence', 0.0),
            "severity": self.final_ai_data.get('severity', 'low'),
            "road_balance": imu_balance,
            "road_condition": condition
        }

        # Send to GUI
        msg = String()
        msg.data = json.dumps(final_response)
        self.gui_pub.publish(msg)
        
        self.get_logger().info(f"✅ Mission Analysis Complete: {condition}")
        
        # Reset storage for the next mission
        self.final_ai_data = None
        self.final_imu_data = None

def main(args=None):
    rclpy.init(args=args)
    node = FinalFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()