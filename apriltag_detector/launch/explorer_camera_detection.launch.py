import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Get the package share directory
    pkg_share = get_package_share_directory('apriltag_detector')

    # Config file path
    apriltag_config_file = os.path.join(pkg_share, 'config', 'tags_params.yaml')
    usb_cam_file = 'file://' + os.path.join(pkg_share, 'config', 'explorer_camera_calib.yaml')
    # USB Cam node
    usb_cam_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='explorer_camera',
        parameters=[
            {'camera_name': 'explorer_camera'},
            {'video_device': '/dev/video4'},
            {'camera_info_url': usb_cam_file}
        ]
    )

    # AprilTag Detector node
    apriltag_detector_node = Node(
        package='apriltag_detector',
        executable='apriltag_detector',
        name='apriltag_detector',
        parameters=[apriltag_config_file]
    )

    return LaunchDescription([
        usb_cam_node,
        apriltag_detector_node
    ])