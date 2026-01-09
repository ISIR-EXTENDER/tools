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
find_package(cv_bridge REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(extender_msgs REQUIRED)
find_package(OpenCV REQUIRED)
find_package(apriltag REQUIRED)
find_package(Eigen3 REQUIRED)

add_executable(apriltag_detector
  src/detector.cpp
)

ament_target_dependencies(apriltag_detector
  rclcpp
  sensor_msgs
  extender_msgs
  cv_bridge
)

target_include_directories(apriltag_detector PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

target_link_libraries(apriltag_detector
  ${OpenCV_LIBRARIES}
  apriltag::apriltag   
  Eigen3::Eigen
)

install(TARGETS apriltag_detector
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)


ament_package()