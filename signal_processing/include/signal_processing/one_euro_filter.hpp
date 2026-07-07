#pragma once

/**
 * @file one_euro_filter.hpp
 * @brief One Euro filter for scalar and 3-D vector signals.
 *
 * The One Euro filter (Casiez et al., CHI 2012) is an adaptive low-pass filter
 * that automatically adjusts its cutoff frequency based on the estimated signal
 * speed.  It reduces lag for fast-moving signals while still smoothing slow
 * noisy ones.
 *
 * Cutoff frequency at each step:
 *   fc = min_cutoff + β * |d̂x/dt|
 *
 * where d̂x/dt is itself a first-order smoothed derivative with cutoff
 * frequency d_cutoff.
 *
 * Tuning guidance:
 *  - Increase @p min_cutoff to reduce lag at the cost of more jitter at rest.
 *  - Increase @p beta to reduce lag during fast motion.
 *  - @p d_cutoff usually needs no tuning (default 1 Hz works well).
 *
 * Two classes are provided:
 *  - OneEuroFilter    – scalar signal, user supplies wall-clock timestamps.
 *  - OneEuroFilter3d  – per-axis independent filtering of Eigen::Vector3d.
 *
 * Both are header-only and ROS-agnostic.
 *
 * Reference: Casiez, G., Roussel, N., & Vogel, D. (2012). 1€ Filter: A simple
 *   speed-based low-pass filter for noisy input in interactive systems.
 *   Proc. ACM CHI 2012.
 */

#include <array>
#include <cmath>

#include <Eigen/Core>

#include "signal_processing/low_pass_filter.hpp"

namespace signal_processing
{

namespace detail
{

/**
 * @brief Compute the EMA smoothing coefficient α from a time step and cutoff frequency.
 *
 * Uses the approximation α = 1 / (1 + τ/dt) where τ = 1 / (2π fc).
 * Returns 1.0 (no smoothing) when either argument is non-positive.
 *
 * @param dt      Time elapsed since the last sample (seconds).
 * @param cutoff  Cutoff frequency fc (Hz).
 * @return α ∈ (0, 1].
 */
inline double smoothingFactor(double dt, double cutoff)
{
  if (dt <= 0.0 || cutoff <= 0.0)
  {
    return 1.0;
  }

  constexpr double pi = 3.14159265358979323846;
  const double tau = 1.0 / (2.0 * pi * cutoff);
  return 1.0 / (1.0 + tau / dt);
}

}  // namespace detail

/**
 * @brief Adaptive scalar One Euro filter.
 *
 * Maintains internal state (last value, last derivative, last timestamp) across
 * calls.  Call reset() to reinitialise before a new signal segment.
 *
 * The first call initialises the state and returns @p value unchanged.
 * Non-monotonic timestamps are handled gracefully: a dt <= 0 is replaced by
 * 1/frequency so the filter does not divide by zero.
 */
class OneEuroFilter
{
public:
  /**
   * @param frequency   Nominal input sampling frequency (Hz). Used only as a
   *                    fallback when consecutive timestamps are non-monotonic.
   * @param min_cutoff  Minimum cutoff frequency (Hz). Controls smoothing at rest.
   * @param beta        Speed coefficient. Higher values reduce lag during motion.
   * @param d_cutoff    Cutoff frequency of the derivative low-pass pre-filter (Hz).
   */
  explicit OneEuroFilter(
    double frequency = 30.0,
    double min_cutoff = 1.0,
    double beta = 0.1,
    double d_cutoff = 1.0)
  : frequency_(std::max(frequency, 1e-3)),
    min_cutoff_(std::max(min_cutoff, 1e-6)),
    beta_(std::max(beta, 0.0)),
    d_cutoff_(std::max(d_cutoff, 1e-6))
  {
  }

  /// Reset internal state; the next filter() call will re-initialise.
  void reset()
  {
    last_value_ = 0.0;
    last_derivative_ = 0.0;
    last_timestamp_ = -1.0;
  }

