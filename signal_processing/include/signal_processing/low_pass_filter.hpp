#pragma once

/**
 * @file low_pass_filter.hpp
 * @brief First-order discrete low-pass filter utilities.
 *
 * Implements exponential smoothing (EMA / IIR first-order low-pass):
 *
 *   y[n] = α * x[n] + (1 - α) * y[n-1]
 *
 * where α = T / (T + τ), T is the sample period and τ is the time constant.
 *
 * Provided helpers:
 *  - computeLowPassAlpha(): convert period+time-constant to an α coefficient.
 *  - exponentialSmoothing(): single-shot stateless application.
 *  - FirstOrderLowPassFilter<T>: stateful filter object for repeated calls.
 *
 * All utilities are header-only and ROS-agnostic.  T must support arithmetic
 * operations compatible with scalar multiplication (e.g. double, Eigen vectors).
 */

#include <type_traits>

#include "signal_processing/saturation.hpp"

namespace signal_processing
{

/**
 * @brief Compute the smoothing coefficient α for a first-order low-pass filter.
 *
 * Uses the bilinear-equivalent formula:
 *   α = T / (T + τ)
 *
 * where T is the sample period and τ is the desired time constant.  The result
 * is clamped to [0, 1].  Returns 1.0 (no filtering) when either argument is
 * non-positive.
 *
 * @param sample_period   Sampling period T (seconds).
 * @param time_constant   Filter time constant τ (seconds).
 * @return α ∈ [0, 1].  Values close to 1 give fast response; close to 0 give heavy smoothing.
 */
inline double computeLowPassAlpha(double sample_period, double time_constant)
{
  if (sample_period <= 0.0 || time_constant <= 0.0)
  {
    return 1.0;
  }

  return clamp(sample_period / (sample_period + time_constant), 0.0, 1.0);
}

/**
 * @brief Apply one step of exponential smoothing without maintaining state.
 *
 * Computes y = α * input + (1 − α) * previous, with α clamped to [0, 1].
 * Works with any type T that supports scalar-weighted addition.
 *
 * @tparam T      Value type (double, Eigen::Vector3d, etc.).
 * @param input    Current raw measurement x[n].
 * @param previous Previously filtered output y[n-1].
 * @param alpha    Filter coefficient α ∈ [0, 1].
 * @return Filtered value y[n].
 */
template <typename T>
inline T exponentialSmoothing(const T & input, const T & previous, double alpha)
{
  const double safe_alpha = clamp(alpha, 0.0, 1.0);
  return static_cast<T>(safe_alpha * input + (1.0 - safe_alpha) * previous);
}

/**
 * @brief Stateful first-order low-pass filter.
 *
 * Maintains internal state across calls so consumers do not need to track
 * the previous filtered value themselves.
 *
 * The first call to filter() initialises the state to the input value
 * (warm-start) to avoid a large transient at startup.  Call reset() to
 * reinitialise before a new signal segment.
 *
 * Example usage:
 * @code
 *   FirstOrderLowPassFilter<Eigen::Vector3d> lpf;
 *   const double alpha = computeLowPassAlpha(0.01, 0.05); // T=10 ms, τ=50 ms
 *   for (const auto & sample : samples) {
 *     const auto smoothed = lpf.filter(sample, alpha);
 *   }
 * @endcode
 *
 * @tparam T  Value type.  Must support arithmetic with double scalars.
 */
template <typename T>
class FirstOrderLowPassFilter
{
public:
  FirstOrderLowPassFilter() = default;

  /// Reset internal state; the next filter() call will re-initialise.
  void reset()
  {
    initialized_ = false;
    state_ = T{};
  }

  /// Return the current internal (filtered) state.
  const T & state() const
  {
    return state_;
  }

  /// Return true after the first call to filter() has initialised the state.
  bool initialized() const
  {
    return initialized_;
  }

  /**
   * @brief Filter one sample.
   *
   * On the first call (not yet initialised) the state is set to @p input
   * directly and returned unchanged.  Subsequent calls apply exponential
   * smoothing with the supplied @p alpha.
   *
   * @param input  New raw sample x[n].
   * @param alpha  Filter coefficient α ∈ [0, 1].
   * @return Filtered value y[n].
   */
  T filter(const T & input, double alpha)
  {
    if (!initialized_)
    {
      state_ = input;
      initialized_ = true;
      return state_;
    }

    state_ = exponentialSmoothing(input, state_, alpha);
    return state_;
  }

private:
  bool initialized_{false};
  T state_{};
};

}  // namespace signal_processing