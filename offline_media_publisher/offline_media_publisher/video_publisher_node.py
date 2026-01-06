import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge

import cv2
import glob
import os


class VideoPublisher(Node):
    """
    Publish frames from video files in a folder as ROS2 Image messages
    on topic /camera/color/image_raw.

    Scans the folder for video files matching configurable extensions
    (default: .mp4, .avi, .mov, .mkv, .m4v, .webm) and plays them sequentially.
    """

    def __init__(self):
        super().__init__("video_publisher")

        # Declare parameters
        self.declare_parameter('folder_path', '')
        self.declare_parameter('fps', 50)
        self.declare_parameter('video_extensions', '.mp4,.avi,.mov,.mkv,.m4v,.webm')
        
        folder_path = self.get_parameter('folder_path').get_parameter_value().string_value
        self.fps = int(self.get_parameter('fps').get_parameter_value().integer_value)
        
        if not folder_path:
            raise RuntimeError("Parameter 'folder_path' must be provided")
        
        # Resolve extensions to scan
        exts_raw = self.get_parameter('video_extensions').get_parameter_value().string_value
        exts = [e.strip() for e in exts_raw.split(',') if e.strip()]
        if not exts:
            exts = ['.mp4', '.avi', '.mov', '.mkv', '.m4v', '.webm']

        # Scan folder for video files matching each extension
        paths_set = set()
        for ext in exts:
            pattern = os.path.join(folder_path, f"*{ext}")
            for p in glob.glob(pattern):
                paths_set.add(p)
        self.video_paths = sorted(paths_set)
        
        if not self.video_paths:
            raise RuntimeError(
                f"No videos found in {folder_path} with extensions: {', '.join(exts)}"
            )

        self.get_logger().info(f"Found {len(self.video_paths)} videos in {folder_path}:")
        for p in self.video_paths:
            self.get_logger().info(f"  {os.path.basename(p)}")

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, "/camera/color/image_raw", 10)

        # Initialize video capture for the first video
        self.current_video_index = 0
        self.cap = None
        self.frame_width = None
        self.frame_height = None
        
        self._open_next_video()

        # Timer: publish frames at fixed FPS rate
        self.timer = self.create_timer(1.0 / self.fps, self.publish_frame)

        self.get_logger().info(
            f"Video publisher started. Publishing frames from {len(self.video_paths)} videos "
            f"on /camera/color/image_raw at {self.fps} Hz, resolution {self.frame_width}x{self.frame_height}."
        )

    def _open_next_video(self):
        """Open the next video file in the list."""
        if self.cap is not None:
            self.cap.release()
        
        if self.current_video_index >= len(self.video_paths):
            self.get_logger().info("All videos have been played. Looping back to the first video.")
            self.current_video_index = 0
        
        video_path = self.video_paths[self.current_video_index]
        self.get_logger().info(f"Opening video: {os.path.basename(video_path)}")
        
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        # Get video properties (frame dimensions only; FPS is fixed)
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.current_video_index += 1

    def publish_frame(self):
        """Read and publish the next frame from the current video."""
        ret, frame = self.cap.read()
        
        if not ret:
            # End of current video, open the next one
            self._open_next_video()
            ret, frame = self.cap.read()
            
            if not ret:
                self.get_logger().warn("Failed to read first frame of next video")
                return
        
        # Convert frame to ROS2 Image message
        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_color_optical_frame"

        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = VideoPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
