#include <cmath>

#include <gtest/gtest.h>

#include <Eigen/Core>

#include "signal_processing/signal_processing.hpp"

TEST(SaturationTest, ClampAndRateLimitBehaveAsExpected)
{
  EXPECT_DOUBLE_EQ(signal_processing::clamp(3.0, -1.0, 1.0), 1.0);
  EXPECT_DOUBLE_EQ(signal_processing::clamp(-3.0, -1.0, 1.0), -1.0);

  const Eigen::Vector3d current(2.0, -2.0, 0.5);
  const Eigen::Vector3d previous(0.0, 0.0, 0.0);
  const Eigen::Vector3d limited = signal_processing::rateLimitPerAxis(current, previous, 0.75);

  EXPECT_NEAR(limited.x(), 0.75, 1e-12);
  EXPECT_NEAR(limited.y(), -0.75, 1e-12);
  EXPECT_NEAR(limited.z(), 0.5, 1e-12);
}

TEST(SaturationTest, LimitNormScalesVector)
{
  const Eigen::Vector3d input(3.0, 4.0, 0.0);
  const Eigen::Vector3d limited = signal_processing::limitNorm(input, 2.5);

  EXPECT_NEAR(limited.norm(), 2.5, 1e-12);
  EXPECT_NEAR(limited.x(), 1.5, 1e-12);
  EXPECT_NEAR(limited.y(), 2.0, 1e-12);
}

TEST(DeadZoneTest, NormDeadZoneMatchesRampShape)
{
  const Eigen::Vector3d zeroed = signal_processing::applyNormDeadZone(Eigen::Vector3d(0.05, 0.0, 0.0), 0.1, 1.0);
  EXPECT_NEAR(zeroed.norm(), 0.0, 1e-12);

  const Eigen::Vector3d saturated = signal_processing::applyNormDeadZone(Eigen::Vector3d(2.0, 0.0, 0.0), 0.1, 1.0);
  EXPECT_NEAR(saturated.x(), 1.0, 1e-12);
  EXPECT_NEAR(saturated.y(), 0.0, 1e-12);
  EXPECT_NEAR(saturated.z(), 0.0, 1e-12);

  const Eigen::Vector3d ramped = signal_processing::applyNormDeadZone(Eigen::Vector3d(0.55, 0.0, 0.0), 0.1, 1.1);
  EXPECT_NEAR(ramped.x(), 0.45, 1e-12);
}

TEST(LowPassFilterTest, ComputesExpectedAlphaAndState)
{
  EXPECT_NEAR(signal_processing::computeLowPassAlpha(0.1, 0.1), 0.5, 1e-12);

  signal_processing::FirstOrderLowPassFilter<Eigen::Vector3d> filter;
  const Eigen::Vector3d first = filter.filter(Eigen::Vector3d(1.0, 2.0, 3.0), 0.2);
  const Eigen::Vector3d second = filter.filter(Eigen::Vector3d(3.0, 2.0, 1.0), 0.5);

  EXPECT_DOUBLE_EQ(first.x(), 1.0);
  EXPECT_NEAR(second.x(), 2.0, 1e-12);
  EXPECT_NEAR(second.y(), 2.0, 1e-12);
  EXPECT_NEAR(second.z(), 2.0, 1e-12);
}

TEST(OneEuroFilterTest, SmoothesAfterFirstSample)
{
  signal_processing::OneEuroFilter filter(30.0, 1.0, 0.0, 1.0);

  const double first = filter.filter(0.0, 0.0);
  const double second = filter.filter(1.0, 0.1);

  EXPECT_DOUBLE_EQ(first, 0.0);
  EXPECT_GT(second, 0.0);
  EXPECT_LT(second, 1.0);
}

TEST(OneEuroFilterTest, FiltersThreeDimensionsIndependently)
{
  signal_processing::OneEuroFilter3d filter(30.0, 1.0, 0.0, 1.0);

  const Eigen::Vector3d first = filter.filter(Eigen::Vector3d::Zero(), 0.0);
  const Eigen::Vector3d second = filter.filter(Eigen::Vector3d(1.0, -1.0, 2.0), 0.1);

  EXPECT_NEAR(first.norm(), 0.0, 1e-12);
  EXPECT_GT(second.x(), 0.0);
  EXPECT_LT(second.x(), 1.0);
  EXPECT_LT(second.y(), 0.0);
  EXPECT_GT(second.y(), -1.0);
  EXPECT_GT(second.z(), 0.0);
  EXPECT_LT(second.z(), 2.0);
}