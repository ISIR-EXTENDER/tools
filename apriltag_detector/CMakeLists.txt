cmake_minimum_required(VERSION 3.8)
project(apriltag_detector)

# 1. Set C++ Standard (Required for ROS 2 and Eigen)
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(extender_msgs REQUIRED)
find_package(OpenCV REQUIRED)
find_package(apriltag REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

############ AprilTag Detector Component ############
add_library(apriltag_detector_component SHARED
  src/detector.cpp
)

target_include_directories(apriltag_detector_component PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${EIGEN3_INCLUDE_DIRS}
  ${APRILTAG_INCLUDE_DIRS}
)

ament_target_dependencies(apriltag_detector_component
  rclcpp
  rclcpp_components
  sensor_msgs
  extender_msgs
  cv_bridge
  apriltag
  tf2_ros
)

target_link_libraries(apriltag_detector_component
  ${OpenCV_LIBRARIES}
  apriltag::apriltag  
  Eigen3::Eigen
)

############ AprilTag Bridge Component ############
add_library(apriltag_bridge_component SHARED
  src/bridge.cpp
)

target_include_directories(apriltag_bridge_component PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(apriltag_bridge_component
  rclcpp
  rclcpp_components
  geometry_msgs
  extender_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
)

rclcpp_components_register_node(apriltag_detector_component
  PLUGIN "vision_tools::AprilTagDetector"
  EXECUTABLE apriltag_detector_node)

rclcpp_components_register_node(apriltag_bridge_component
  PLUGIN "vision_tools::AprilTagBridge"
  EXECUTABLE apriltag_bridge_node)

install(TARGETS 
  apriltag_detector_component
  apriltag_bridge_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)


ament_package()