# AprilTag Detector

A ROS 2 package for detecting AprilTags from camera feed and estimating their pose in 3D space.

## Overview

This package provides ROS 2 nodes that:
- Subscribe to camera image and camera info topics
- Detect AprilTags (Tag36h11 family) in the image
- Estimate the 3D pose (position and orientation) of detected tags
- Publish detected tag poses as `SharedControlGoalArray` messages for shared control applications
- Transform detected poses to a target frame (e.g., robot base_link) using TF2

## Features

- Real-time AprilTag detection using the apriltag library
- 3D pose estimation for each detected tag
- Configurable tag sizes and detection parameters
- Supports USB camera integration via usb_cam
- Flexible topic remapping for different camera setups
- TF2-based pose transformation to target frames
- Composable node architecture for efficient processing

## Dependencies

- ROS 2 (Humble or later)
- OpenCV
- apriltag
- Eigen3
- cv_bridge
- sensor_msgs
- geometry_msgs
- tf2
- tf2_ros
- tf2_geometry_msgs
- rclcpp
- rclcpp_components
- usb_cam (for camera input)
- extender_msgs (custom message types)

## Installation

Build the package with colcon:

```bash
sudo apt-get install ros-humble-usb-cam
sudo apt-get install ros-humble-apriltag ros-humble-apriltag-ros

cd /home/megane/ros2_humble_ws
colcon build --packages-select apriltag_detector
source install/setup.bash
```

## Usage

### Launch the detector with USB camera

Run the complete detection pipeline with USB camera input:

```bash
ros2 launch apriltag_detector explorer_camera_detection.launch.py
```

This will:
1. Start the USB camera node (configured for `/dev/video0` with calibration from `explorer_camera_calib.yaml`)
2. Start the AprilTag detector node
3. Start the AprilTag bridge node for pose transformation

### Run detector only

If you already have a camera node running:

```bash
ros2 run apriltag_detector apriltag_detector
```

## Configuration

### AprilTag Detector Config

Configure the detector in `config/tags_params.yaml`:

```yaml
apriltag_detector:
  ros__parameters:
    max_hamming_distance: 1          # Maximum Hamming distance for detection
    tag_sizes:
      "0": 0.024                     # Tag ID: size in meters
      "1": 0.024
      "2": 0.024
      # ... up to tag ID 9
```

Parameters:
- `max_hamming_distance`: Maximum acceptable Hamming distance for tag detection (higher = more permissive)
- `tag_sizes.<tag_id>`: Physical size of each tag in meters (required for pose estimation)

## Topics

### Subscriptions

- `/image_raw` (sensor_msgs/Image): Raw camera image
- `/camera_info` (sensor_msgs/CameraInfo): Camera calibration information

### Publications

- `/tag_detections` (extender_msgs/AprilTagPoseArray): Array of detected tags with their 3D poses

## Message Structure

The detector publishes `AprilTagPoseArray` messages containing:

```
detected_tags: AprilTagPose[]
  id: int32                  # AprilTag ID
  tag_pose: geometry_msgs/PoseStamped
    header: Header
      frame_id: str
      stamp: Time
    pose: Pose
      position: Point (x, y, z)
      orientation: Quaternion (x, y, z, w)
```