# Extender Messages

A ROS2 message package that defines custom message types for the extender robot control framework. This package provides standardized interfaces for teleoperation and joint control commands.

## Overview

The `extender_msgs` package contains ROS2 message definitions used throughout the extender project for:

- **Teleoperation Commands**: Structured messages for robot teleoperation with mode selection
- **Joint Position Commands**: Messages for direct joint-space position control
- **Standardized Interfaces**: Consistent message formats across different controllers and interfaces

## Messages

### TeleopCommand

A comprehensive teleoperation command message that combines velocity commands with operational modes.

**Fields**:

- **`twist`** (`geometry_msgs/Twist`): Desired Cartesian velocity command
  - `linear`: Linear velocity components (x, y, z) in m/s
  - `angular`: Angular velocity components (x, y, z) in rad/s

- **`mode`** (`uint8`): Teleoperation mode selector
  - `TRANSLATION_ROTATION` (0): Combined translation and rotation control
  - `ROTATION` (1): Rotation-only control (linear velocity ignored)
  - `TRANSLATION` (2): Translation-only control (angular velocity ignored)
  - `BOTH` (3): Full 6DOF control (legacy mode)

### JointPositionCommand

A message for commanding specific joint positions by name.

**Fields**:

- **`joint_names`** (`string[]`): Array of joint names to command
- **`desired_position`** (`float64[]`): Corresponding target positions in radians (or meters for prismatic joints)

**Requirements**:
- `joint_names` and `desired_position` arrays must have the same length
- Joint names must match those defined in the robot's URDF
- Positions must be within joint limits

### AprilTagPose

A message representing the detected pose of a single AprilTag.

**Fields**:

- **`id`** (`int32`): Unique identifier of the detected AprilTag
- **`tag_pose`** (`geometry_msgs/Pose`): 3D pose of the tag in the camera frame
  - `position`: 3D position (x, y, z) in meters
  - `orientation`: Quaternion (x, y, z, w) representing tag orientation

### AprilTagPoseArray

A collection of detected AprilTag poses.

**Fields**:

- **`detected_tags`** (`extender_msgs/AprilTagPose[]`): Array of detected AprilTags with their poses

**Usage**: Used for publishing results from AprilTag detection pipelines

## Installation

1. Clone the package into your ROS2 workspace:
   ```bash
   cd ~/ros2_ws/src
   git clone <repository-url>
   ```

2. Build the workspace:
   ```bash
   colcon build --packages-select extender_msgs
   ```

The messages will be automatically generated and made available to other ROS2 packages.
