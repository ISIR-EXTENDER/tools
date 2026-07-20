#pragma once

/**
 * @file saturation.hpp
 * @brief Scalar and vector saturation/clamping helpers.
 *
 * Provides utilities for:
 *  - Scalar symmetric clamping.
 *  - Component-wise symmetric clamping of Eigen vectors.
 *  - Per-axis rate limiting (delta clamping between successive samples).
 *  - Norm-based magnitude limiting for multi-dimensional vectors.
 *
 * All functions are ROS-agnostic.
 */

#include <Eigen/Core>

namespace signal_processing
{

  /**
   * @brief Clamp a scalar to [-|limit|, +|limit|].
   *
   * @param value  Input scalar.
   * @param limit  Symmetric bound (absolute value is taken).
   * @return Clamped scalar.
   */
  double clampSymmetric(double value, double limit);

  /**
   * @brief Clamp each element of an Eigen vector to [-|limit|, +|limit|].
   *
   * Applies the same scalar symmetric bound to every component.
   *
   * @param value  Input vector.
   * @param limit  Symmetric bound (absolute value is taken).
   * @return Component-wise clamped vector.
   */
  Eigen::VectorXd clampSymmetric(const Eigen::VectorXd &value, double limit);

  /**
   * @brief Clamp each element of @p value to ±|limit_i| using a per-element limit vector.
   *
   * @param value  Input vector.
   * @param limit  Per-element symmetric bound (absolute values are taken).
   * @return Component-wise clamped vector.
   */
  Eigen::VectorXd clampSymmetric(const Eigen::VectorXd &value, const Eigen::VectorXd &limit);

  /**
   * @brief Limit the per-axis change from @p previous to @p current by @p max_delta.
   *
   * Each component of the output satisfies:
   *   |output_i - previous_i| <= |max_delta_i|
   *
   * Useful for smoothing step commands without a proper filter when a hard
   * slew-rate limit is preferable.
   *
   * @param current    New (potentially large) command vector.
   * @param previous   Previous output vector.
   * @param max_delta  Per-axis maximum allowed change per step.
   * @return Rate-limited output vector.
   */
  Eigen::VectorXd rateLimitPerAxis(const Eigen::VectorXd &current, const Eigen::VectorXd &previous,
                                   const Eigen::VectorXd &max_delta);

  /**
   * @brief Rate-limit overload with a single scalar @p max_delta applied uniformly to all axes.
   *
   * @param current    New command vector.
   * @param previous   Previous output vector.
   * @param max_delta  Scalar maximum allowed change per step applied to every axis.
   * @return Rate-limited output vector.
   */
  Eigen::VectorXd rateLimitPerAxis(const Eigen::VectorXd &current, const Eigen::VectorXd &previous,
                                   double max_delta);

  /**
   * @brief Scale @p value so that its Euclidean norm does not exceed @p max_norm.
   *
   * Direction is preserved.  If the norm is already within the limit, or if
   * @p max_norm <= 0, the vector is returned unchanged (or zeroed, respectively).
   *
   * @param value     Input vector.
   * @param max_norm  Maximum allowed Euclidean norm (must be > 0 to have effect).
   * @return Norm-limited vector with the same direction as @p value.
   */
  Eigen::VectorXd limitNorm(const Eigen::VectorXd &value, double max_norm);

} // namespace signal_processing
