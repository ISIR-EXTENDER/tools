# AprilTag Detector

A ROS 2 package for detecting AprilTags from camera feed and estimating their pose in 3D space.

## Overview

This package provides a ROS 2 node that:
- Subscribes to camera image and camera info topics
- Detects AprilTags (Tag36h11 family) in the image
- Estimates the 3D pose (position and orientation) of detected tags
- Publishes detected tag poses as `AprilTagPoseArray` messages

## Features

- Real-time AprilTag detection using the apriltag library
- 3D pose estimation for each detected tag
- Configurable tag sizes and detection parameters
- Supports USB camera integration via usb_cam
- Flexible topic remapping for different camera setups

## Dependencies

- ROS 2 (Humble or later)
- OpenCV
- apriltag
- Eigen3
- cv_bridge
- sensor_msgs
- rclcpp
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
ros2 launch apriltag_detector detection.launch.py
```

This will:
1. Start the USB camera node (configured for `/dev/video4` with calibration from `explorer_camera_calib.yaml`)
2. Start the AprilTag detector node

### Run detector only

If you already have a camera node running:

```bash
ros2 run apriltag_detector apriltag_detector
```

## Configuration

### AprilTag Detector Config

Configure the detector in `config/apriltag_detector.yaml`:

```yaml
apriltag_detector:
  ros__parameters:
    max_hamming_distance: 1          # Maximum Hamming distance for detection
    tag_publisher_topic: "/tag_detections"  # Output topic
    tag_sizes:
      0: 0.1                         # Tag ID: size in meters
      1: 0.1
      2: 0.15
```

Parameters:
- `max_hamming_distance`: Maximum acceptable Hamming distance for tag detection (higher = more permissive)
- `tag_sizes.<tag_id>`: Physical size of each tag in meters (required for pose estimation)
- `tag_publisher_topic`: Topic where detected tag poses are published

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