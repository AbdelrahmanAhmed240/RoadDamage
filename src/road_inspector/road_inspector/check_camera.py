import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CameraViewer(Node):
    def __init__(self):
        super().__init__('camera_viewer')
        self.subscription = self.create_subscription(Image, '/camera/image_raw', self.listener_callback, 10)
        self.bridge = CvBridge()
        self.get_logger().info("📺 Window opening... Press 'q' to exit.")

    def listener_callback(self, msg):
        # Convert ROS Image message to OpenCV format
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        # Display the frame
        cv2.imshow("Realme Camera Stream", frame)
        
        # Keep window alive; exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    viewer = CameraViewer()
    try:
        rclpy.spin(viewer)
    except SystemExit:
        pass
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()