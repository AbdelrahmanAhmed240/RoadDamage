#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from std_msgs.msg import String
import socket
import time

class NavigationNode(Node):
    def __init__(self):
        super().__init__('navigation_node')
        
        # 1. QoS Profile: TRANSIENT_LOCAL ensures late-joiners get the latest state
        self.state_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # Connection Config
        self.esp32_ip = "192.168.1.30" 
        self.port = 8080 
        
        # Pubs & Subs
        self.state_pub = self.create_publisher(String, '/system/state', self.state_qos)
        self.create_subscription(String, '/cmd_move', self.cmd_callback, 10)
        self.create_subscription(String, '/camera/ready', self.camera_ready_callback, 10)
        self.pending_mission = None
        self.get_logger().info(f"🚀 Mission Control Online. Target ESP: {self.esp32_ip}")

    def send_socket_command(self, message, travel_time):
        """
        Handles UDP communication with the ESP32.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(travel_time + 2.0) # Wait long enough for mission to finish
                
                self.get_logger().info(f"📡 Sending UDP: {message}")
                s.sendto((message + "\n").encode('utf-8'), (self.esp32_ip, self.port))
                
                # Receive 'FINISHED' from ESP32
                data, addr = s.recvfrom(1024)
                return data.decode('utf-8').strip()
        except socket.timeout:
            self.get_logger().error("🛑 Connection Timed Out: ESP32 did not respond in time.")
            return "TIMEOUT"
        except Exception as e:
            self.get_logger().error(f"🌐 Connection Failed: {e}")
            return None

    def cmd_callback(self, msg):
        parts = msg.data.split(',')
        if len(parts) < 3: return
        
        self.pending_mission = {
            'road': parts[0],
            'dist': float(parts[1]),
            'vel': float(parts[2])
        }
        
        self.get_logger().info(f"⏳ Mission {parts[0]} Queued. Waiting for Camera...")
        self.publish_state("ACTIVE")
            
    def camera_ready_callback(self, msg):
        if msg.data == "READY" and self.pending_mission:
            mission = self.pending_mission
            travel_time = mission['dist'] / mission['vel']
            
            self.get_logger().info("🟢 Camera is LIVE. Executing Movement!")
            
            # Execute the movement now that we know the camera is working
            command = f"MOVE:{travel_time}"
            response = self.send_socket_command(command, travel_time)
            
            # Mission finished
            self.publish_state("IDLE")
            self.pending_mission = None
                
    def publish_state(self, state):
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)
        self.get_logger().info(f"Broadcasted State: {state}")

def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("📴 Shutting down Mission Control.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()