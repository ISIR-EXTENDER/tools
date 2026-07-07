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
 * All functions are header-only and ROS-agnostic.
 */

#include <cmath>

#include <Eigen/Core>

#include "signal_processing/saturation.hpp"

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
inline double applyDeadZone(double value, double threshold)
{
  return std::abs(value) <= std::abs(threshold) ? 0.0 : value;
}

/**
 * @brief Scaled dead-zone with linear ramp for a scalar.
 *
 * Maps input magnitude to output in [0, 1]:
 *   - 0                           when |value| <= dead_zone
 *   - linear ramp from 0 to 1     when dead_zone < |value| < saturation_zone
 *   - 1 (saturated)               when |value| >= saturation_zone
 *
 * Sign of @p value is preserved in the output.
 * If saturation_zone == dead_zone the ramp collapses to a step at the boundary.
 *
 * @param value           Input signal.
 * @param dead_zone       Inner threshold below which the output is 0.
 * @param saturation_zone Outer threshold above which the output saturates at ±1.
 * @return Scaled and dead-zoned signal in [-1, 1].
 */
inline double applyScaledDeadZone(double value, double dead_zone, double saturation_zone)
{
  const double magnitude = std::abs(value);
  const double safe_dead_zone = std::abs(dead_zone);
  const double safe_saturation_zone = std::max(std::abs(saturation_zone), safe_dead_zone);

  if (magnitude <= safe_dead_zone)
  {
    return 0.0;
  }

  if (safe_saturation_zone - safe_dead_zone <= 1e-12)
  {
    return value >= 0.0 ? 1.0 : -1.0;
  }

  const double scaled_magnitude = std::clamp(
    (magnitude - safe_dead_zone) / (safe_saturation_zone - safe_dead_zone),
    0.0,
    1.0);

  return std::copysign(scaled_magnitude, value);
}

/**
 * @brief Apply a scaled dead-zone independently to each element of an Eigen vector.
 *
 * Each component is treated as an independent scalar and passed through
 * applyScaledDeadZone() with the same @p dead_zone and @p saturation_zone.
 *
 * @tparam Derived      Eigen expression type.
 * @param value         Input vector.
 * @param dead_zone     Per-component inner threshold.
 * @param saturation_zone  Per-component outer saturation threshold.
 * @return Component-wise dead-zoned vector.
 */
template <typename Derived>
inline typename Derived::PlainObject applyScaledDeadZonePerAxis(
  const Eigen::MatrixBase<Derived> & value,
  double dead_zone,
  double saturation_zone)
{
  typename Derived::PlainObject result = value;
  for (Eigen::Index index = 0; index < value.size(); ++index)
  {
    result(index) = applyScaledDeadZone(value(index), dead_zone, saturation_zone);
  }
  return result;
}

/**
 * @brief Return true if the Euclidean norm of @p value is within the dead-zone.
 *
 * Convenience predicate used to short-circuit processing before calling
 * applyNormDeadZone().
 *
 * @tparam Derived  Eigen expression type.
 * @param value     Input vector.
 * @param dead_zone Dead-zone radius.
 * @return true when ||value|| <= |dead_zone|.
 */
template <typename Derived>
inline bool isInsideNormDeadZone(
  const Eigen::MatrixBase<Derived> & value,
  double dead_zone)
{
  return value.norm() <= std::abs(dead_zone);
}

/**
 * @brief Apply a scaled dead-zone to the Euclidean norm of a vector.
 *
 * The magnitude is transformed by applyScaledDeadZone() while the direction
 * is preserved.  Suitable for joystick-style 3-D inputs where a spherical
 * dead-zone is preferred over independent per-axis thresholds.
 *
 * Output magnitude:
 *   - 0                        when ||value|| <= dead_zone
 *   - ramp from 0 to 1         when dead_zone < ||value|| < saturation_zone
 *   - 1 (saturated direction)  when ||value|| >= saturation_zone
 *
 * @tparam Derived          Eigen expression type.
 * @param value             Input vector.
 * @param dead_zone         Spherical dead-zone radius.
 * @param saturation_zone   Spherical saturation radius.
 * @return Direction-preserving, norm-scaled vector.
 */
template <typename Derived>
inline typename Derived::PlainObject applyNormDeadZone(
  const Eigen::MatrixBase<Derived> & value,
  double dead_zone,
  double saturation_zone)
{
  const double norm = value.norm();
  const double safe_dead_zone = std::abs(dead_zone);
  const double safe_saturation_zone = std::max(std::abs(saturation_zone), safe_dead_zone);

  if (norm <= safe_dead_zone || norm <= 1e-12)
  {
    return Derived::PlainObject::Zero(value.rows(), value.cols());
  }

  const double scaled_norm = applyScaledDeadZone(norm, safe_dead_zone, safe_saturation_zone);
  return (value / norm) * std::abs(scaled_norm);
}

}  // namespace signal_processing