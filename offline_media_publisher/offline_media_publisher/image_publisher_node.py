import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge

import cv2
import glob
import os


class ImagePublisher(Node):
    """
    Publish images from a folder alternately as a ROS2 Image message
    on topic /camera/color/image_raw.

    Scans the folder for images matching configurable extensions
    (default: .jpg, .jpeg, .png, .bmp, .tiff, .tif) and alternates between them.
    """

    def __init__(self):
        super().__init__("image_publisher")

        # Declare parameters
        self.declare_parameter('folder_path', '')
        self.declare_parameter('fps', 100)
        self.declare_parameter('image_extensions', '.jpg,.jpeg,.png,.bmp,.tiff,.tif')
        
        folder_path = self.get_parameter('folder_path').get_parameter_value().string_value
        fps = int(self.get_parameter('fps').get_parameter_value().integer_value)
        
        if not folder_path:
            raise RuntimeError("Parameter 'folder_path' must be provided")
        
        # Resolve extensions to scan
        exts_raw = self.get_parameter('image_extensions').get_parameter_value().string_value
        exts = [e.strip() for e in exts_raw.split(',') if e.strip()]
        if not exts:
            exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

        # Scan folder for images matching each extension
        paths_set = set()
        for ext in exts:
            pattern = os.path.join(folder_path, f"*{ext}")
            for p in glob.glob(pattern):
                paths_set.add(p)
        self.image_paths = sorted(paths_set)
        
        if not self.image_paths:
            raise RuntimeError(
                f"No images found in {folder_path} with extensions: {', '.join(exts)}"
            )

        self.get_logger().info(f"Found {len(self.image_paths)} images in {folder_path}:")
        for p in self.image_paths:
            self.get_logger().info(f"  {os.path.basename(p)}")

        # Load all images (OpenCV BGR)
        self.cv_images = []
        for path in self.image_paths:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                raise RuntimeError(f"Failed to read image: {path}")
            self.cv_images.append(img)

        # Optional sanity check: advise if sizes differ
        shapes = [img.shape for img in self.cv_images]
        if len(set(shapes)) > 1:
            self.get_logger().warn(
                f"Images have different sizes. "
                "This is allowed, but some consumers may assume constant resolution."
            )

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, "/camera/color/image_raw", 10)

        # Index of the current image
        self.current_index = 0

        # Timer: publish at configured FPS and alternate image each time
        self.timer = self.create_timer(1.0 / fps, self.publish_image)

        h, w, _ = self.cv_images[0].shape
        self.get_logger().info(
            f"Image publisher started. Publishing {len(self.cv_images)} images alternately on /camera/color/image_raw "
            f"at {fps} Hz, base resolution {w}x{h}."
        )

    def publish_image(self):
        # Select current image
        img = self.cv_images[self.current_index]

        msg = self.bridge.cv2_to_imgmsg(img, encoding="bgr8")
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_color_optical_frame"

        self.publisher.publish(msg)

        # Cycle through images: 0 → 1 → 2 → ... → n-1 → 0 → ...
        self.current_index = (self.current_index + 1) % len(self.cv_images)


def main(args=None):
    rclpy.init(args=args)
    node = ImagePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
