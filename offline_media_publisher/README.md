# offline_media_publisher

ROS 2 package for publishing images or video frames as simulated camera streams for testing and offline processing.

## Overview

This package provides two publisher nodes that simulate camera streams by publishing pre-recorded images or video frames to `/camera/color/image_raw`. Useful for testing vision pipelines without live camera hardware.

## Nodes

### image_publisher

Publishes static images from a folder in a cyclic pattern.

**Parameters:**
- `folder_path` (string, **required**) - Path to folder containing images
- `fps` (int, default: 100) - Publishing rate in Hz
- `image_extensions` (string, default: `.jpg,.jpeg,.png,.bmp,.tiff,.tif`) - Comma-separated list of extensions to include

**Usage with launch file:**
```bash
ros2 launch offline_media_publisher image_publisher_launch.py folder_path:=/path/to/images fps:=100
```

Edit `config/image_publisher.yaml` to set `folder_path` before launching, or override at runtime:
```bash
ros2 run offline_media_publisher image_publisher \
  --ros-args \
  -p folder_path:=/path/to/images \
  -p fps:=100 \
  -p image_extensions:='.jpg,.jpeg,.png,.bmp,.tiff,.tif'
```

**Image selection:** Scans for files matching the configured extensions and cycles through them sequentially.

### video_publisher

Publishes frames from video files sequentially with fixed frame rate.

**Parameters:**
- `folder_path` (string, **required**) - Path to folder containing videos
- `fps` (int, default: 50) - Publishing rate in Hz (overrides native video FPS)
- `video_extensions` (string, default: `.mp4,.avi,.mov,.mkv,.m4v,.webm`) - Comma-separated list of extensions to include

**Usage with launch file:**
```bash
ros2 launch offline_media_publisher video_publisher_launch.py folder_path:=/path/to/videos fps:=50
```

Edit `config/video_publisher.yaml` to set `folder_path` before launching, or override at runtime:
```bash
ros2 run offline_media_publisher video_publisher \
  --ros-args \
  -p folder_path:=/path/to/videos \
  -p fps:=50 \
  -p video_extensions:='.mp4,.avi,.mov,.mkv,.m4v,.webm'
```

**Video selection:** Scans for files matching the configured extensions and plays them sequentially. Automatically loops back to first video when all have been played.

## Published Topics

Both nodes publish to:
- `/camera/color/image_raw` (`sensor_msgs/Image`) - BGR8 encoded camera images

## Building

```bash
cd /path/to/workspace
colcon build --packages-select offline_media_publisher
source install/setup.bash
```

## Dependencies

- ROS 2 (Humble or later)
- Python 3
- OpenCV
- cv_bridge

## License

BSD-3-Clause
