# Tools

ROS 2 packages for hand tracking, visualization, and testing with offline data sources.

## Packages

### [mediapipe_mocap](mediapipe_mocap/)
Detects hand landmarks from RGB images using Google MediaPipe HandLandmarker. Includes the integrated `viewer_node` for overlay visualization with MediaPipe drawing utilities. Features:
- Real-time hand tracking with 21 3D landmarks per hand
- Configurable detection thresholds
- Low-latency sensor data QoS
- Built-in viewer for on-screen overlay

### [offline_media_publisher](offline_media_publisher/)
Publishes images or video frames as simulated camera streams for testing:
- **image_publisher**: Pattern-based image selection (`hand*.jpg`), configurable FPS, cyclic playback
- **video_publisher**: Sequential video playback (`hand*.mp4`), fixed FPS override, automatic looping

## Building

Build all packages:
```bash
cd /path/to/workspace
colcon build --packages-select mediapipe_mocap offline_media_publisher
source install/setup.bash
```

Or build individual packages:
```bash
colcon build --packages-select mediapipe_mocap
```

## Quick Start

1. **MediaPipe model**: The hand landmarker model is **provided by default** in `mediapipe_mocap/models/`. Alternatively, download the latest version:
   ```bash
   wget https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
   ```

2. **Run with offline video**:
   ```bash
   # Terminal 1: Publish video frames
   ros2 run offline_media_publisher video_publisher \
     --ros-args -p folder_path:=/path/to/videos -p fps:=30

   # Terminal 2: Detect hand landmarks
   ros2 launch mediapipe_mocap hand_landmarks_launch.py

   # Terminal 3: Visualize results
   ros2 launch mediapipe_mocap viewer_launch.py
   ```

3. **Run with live camera**:
   ```bash
   # Terminal 1: Your camera node publishing to /camera/color/image_raw
   
   # Terminal 2: Detect hand landmarks
   ros2 launch mediapipe_mocap hand_landmarks_launch.py

   # Terminal 3: Visualize results
   ros2 launch mediapipe_mocap viewer_launch.py
   ```

## Dependencies

- ROS 2 (Humble or later)
- Python 3
- OpenCV
- cv_bridge
- MediaPipe (Python): `pip install mediapipe`
- NumPy

## License

BSD-3-Clause


