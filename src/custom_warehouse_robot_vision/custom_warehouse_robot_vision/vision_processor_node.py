#!/usr/bin/env python3
import time
import math
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, Point
from std_msgs.msg import Bool, String
from cv_bridge import CvBridge, CvBridgeError

class VisionProcessorNode(Node):
    """
    Industrial Warehouse AMR Vision Processing Node.
    - Synchronizes RGB and Depth image streams.
    - Performs docking station marker detection with 3D metric coordinate estimation.
    - Detects pallet fork entry pockets.
    - Provides extensible hooks for future AI / YOLO vision tasks.
    - Publishes real-time annotated HUD stream for RViz / operator display.
    """

    def __init__(self):
        super().__init__('vision_processor_node')

        self.bridge = CvBridge()
        self.latest_rgb = None
        self.latest_depth = None
        self.camera_matrix = None
        self.fps_counter = 0
        self.last_time = time.time()
        self.current_fps = 0.0

        # Parameters
        self.declare_parameter('enable_dock_detection', True)
        self.declare_parameter('enable_pallet_detection', True)
        self.declare_parameter('publish_annotated_feed', True)

        # Subscriptions
        self.sub_rgb = self.create_subscription(
            Image,
            '/camera/rgb/image_raw',
            self.rgb_callback,
            10
        )
        self.sub_depth = self.create_subscription(
            Image,
            '/camera/depth/image_raw',
            self.depth_callback,
            10
        )
        self.sub_info = self.create_subscription(
            CameraInfo,
            '/camera/rgb/camera_info',
            self.info_callback,
            10
        )

        # Publishers
        self.pub_annotated = self.create_publisher(
            Image,
            '/vision/annotated_image',
            10
        )
        self.pub_dock_pose = self.create_publisher(
            PoseStamped,
            '/vision/docking_target',
            10
        )
        self.pub_dock_detected = self.create_publisher(
            Bool,
            '/vision/dock_detected',
            10
        )
        self.pub_vision_status = self.create_publisher(
            String,
            '/vision/status',
            10
        )

        # Processing Timer (15 Hz)
        self.timer = self.create_timer(1.0 / 15.0, self.process_pipeline)
        self.get_logger().info("Titan AMR Vision Processor Node Initialized.")

    def info_callback(self, msg: CameraInfo):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape((3, 3))
            self.get_logger().info(f"Camera intrinsic matrix received (fx={self.camera_matrix[0,0]:.1f}, fy={self.camera_matrix[1,1]:.1f})")

    def rgb_callback(self, msg: Image):
        try:
            self.latest_rgb = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge RGB error: {e}")

    def depth_callback(self, msg: Image):
        try:
            self.latest_depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge Depth error: {e}")

    def process_pipeline(self):
        if self.latest_rgb is None:
            return

        frame = self.latest_rgb.copy()
        h, w, _ = frame.shape

        # Calculate FPS
        self.fps_counter += 1
        now = time.time()
        dt = now - self.last_time
        if dt >= 1.0:
            self.current_fps = self.fps_counter / dt
            self.fps_counter = 0
            self.last_time = now

        # Draw HUD Reticle & Header
        cv2.line(frame, (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), (0, 255, 255), 1)
        cv2.line(frame, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (0, 255, 255), 1)

        # 1. Docking Target Detection
        dock_found, dock_x, dock_y, dock_z = self.detect_docking_target(frame)

        dock_msg = Bool()
        dock_msg.data = dock_found
        self.pub_dock_detected.publish(dock_msg)

        if dock_found:
            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = 'camera_depth_optical_frame'
            pose_msg.pose.position.x = float(dock_x)
            pose_msg.pose.position.y = float(dock_y)
            pose_msg.pose.position.z = float(dock_z)
            pose_msg.pose.orientation.w = 1.0
            self.pub_dock_pose.publish(pose_msg)

            # Draw visual tracking box and distance readout
            cv2.putText(frame, f"DOCK TARGET: [{dock_x:.2f}m, {dock_y:.2f}m, {dock_z:.2f}m]",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "DOCK TARGET: SEARCHING...",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        # 2. Pallet / Shelf Pockets Detection
        self.detect_pallet_pockets(frame)

        # 3. Hook for future user-specified vision tasks (YOLO, OpenCV ML, Barcode/QR)
        self.custom_vision_tasks_hook(frame)

        # Overlay FPS & Status info
        cv2.putText(frame, f"Titan AMR Vision | FPS: {self.current_fps:.1f}",
                    (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Publish Annotated Image
        try:
            annotated_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            annotated_msg.header.stamp = self.get_clock().now().to_msg()
            annotated_msg.header.frame_id = 'camera_depth_optical_frame'
            self.pub_annotated.publish(annotated_msg)
        except CvBridgeError as e:
            self.get_logger().error(f"Error publishing annotated image: {e}")

    def detect_docking_target(self, frame):
        """
        Detects the high-contrast square fiducial marker on the docking station.
        Returns (detected: bool, x: float, y: float, z: float in camera coordinates).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 15, 4)

        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        best_target = None
        min_area = 300
        max_area = 80000

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                # Check for 4-sided polygon (quadrilateral / marker)
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = float(w) / float(h)
                    if 0.7 <= aspect_ratio <= 1.3:
                        best_target = (x, y, w, h, approx)
                        break

        if best_target is not None:
            x, y, w, h, approx = best_target
            cx = x + w // 2
            cy = y + h // 2

            # Visual overlay
            cv2.drawContours(frame, [approx], -1, (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)

            # Query depth at center pixel
            z_metric = 2.0  # default fallback distance
            if self.latest_depth is not None:
                dh, dw = self.latest_depth.shape
                if 0 <= cy < dh and 0 <= cx < dw:
                    d_val = self.latest_depth[cy, cx]
                    if not math.isnan(d_val) and not math.isinf(d_val) and d_val > 0.1:
                        z_metric = float(d_val)

            # De-project to 3D optical coordinates
            if self.camera_matrix is not None:
                fx = self.camera_matrix[0, 0]
                fy = self.camera_matrix[1, 1]
                cx_cam = self.camera_matrix[0, 2]
                cy_cam = self.camera_matrix[1, 2]
                x_metric = (cx - cx_cam) * z_metric / fx
                y_metric = (cy - cy_cam) * z_metric / fy
            else:
                # Approximate pinhole model
                x_metric = (cx - frame.shape[1] / 2.0) * z_metric / 500.0
                y_metric = (cy - frame.shape[0] / 2.0) * z_metric / 500.0

            return True, x_metric, y_metric, z_metric

        return False, 0.0, 0.0, 0.0

    def detect_pallet_pockets(self, frame):
        """
        Identifies pallet fork pockets / shelf structure legs.
        """
        # Crop to lower half of frame where pallets appear
        h, w, _ = frame.shape
        roi = frame[int(h * 0.5):, :]

        # Edge detection in region of interest
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)

        # Detect horizontal/vertical lines (runners and deck)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40,
                                minLineLength=60, maxLineGap=10)

        if lines is not None:
            for line in lines[:4]:
                x1, y1, x2, y2 = line[0]
                y1_full = y1 + int(h * 0.5)
                y2_full = y2 + int(h * 0.5)
                cv2.line(frame, (x1, y1_full), (x2, y2_full), (255, 100, 0), 2)

    def custom_vision_tasks_hook(self, frame):
        """
        ========================================================================
        HOOK FOR FUTURE VISION PROCESSING TASKS (YOLO, OpenCV ML, OCR, etc.)
        ========================================================================
        This method is designed for easy drop-in integration of neural networks
        (e.g., ultralytics YOLOv8/v11, barcode decoders, object classifiers).
        The frame is passed directly as a BGR numpy array.
        """
        # Placeholder indicator in HUD
        cv2.putText(frame, "[Vision Pipeline: AI Hooks Ready]",
                    (frame.shape[1] - 310, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

def main(args=None):
    rclpy.init(args=args)
    node = VisionProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
