#pragma once

/**
 * @file one_euro_filter.hpp
 * @brief One Euro filter for scalar and vector signals.
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
 *  - OneEuroFilter        – scalar signal, user supplies wall-clock timestamps.
 *  - OneEuroFilterVector  – per-axis independent filtering of Eigen::VectorXd.
 *
 * Both are ROS-agnostic.
 *
 * Reference: Casiez, G., Roussel, N., & Vogel, D. (2012). 1€ Filter: A simple
 *   speed-based low-pass filter for noisy input in interactive systems.
 *   Proc. ACM CHI 2012.
 * Algorithm overview and tuning examples: https://gery.casiez.net/1euro/
 */

#include <vector>

#include <Eigen/Core>

namespace signal_processing
{

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
    explicit OneEuroFilter(double frequency = 30.0, double min_cutoff = 1.0, double beta = 0.1,
                           double d_cutoff = 1.0);

    /// Reset internal state; the next filter() call will re-initialise.
    void reset();

    /**
     * @brief Filter one scalar sample.
     *
     * @param value          Raw input sample.
     * @param timestamp_sec  Monotonic wall-clock timestamp of this sample (seconds).
     * @return Filtered value.
     */
    double filter(double value, double timestamp_sec);

  private:
    double frequency_;            ///< Nominal sampling frequency (Hz).
    double min_cutoff_;           ///< Minimum low-pass cutoff frequency (Hz).
    double beta_;                 ///< Speed coefficient for adaptive cutoff.
    double d_cutoff_;             ///< Cutoff of the derivative pre-filter (Hz).
    double last_value_{0.0};      ///< Filtered value from the previous step.
    double last_derivative_{0.0}; ///< Smoothed derivative from the previous step.
    double last_timestamp_{-1.0}; ///< Timestamp of the previous step (-1 = uninitialised).
  };

  /**
   * @brief One Euro filter applied independently to each axis of an Eigen::VectorXd.
   *
   * Wraps scalar OneEuroFilter instances sharing the same parameters. All axes
   * receive the same timestamp; their filtered outputs are assembled back into a
   * VectorXd.
   *
   * @see OneEuroFilter for parameter descriptions and tuning guidance.
   */
  class OneEuroFilterVector
  {
  public:
    /**
     * @param size        Number of vector axes to filter.
     * @param frequency   Nominal input sampling frequency (Hz).
     * @param min_cutoff  Minimum cutoff frequency (Hz).
     * @param beta        Speed coefficient.
     * @param d_cutoff    Cutoff of the derivative pre-filter (Hz).
     */
    explicit OneEuroFilterVector(Eigen::Index size, double frequency = 30.0,
                                 double min_cutoff = 1.0, double beta = 0.1, double d_cutoff = 1.0);

    /// Reset all axis filters.
    void reset();

    /**
     * @brief Filter one vector sample.
     *
     * @param value          Raw vector input.
     * @param timestamp_sec  Monotonic wall-clock timestamp (seconds).
     * @return Filtered VectorXd.
     */
    Eigen::VectorXd filter(const Eigen::VectorXd &value, double timestamp_sec);

  private:
    std::vector<OneEuroFilter> filters_; ///< Per-axis scalar filters.
  };

} // namespace signal_processing
