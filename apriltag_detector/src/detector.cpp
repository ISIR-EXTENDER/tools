#include "apriltag_detector/detector.hpp"

namespace vision_tools
{
  AprilTagDetector::AprilTagDetector(const rclcpp::NodeOptions &options)
      : Node("apriltag_detector", options)
  {
    tf_ = tag36h11_create();
    td_ = apriltag_detector_create();
    apriltag_detector_add_family(td_, tf_);

    camera_info_sub_ = this->create_subscription<sensor_msgs::msg::CameraInfo>(
        "/camera_info", 10,
        std::bind(&AprilTagDetector::cameraInfoCallback, this, std::placeholders::_1));
    image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
        "/image_raw", 10, std::bind(&AprilTagDetector::imageCallback, this, std::placeholders::_1));

    this->get_parameter("tag_publisher_topic", tag_publisher_topic_);
    tag_publisher_ =
        this->create_publisher<extender_msgs::msg::AprilTagPoseArray>(tag_publisher_topic_, 10);

    this->get_parameter("max_hamming_distance", max_hamming_distance_);
    std::string prefix = "tag_sizes";
    auto list_result = this->list_parameters({prefix}, 10);

    for (const auto &name : list_result.names)
    {
      std::string id_str = name.substr(prefix.length() + 1);

      double size_value;
      if (this->get_parameter(name, size_value))
      {
        int tag_id = std::stoi(id_str);
        tag_sizes_[tag_id] = size_value;

        RCLCPP_INFO(this->get_logger(), "Loaded Tag ID: %d, Size: %f meters", tag_id, size_value);
      }
    }
  }

  AprilTagDetector::~AprilTagDetector()
  {
    apriltag_detector_destroy(td_);
    tag36h11_destroy(tf_);
  }

  void AprilTagDetector::cameraInfoCallback(const sensor_msgs::msg::CameraInfo::SharedPtr msg)
  {
    // Extract intrinsics from the K matrix (3x3 row-major)
    // K = [fx 0 cx; 0 fy cy; 0 0 1]
    fx_ = msg->k[0];
    cx_ = msg->k[2];
    fy_ = msg->k[4];
    cy_ = msg->k[5];

    has_camera_info_ = true;

    RCLCPP_INFO(this->get_logger(), "Camera info received. Intrinsics: fx=%f, fy=%f, cx=%f, cy=%f",
                fx_, fy_, cx_, cy_);

    info.fx = fx_;
    info.fy = fy_;
    info.cx = cx_;
    info.cy = cy_;

    camera_info_sub_.reset();
  }

  void AprilTagDetector::imageCallback(const sensor_msgs::msg::Image::SharedPtr msg)
  {
    current_frame_ = cv_bridge::toCvShare(msg, "mono8")->image;
    image_u8_t current_frame_apriltag_ = {
        current_frame_.cols,
        current_frame_.rows,
        current_frame_.cols,
        current_frame_.data,
    };

    detections_ = apriltag_detector_detect(td_, &current_frame_apriltag_);

    extender_msgs::msg::AprilTagPoseArray detection_array_msg;
    double err;
    for (int i = 0; i < zarray_size(detections_); i++)
    {
      zarray_get(detections_, i, &det);
      if (det->hamming > max_hamming_distance_)
        continue;

      info.det = det;
      info.tagsize = tag_sizes_[det->id];

      apriltag_pose_t pose;
      err = estimate_tag_pose(&info, &pose);

      Eigen::Map<Eigen::Vector3d> translation(pose.t->data);
      Eigen::Map<Eigen::Matrix<double, 3, 3, Eigen::RowMajor>> rotation(pose.R->data);
      Eigen::Quaterniond q(rotation);

      extender_msgs::msg::AprilTagPose detection_msg;
      detection_msg.id = det->id;
      detection_msg.tag_pose.position.x = translation.x();
      detection_msg.tag_pose.position.y = translation.y();
      detection_msg.tag_pose.position.z = translation.z();

      detection_msg.tag_pose.orientation.x = q.x();
      detection_msg.tag_pose.orientation.y = q.y();
      detection_msg.tag_pose.orientation.z = q.z();
      detection_msg.tag_pose.orientation.w = q.w();

      detection_array_msg.detected_tags.push_back(detection_msg);
      matd_destroy(pose.R);
      matd_destroy(pose.t);
    }
    apriltag_detections_destroy(detections_);
    tag_publisher_->publish(detection_array_msg);
  }

} // namespace vision_tools

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  // This is the magic part that allows reading the YAML automatically
  auto node_options = rclcpp::NodeOptions()
                          .allow_undeclared_parameters(true)
                          .automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<vision_tools::AprilTagDetector>(node_options);
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}