  /**
   * @brief Filter one scalar sample.
   *
   * @param value          Raw input sample.
   * @param timestamp_sec  Monotonic wall-clock timestamp of this sample (seconds).
   * @return Filtered value.
   */
  double filter(double value, double timestamp_sec)
  {
    if (last_timestamp_ < 0.0)
    {
      // First sample: warm-start the filter state.
      last_value_ = value;
      last_derivative_ = 0.0;
      last_timestamp_ = timestamp_sec;
      return value;
    }

    double dt = timestamp_sec - last_timestamp_;
    if (dt <= 0.0)
    {
      // Non-monotonic timestamp: fall back to nominal period.
      dt = 1.0 / frequency_;
    }

    // Smooth the derivative to estimate signal speed.
    const double derivative = (value - last_value_) / dt;
    const double derivative_alpha = detail::smoothingFactor(dt, d_cutoff_);
    const double filtered_derivative = exponentialSmoothing(derivative, last_derivative_, derivative_alpha);

    // Adapt cutoff frequency based on signal speed.
    const double cutoff = min_cutoff_ + beta_ * std::abs(filtered_derivative);
    const double alpha = detail::smoothingFactor(dt, cutoff);
    const double filtered_value = exponentialSmoothing(value, last_value_, alpha);

    last_value_ = filtered_value;
    last_derivative_ = filtered_derivative;
    last_timestamp_ = timestamp_sec;

    return filtered_value;
  }

private:
  double frequency_;           ///< Nominal sampling frequency (Hz).
  double min_cutoff_;          ///< Minimum low-pass cutoff frequency (Hz).
  double beta_;                ///< Speed coefficient for adaptive cutoff.
  double d_cutoff_;            ///< Cutoff of the derivative pre-filter (Hz).
  double last_value_{0.0};     ///< Filtered value from the previous step.
  double last_derivative_{0.0}; ///< Smoothed derivative from the previous step.
  double last_timestamp_{-1.0}; ///< Timestamp of the previous step (-1 = uninitialised).
};

/**
 * @brief One Euro filter applied independently to each axis of an Eigen::Vector3d.
 *
 * Wraps three scalar OneEuroFilter instances sharing the same parameters.
 * All three axes receive the same timestamp; their filtered outputs are
 * assembled back into a Vector3d.
 *
 * @see OneEuroFilter for parameter descriptions and tuning guidance.
 */
class OneEuroFilter3d
{
public:
  /**
   * @param frequency   Nominal input sampling frequency (Hz).
   * @param min_cutoff  Minimum cutoff frequency (Hz).
   * @param beta        Speed coefficient.
   * @param d_cutoff    Cutoff of the derivative pre-filter (Hz).
   */
  explicit OneEuroFilter3d(
    double frequency = 30.0,
    double min_cutoff = 1.0,
    double beta = 0.1,
    double d_cutoff = 1.0)
  : filters_{
      OneEuroFilter(frequency, min_cutoff, beta, d_cutoff),
      OneEuroFilter(frequency, min_cutoff, beta, d_cutoff),
      OneEuroFilter(frequency, min_cutoff, beta, d_cutoff)}
  {
  }

  /// Reset all three axis filters.
  void reset()
  {
    for (auto & filter : filters_)
    {
      filter.reset();
    }
  }

  /**
   * @brief Filter one Vector3d sample.
   *
   * @param value          Raw 3-D input.
   * @param timestamp_sec  Monotonic wall-clock timestamp (seconds).
   * @return Filtered Vector3d.
   */
  Eigen::Vector3d filter(const Eigen::Vector3d & value, double timestamp_sec)
  {
    return Eigen::Vector3d(
      filters_[0].filter(value.x(), timestamp_sec),
      filters_[1].filter(value.y(), timestamp_sec),
      filters_[2].filter(value.z(), timestamp_sec));
  }

private:
  std::array<OneEuroFilter, 3> filters_; ///< Per-axis scalar filters (x, y, z).
};

}  // namespace signal_processing