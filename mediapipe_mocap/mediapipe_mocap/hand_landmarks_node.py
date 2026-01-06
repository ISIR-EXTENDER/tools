import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, PointCloud
from geometry_msgs.msg import Point32
from cv_bridge import CvBridge

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)


import time
import platform
import os
from ament_index_python.packages import get_package_share_directory


class HandLandmarksNode(Node):
    """
    Subscribe to an RGB image, run MediaPipe Tasks HandLandmarker,
    publish hand landmarks as a PointCloud.

    Output semantics (for the FIRST detected hand):
      - 21 points in fixed order (MediaPipe index 0..20)
      - point.x = normalized x in [0,1]
      - point.y = normalized y in [0,1]
      - point.z = normalized depth-like z (wrist ≈ 0)  :contentReference[oaicite:4]{index=4}

    header.frame_id and header.stamp are copied from the input Image.
    """

    def __init__(self):
        super().__init__('hand_landmarks_node')

        # Get package share directory for default model path
        package_share_dir = get_package_share_directory('mediapipe_mocap')
        default_model_path = os.path.join(package_share_dir, 'models', 'hand_landmarker.task')

        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('image_topic', '/camera/color/image_raw'),
                ('landmarks_topic', '/hand_landmarks'),
                ('model_path', default_model_path),
                ('num_hands', 1),
                ('min_hand_detection_confidence', 0.5),
                ('min_hand_presence_confidence', 0.5),
                ('min_tracking_confidence', 0.5)
            ]
        )


        # Retrieve parameters
        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        landmarks_topic = self.get_parameter('landmarks_topic').get_parameter_value().string_value
        model_path = self.get_parameter('model_path').get_parameter_value().string_value
        # Use default path if YAML provides empty string
        if not model_path:
            model_path = default_model_path
        num_hands = int(self.get_parameter('num_hands').get_parameter_value().integer_value)
        min_det_conf = float(
            self.get_parameter('min_hand_detection_confidence').get_parameter_value().double_value
        )
        min_presence_conf = float(
            self.get_parameter('min_hand_presence_confidence').get_parameter_value().double_value
        )
        min_track_conf = float(
            self.get_parameter('min_tracking_confidence').get_parameter_value().double_value
        )

        self.bridge = CvBridge()

        # ---------------- Publisher / Subscriber ----------------
        self.landmarks_pub = self.create_publisher(PointCloud, landmarks_topic, 10)

        self.image_sub = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            20
        )

        # Detect delegate: use GPU on native Linux, CPU on WSL or other systems
        delegate = self._get_best_delegate()
        
        options = HandLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=model_path,
                delegate=delegate
            ),
            running_mode=RunningMode.VIDEO,   # stream of frames with timestamps
            num_hands=num_hands,
            min_hand_detection_confidence=min_det_conf,
            min_hand_presence_confidence=min_presence_conf,
            min_tracking_confidence=min_track_conf,
        )

        self.landmarker = HandLandmarker.create_from_options(options)
        
        self.get_logger().info(
            f'HandLandmarksNode started.\n'
            f'  image_topic      = {image_topic}\n'
            f'  landmarks_topic  = {landmarks_topic}\n'
            f'  model_path       = {model_path}'
        )

        self.last_time = time.time()
        self.frame_count = 0

    # -------------------------------------------------------------
    # Image callback: convert ROS image → MediaPipe Image → detect
    # -------------------------------------------------------------
    def image_callback(self, msg: Image):
        # Convert ROS Image to OpenCV BGR
        try:
            cv_bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Error converting RGB image: {e}')
            return

        # BGR → RGB (MediaPipe expects SRGB)
        cv_rgb = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2RGB)

        # Wrap as MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv_rgb)

        # Use ROS time as monotonically increasing timestamp (ms)
        ts_ms = (
            msg.header.stamp.sec * 1000
            + msg.header.stamp.nanosec // 1_000_000
        )

        try:
            result = self.landmarker.detect_for_video(mp_image, ts_ms)
        except Exception as e:
            self.get_logger().error(f'Error in HandLandmarker.detect_for_video: {e}')
            return

        if not result.hand_landmarks:
            # No hands → nothing to publish
            self.get_logger().debug('No hand detected in current frame.')
            return
        
        # Extract first hand's landmarks
        cloud = PointCloud()
        cloud.header = msg.header
        cloud.points = [Point32(x=float(lm.x), y=float(lm.y), z=float(lm.z)) for lm in result.hand_landmarks[0]]
        self.landmarks_pub.publish(cloud)

        self.get_logger().debug(f'Published {len(cloud.points)} landmarks.')

        # --- FPS MEASUREMENT (debug mode only) ---
        if self.get_logger().is_enabled_for(rclpy.logging.LoggingSeverity.DEBUG):
            self.frame_count += 1
            now = time.time()
            elapsed = now - self.last_time
            if elapsed >= 1.0:  # every 1 second
                fps = self.frame_count / elapsed
                self.get_logger().debug(f"Mediapipe FPS = {fps:.2f}")
                self.last_time = now
                self.frame_count = 0

    

    def destroy_node(self):
        # Cleanly close MediaPipe resources
        try:
            self.landmarker.close()
        except Exception:
            pass
        super().destroy_node()

    def _is_wsl(self) -> bool:
        """Check if running on Windows Subsystem for Linux."""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower() or 'wsl' in f.read().lower()
        except Exception:
            return False

    def _get_best_delegate(self) -> str:
        """Get the best delegate available on the current platform."""
        system = platform.system()
        delegate = mp.tasks.BaseOptions.Delegate.CPU
        delegate_name = 'CPU'
        if system == 'Linux':
            if not self._is_wsl():
                system = 'Linux (native)'
                delegate = mp.tasks.BaseOptions.Delegate.GPU
                delegate_name = 'GPU'
            else:
                system = 'WSL (Windows Subsystem for Linux)'
        elif system == 'Darwin':
            system = 'macOS'
        self.get_logger().info(f'Platform: {system}. Using {delegate_name} delegate.')
        return 'CPU'


def main(args=None):
    rclpy.init(args=args)
    node = HandLandmarksNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
