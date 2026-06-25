#pragma once

/**
 * @file saturation.hpp
 * @brief Scalar and vector saturation/clamping helpers.
 *
 * Provides compile-time-generic utilities for:
 *  - Scalar clamping to a [lower, upper] interval.
 *  - Component-wise symmetric clamping of Eigen vectors/matrices.
 *  - Per-axis rate limiting (delta clamping between successive samples).
 *  - Norm-based magnitude limiting for multi-dimensional vectors.
 *
 * All functions are header-only, ROS-agnostic, and free of dynamic allocation.
 */

#include <algorithm>
#include <cmath>

#include <Eigen/Core>

namespace signal_processing
{

/**
 * @brief Clamp a scalar @p value to the closed interval [@p lower, @p upper].
 *
 * If @p lower > @p upper they are swapped before clamping, so the call is
 * safe regardless of argument order.
 *
 * @tparam Scalar Any arithmetic type that supports std::max / std::min.
 * @param value  Value to clamp.
 * @param lower  Lower bound (inclusive).
 * @param upper  Upper bound (inclusive).
 * @return Clamped value in [lower, upper].
 */
template <typename Scalar>
inline Scalar clamp(Scalar value, Scalar lower, Scalar upper)
{
  if (lower > upper)
  {
    std::swap(lower, upper);
  }
  return std::max(lower, std::min(value, upper));
}

/**
 * @brief Clamp each element of an Eigen matrix to [-|limit|, +|limit|].
 *
 * Applies the same scalar symmetric bound to every component.
 *
 * @tparam Derived  Eigen matrix expression type.
 * @param value  Input matrix.
 * @param limit  Symmetric bound (absolute value is taken).
 * @return Component-wise clamped matrix of the same type.
 */
template <typename Derived>
inline typename Derived::PlainObject clampSymmetric(
  const Eigen::MatrixBase<Derived> & value,
  double limit)
{
  const double magnitude = std::abs(limit);
  const auto lower = Derived::PlainObject::Constant(value.rows(), value.cols(), -magnitude);
  const auto upper = Derived::PlainObject::Constant(value.rows(), value.cols(), magnitude);
  return value.cwiseMax(lower).cwiseMin(upper);
}

/**
 * @brief Clamp each element of @p value to ±|limit_i| using a per-element limit vector.
 *
 * @tparam DerivedValue  Eigen expression type of the value to clamp.
 * @tparam DerivedLimit  Eigen expression type of the per-element limit.
 * @param value  Input matrix.
 * @param limit  Per-element symmetric bound (absolute values are taken).
 * @return Component-wise clamped matrix.
 */
template <typename DerivedValue, typename DerivedLimit>
inline typename DerivedValue::PlainObject clampSymmetric(
  const Eigen::MatrixBase<DerivedValue> & value,
  const Eigen::MatrixBase<DerivedLimit> & limit)
{
  const auto magnitude = limit.cwiseAbs();
  return value.cwiseMax(-magnitude).cwiseMin(magnitude);
}

/**
 * @brief Limit the per-axis change from @p previous to @p current by @p max_delta.
 *
 * Each component of the output satisfies:
 *   |output_i - previous_i| <= |max_delta_i|
 *
 * Useful for smoothing step commands without a proper filter when a hard
 * slew-rate limit is preferable.
 *
 * @tparam DerivedCurrent   Eigen expression type of the new sample.
 * @tparam DerivedPrevious  Eigen expression type of the previous sample.
 * @tparam DerivedDelta     Eigen expression type of the per-axis max delta.
 * @param current    New (potentially large) command vector.
 * @param previous   Previous output vector.
 * @param max_delta  Per-axis maximum allowed change per step.
 * @return Rate-limited output vector.
 */
template <typename DerivedCurrent, typename DerivedPrevious, typename DerivedDelta>
inline typename DerivedCurrent::PlainObject rateLimitPerAxis(
  const Eigen::MatrixBase<DerivedCurrent> & current,
  const Eigen::MatrixBase<DerivedPrevious> & previous,
  const Eigen::MatrixBase<DerivedDelta> & max_delta)
{
  return previous + (current - previous).cwiseMax(-max_delta.cwiseAbs()).cwiseMin(max_delta.cwiseAbs());
}

/**
 * @brief Rate-limit overload with a single scalar @p max_delta applied uniformly to all axes.
 *
 * @tparam Derived  Eigen expression type.
 * @param current    New command vector.
 * @param previous   Previous output vector.
 * @param max_delta  Scalar maximum allowed change per step applied to every axis.
 * @return Rate-limited output vector.
 */
template <typename Derived>
inline typename Derived::PlainObject rateLimitPerAxis(
  const Eigen::MatrixBase<Derived> & current,
  const Eigen::MatrixBase<Derived> & previous,
  double max_delta)
{
  const auto per_axis = Derived::PlainObject::Constant(current.rows(), current.cols(), std::abs(max_delta));
  return rateLimitPerAxis(current, previous, per_axis);
}

/**
 * @brief Scale @p value so that its Euclidean norm does not exceed @p max_norm.
 *
 * Direction is preserved.  If the norm is already within the limit, or if
 * @p max_norm <= 0, the vector is returned unchanged (or zeroed, respectively).
 *
 * @tparam Derived  Eigen expression type.
 * @param value     Input vector.
 * @param max_norm  Maximum allowed Euclidean norm (must be > 0 to have effect).
 * @return Norm-limited vector with the same direction as @p value.
 */
template <typename Derived>
inline typename Derived::PlainObject limitNorm(
  const Eigen::MatrixBase<Derived> & value,
  double max_norm)
{
  const double safe_max_norm = std::abs(max_norm);
  if (safe_max_norm <= 0.0)
  {
    return Derived::PlainObject::Zero(value.rows(), value.cols());
  }

  const double current_norm = value.norm();
  if (current_norm <= safe_max_norm || current_norm <= 1e-12)
  {
    return value;
  }

  return value * (safe_max_norm / current_norm);
}

}  // namespace signal_processing