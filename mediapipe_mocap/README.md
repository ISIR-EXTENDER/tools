# hand_landmarks_mediapipe

ROS 2 node that detects hand landmarks from RGB images using Google MediaPipe and publishes them as a PointCloud message.

## Overview

This package subscribes to camera images and runs MediaPipe's HandLandmarker to detect hand positions in real-time. It outputs 21 normalized 3D landmarks per detected hand.

## Features

- **Real-time hand tracking** using MediaPipe Tasks API
- **Configurable detection thresholds** for detection, presence, and tracking confidence
- **FPS measurement** to monitor processing performance
- **Low-latency mode** using sensor data QoS profile
- **Built-in viewer** to overlay landmarks with MediaPipe drawing styles

## Published Topics

- `/hand_landmarks` (`sensor_msgs/PointCloud`) - 21 normalized hand landmarks
  - `point.x`: normalized x coordinate [0, 1]
  - `point.y`: normalized y coordinate [0, 1]
  - `point.z`: normalized depth-like value (wrist ≈ 0)

## Subscribed Topics

- `/camera/color/image_raw` (`sensor_msgs/Image`) - Input RGB images

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_topic` | string | `/camera/color/image_raw` | Input image topic |
| `landmarks_topic` | string | `/hand_landmarks` | Output landmarks topic |
| `model_path` | string | `<auto-resolved>` | Path to MediaPipe model file (auto-resolved to `<package_share>/models/hand_landmarker.task`) |
| `num_hands` | int | 1 | Maximum number of hands to detect |
| `min_hand_detection_confidence` | double | 0.5 | Minimum confidence for hand detection |
| `min_hand_presence_confidence` | double | 0.5 | Minimum confidence for hand presence |
| `min_tracking_confidence` | double | 0.5 | Minimum tracking confidence |
 

## Usage

### Prerequisites

1. Install MediaPipe:
   ```bash
   pip install mediapipe
   ```

2. The MediaPipe hand landmarker model is **provided by default** in the `models/` folder of this package and automatically resolved at runtime.

### Running the Node

Use the launch file (recommended):

```bash
ros2 launch hand_landmarks_mediapipe hand_landmarks_launch.py
```

Or run directly (model path is auto-resolved):

```bash
ros2 run hand_landmarks_mediapipe hand_landmarks_node
```

### Running the Viewer

Use the bundled viewer to overlay landmarks on the input image:

```bash
ros2 launch hand_landmarks_mediapipe viewer_launch.py
```

Or run directly:

```bash
ros2 run hand_landmarks_mediapipe viewer_node
```

Topics can be overridden via parameters (`image_topic`, `landmarks_topic`, `window_name`).

### Configuration

Parameters are loaded from `config/hand_landmarks_node.yaml`. 

**Model path handling:**
- By default, `model_path` is left empty in the YAML file, which triggers automatic resolution to `<package_share>/models/hand_landmarker.task`
- To use a custom model, edit `config/hand_landmarks_node.yaml` and set `model_path` to an absolute path:
  ```yaml
  hand_landmarks_node:
    ros__parameters:
      model_path: "/path/to/custom/hand_landmarker.task"
  ```

Override parameters at runtime:

```bash
ros2 run hand_landmarks_mediapipe hand_landmarks_node \
  --ros-args \
  -p image_topic:=/my/custom/image/topic \
  -p model_path:=/path/to/custom/model.task
```

 

## Building

```bash
cd /path/to/workspace
colcon build --packages-select hand_landmarks_mediapipe
source install/setup.bash
```

## Dependencies

- ROS 2 (Humble or later)
- OpenCV
- cv_bridge
- MediaPipe (Python)
- NumPy

## License

BSD-3-Clause
