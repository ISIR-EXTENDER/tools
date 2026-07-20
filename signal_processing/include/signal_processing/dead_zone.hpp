#pragma once

/**
 * @file dead_zone.hpp
 * @brief Scalar and vector dead-zone application helpers.
 *
 * Provides three complementary strategies:
 *  - Hard dead-zone: output is zeroed inside the threshold, unchanged outside.
 *  - Scaled dead-zone (ramp): output linearly ramps from 0 at the dead-zone
 *    boundary to 1 at the saturation boundary, then saturates.
 *  - Norm-based dead-zone: same ramp applied to the Euclidean magnitude of a
 *    multi-dimensional vector, preserving direction.
 *
 * All functions are ROS-agnostic.
 */

#include <Eigen/Core>

namespace signal_processing
{

  /**
   * @brief Hard dead-zone for a scalar.
   *
   * Returns 0 when |value| <= |threshold|, otherwise returns @p value unchanged.
   *
   * @param value      Input signal.
   * @param threshold  Dead-zone radius (absolute value is taken).
   * @return 0 inside the dead-zone, @p value outside.
   */
  double applyDeadZone(double value, double threshold);

  /**
   * @brief Scaled dead-zone with linear ramp for a scalar.
   *
   * Maps input magnitude to output in [0, max_value]:
   *   - 0                           when |value| <= dead_zone
   *   - linear ramp from 0 to max   when dead_zone < |value| < saturation_zone
   *   - max (saturated)             when |value| >= saturation_zone
   *
   * Sign of @p value is preserved in the output.
   * If saturation_zone == dead_zone the ramp collapses to a step at the boundary.
   *
   * @param value           Input signal.
   * @param dead_zone       Inner threshold below which the output is 0.
   * @param saturation_zone Outer input threshold above which the output saturates.
   * @param max_value       Output magnitude at and above @p saturation_zone.
   * @return Scaled and dead-zoned signal in [-|max_value|, |max_value|].
   */
  double applyScaledDeadZone(double value, double dead_zone, double saturation_zone,
                             double max_value = 1.0);

  /**
   * @brief Apply a scaled dead-zone independently to each element of an Eigen vector.
   *
   * Each component is treated as an independent scalar and passed through
   * applyScaledDeadZone() with the same @p dead_zone, @p saturation_zone, and
   * @p max_value.
   *
   * @param values        Input vector.
   * @param dead_zone     Per-component inner threshold.
   * @param saturation_zone  Per-component outer saturation threshold.
   * @param max_value     Per-component output magnitude at saturation.
   * @return Component-wise dead-zoned vector.
   */
  Eigen::VectorXd applyScaledDeadZonePerAxis(const Eigen::VectorXd &values, double dead_zone,
                                             double saturation_zone, double max_value = 1.0);

  /**
   * @brief Compatibility wrapper for applyScaledDeadZonePerAxis().
   */
  Eigen::VectorXd applyScaledDeadZoneVector(const Eigen::VectorXd &values, double dead_zone,
                                            double saturation_zone, double max_value = 1.0);

  /**
   * @brief Return true if the Euclidean norm of @p value is within the dead-zone.
   *
   * Convenience predicate used to short-circuit processing before calling
   * applyNormDeadZone().
   *
   * @param value     Input vector.
   * @param dead_zone Dead-zone radius.
   * @return true when ||value|| <= |dead_zone|.
   */
  bool isInsideNormDeadZone(const Eigen::VectorXd &value, double dead_zone);

  /**
   * @brief Apply a scaled dead-zone to the Euclidean norm of a vector.
   *
   * The magnitude is transformed by applyScaledDeadZone() while the direction
   * is preserved.  Suitable for joystick-style 3-D inputs where a spherical
   * dead-zone is preferred over independent per-axis thresholds.
   *
   * Output magnitude:
   *   - 0                        when ||value|| <= dead_zone
   *   - ramp from 0 to max       when dead_zone < ||value|| < saturation_zone
   *   - max (saturated)          when ||value|| >= saturation_zone
   *
   * @param values            Input vector.
   * @param dead_zone         Spherical dead-zone radius.
   * @param saturation_zone   Spherical saturation radius.
   * @param max_value         Output norm at and above @p saturation_zone.
   * @return Direction-preserving, norm-scaled vector.
   */
  Eigen::VectorXd applyNormDeadZone(const Eigen::VectorXd &values, double dead_zone,
                                    double saturation_zone, double max_value = 1.0);
} // namespace signal_processing
