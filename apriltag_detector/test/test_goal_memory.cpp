#include <gtest/gtest.h>

#include "apriltag_detector/goal_memory.hpp"

using vision_tools::GoalMemory;

namespace
{
  geometry_msgs::msg::Pose at(double x)
  {
    geometry_msgs::msg::Pose pose;
    pose.position.x = x;
    pose.orientation.w = 1.0;
    return pose;
  }
} // namespace

TEST(GoalMemory, ListsTagsInIdOrderWhateverTheDetectionOrder)
{
  GoalMemory memory;
  memory.see(7, at(0.7), 0.0);
  memory.see(2, at(0.2), 0.0);
  const auto poses = memory.poses(0.0);
  ASSERT_EQ(poses.size(), 2u);
  EXPECT_DOUBLE_EQ(poses[0].position.x, 0.2);
  EXPECT_DOUBLE_EQ(poses[1].position.x, 0.7);
}

TEST(GoalMemory, KeepsAHiddenTagWithoutTimeout)
{
  GoalMemory memory;
  memory.see(1, at(0.5), 0.0);
  EXPECT_EQ(memory.poses(3600.0).size(), 1u);
}

TEST(GoalMemory, MovesATagSeenAgain)
{
  GoalMemory memory;
  memory.see(1, at(0.5), 0.0);
  memory.see(1, at(0.6), 1.0);
  const auto poses = memory.poses(1.0);
  ASSERT_EQ(poses.size(), 1u);
  EXPECT_DOUBLE_EQ(poses[0].position.x, 0.6);
}

TEST(GoalMemory, ForgetsATagUnseenPastTheTimeout)
{
  GoalMemory memory{5.0};
  memory.see(1, at(0.5), 0.0);
  memory.see(2, at(0.6), 4.0);
  EXPECT_EQ(memory.poses(5.0).size(), 2u);
  const auto poses = memory.poses(6.0);
  ASSERT_EQ(poses.size(), 1u);
  EXPECT_DOUBLE_EQ(poses[0].position.x, 0.6);
}
