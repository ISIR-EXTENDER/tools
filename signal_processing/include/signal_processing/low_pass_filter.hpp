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
 *  - FirstOrderLowPassFilter: stateful scalar filter object for repeated calls.
 *  - FirstOrderLowPassFilterVector: stateful Eigen::VectorXd filter object.
 *
 * All utilities are ROS-agnostic.
 */

#include <Eigen/Core>

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
  double computeLowPassAlpha(double sample_period, double time_constant);

  /**
   * @brief Apply one step of exponential smoothing without maintaining state.
   *
   * Computes y = α * input + (1 − α) * previous, with α clamped to [0, 1].
   * @param input    Current raw measurement x[n].
   * @param previous Previously filtered output y[n-1].
   * @param alpha    Filter coefficient α ∈ [0, 1].
   * @return Filtered value y[n].
   */
  double exponentialSmoothing(double input, double previous, double alpha);

  /**
   * @brief Apply one step of vector exponential smoothing without maintaining state.
   *
   * @param input    Current raw measurement x[n].
   * @param previous Previously filtered output y[n-1].
   * @param alpha    Filter coefficient α ∈ [0, 1].
   * @return Filtered value y[n].
   */
  Eigen::VectorXd exponentialSmoothing(const Eigen::VectorXd &input,
                                       const Eigen::VectorXd &previous, double alpha);

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
   *   FirstOrderLowPassFilter lpf;
   *   const double alpha = computeLowPassAlpha(0.01, 0.05); // T=10 ms, τ=50 ms
   *   for (const auto & sample : samples) {
   *     const auto smoothed = lpf.filter(sample, alpha);
   *   }
   * @endcode
   */
  class FirstOrderLowPassFilter
  {
  public:
    FirstOrderLowPassFilter() = default;

    /// Reset internal state; the next filter() call will re-initialise.
    void reset();

    /// Return the current internal (filtered) state.
    double state() const;

    /// Return true after the first call to filter() has initialised the state.
    bool initialized() const;

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
    double filter(double input, double alpha);

  private:
    bool initialized_{false};
    double state_ = 0.0;
  };

  /**
   * @brief Stateful first-order low-pass filter for Eigen::VectorXd signals.
   */
  class FirstOrderLowPassFilterVector
  {
  public:
    FirstOrderLowPassFilterVector() = default;

    /// Reset internal state; the next filter() call will re-initialise.
    void reset();

    /// Return the current internal (filtered) state.
    const Eigen::VectorXd &state() const;

    /// Return true after the first call to filter() has initialised the state.
    bool initialized() const;

    /**
     * @brief Filter one vector sample.
     *
     * On the first call the state is set to @p input directly and returned
     * unchanged. Subsequent calls apply exponential smoothing.
     *
     * @param input  New raw sample x[n].
     * @param alpha  Filter coefficient α ∈ [0, 1].
     * @return Filtered value y[n].
     */
    Eigen::VectorXd filter(const Eigen::VectorXd &input, double alpha);

  private:
    bool initialized_{false};
    Eigen::VectorXd state_;
  };

} // namespace signal_processing
