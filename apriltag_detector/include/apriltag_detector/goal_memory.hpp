#pragma once

#include <map>
#include <vector>

#include "geometry_msgs/msg/pose.hpp"

namespace vision_tools
{
  // Last known pose of each tag, so a tag hidden by the gripper on approach stays a goal.
  class GoalMemory
  {
  public:
    explicit GoalMemory(double timeout_sec = 0.0) : timeout_sec_(timeout_sec)
    {
    }

    void see(int id, const geometry_msgs::msg::Pose &pose, double now_sec)
    {
      goals_[id] = {pose, now_sec};
    }

    // Poses in tag id order; with a positive timeout, tags unseen for longer are forgotten.
    std::vector<geometry_msgs::msg::Pose> poses(double now_sec)
    {
      std::vector<geometry_msgs::msg::Pose> poses;
      for (auto it = goals_.begin(); it != goals_.end();)
      {
        if (timeout_sec_ > 0.0 && now_sec - it->second.seen_sec > timeout_sec_)
        {
          it = goals_.erase(it);
          continue;
        }
        poses.push_back(it->second.pose);
        ++it;
      }
      return poses;
    }

  private:
    struct Seen
    {
      geometry_msgs::msg::Pose pose;
      double seen_sec;
    };

    double timeout_sec_;
    std::map<int, Seen> goals_;
  };
} // namespace vision_tools
