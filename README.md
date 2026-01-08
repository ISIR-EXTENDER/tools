# Tools

A collection of utility packages for the extender robot control framework, providing message definitions, motion capture, media publishing, and data replay capabilities.

## Packages

### extender_msgs
**Package**: `extender_msgs`

ROS2 message definitions for the extender framework. Defines custom message types for teleoperation commands and joint position control.

**Messages**:
- `TeleopCommand`: Teleoperation commands with velocity and mode selection
- `JointPositionCommand`: Joint position commands with named joint targeting

### mediapipe_mocap
**Package**: `mediapipe_mocap`

Motion capture using Google MediaPipe. Detects and tracks landmarks from RGB camera streams with real-time visualization capabilities.


**Components**:
- `hand_landmarks_node`: Detects hand landmarks from an image using mediapipe
- `viewer_node`: Display the landmarks from mediapipe

### offline_media_publisher
**Package**: `offline_media_publisher`

Simulated camera stream publisher for testing and development. Publishes images or video files as camera topics without requiring physical cameras.

**Components**:
- `image_publisher`: Publishes static images or image sequences
- `video_publisher`: Publishes video files with configurable playback

## Dependencies

### Common Dependencies
- ROS2 (Humble or later)
- Python 3

### Package-Specific Dependencies

**mediapipe_mocap**:
- MediaPipe
- OpenCV
- NumPy

**offline_media_publisher**:
- OpenCV

**extender_msgs**:
- ROS2 message generation tools

## Contributing

When adding new tools:
1. Follow ROS2 package structure conventions
2. Include comprehensive documentation
3. Add appropriate tests and examples
4. Update this README with package descriptions
5. Ensure compatibility with the extender framework

## License

TODO: Add license information


