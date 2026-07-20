#include "signal_processing/one_euro_filter.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>

#include "signal_processing/low_pass_filter.hpp"

namespace signal_processing
{
  namespace
  {
    double smoothingFactor(double dt, double cutoff)
    {
      if (dt <= 0.0 || cutoff <= 0.0)
      {
        return 1.0;
      }

      const double tau = 1.0 / (2.0 * M_PI * cutoff);
      return 1.0 / (1.0 + tau / dt);
    }
  } // namespace

  OneEuroFilter::OneEuroFilter(double frequency, double min_cutoff, double beta, double d_cutoff)
      : frequency_(std::max(frequency, 1e-3)), min_cutoff_(std::max(min_cutoff, 1e-6)),
        beta_(std::max(beta, 0.0)), d_cutoff_(std::max(d_cutoff, 1e-6))
  {
  }

  void OneEuroFilter::reset()
  {
    last_value_ = 0.0;
    last_derivative_ = 0.0;
    last_timestamp_ = -1.0;
  }

  double OneEuroFilter::filter(double value, double timestamp_sec)
  {
    if (last_timestamp_ < 0.0)
    {
      last_value_ = value;
      last_derivative_ = 0.0;
      last_timestamp_ = timestamp_sec;
      return value;
    }

    double dt = timestamp_sec - last_timestamp_;
    if (dt <= 0.0)
    {
      dt = 1.0 / frequency_;
    }

    const double derivative = (value - last_value_) / dt;
    const double derivative_alpha = smoothingFactor(dt, d_cutoff_);
    const double filtered_derivative =
        exponentialSmoothing(derivative, last_derivative_, derivative_alpha);

    const double cutoff = min_cutoff_ + beta_ * std::abs(filtered_derivative);
    const double alpha = smoothingFactor(dt, cutoff);
    const double filtered_value = exponentialSmoothing(value, last_value_, alpha);

    last_value_ = filtered_value;
    last_derivative_ = filtered_derivative;
    last_timestamp_ = timestamp_sec;

    return filtered_value;
  }

  OneEuroFilterVector::OneEuroFilterVector(Eigen::Index size, double frequency, double min_cutoff,
                                           double beta, double d_cutoff)
  {
    if (size < 0)
    {
      throw std::invalid_argument("OneEuroFilterVector size must be non-negative");
    }

    filters_.reserve(static_cast<std::size_t>(size));
    for (Eigen::Index index = 0; index < size; ++index)
    {
      filters_.emplace_back(frequency, min_cutoff, beta, d_cutoff);
    }
  }

  void OneEuroFilterVector::reset()
  {
    for (auto &filter : filters_)
    {
      filter.reset();
    }
  }

  Eigen::VectorXd OneEuroFilterVector::filter(const Eigen::VectorXd &value, double timestamp_sec)
  {
    if (static_cast<std::size_t>(value.size()) != filters_.size())
    {
      throw std::invalid_argument("OneEuroFilterVector input size does not match filter size");
    }

    Eigen::VectorXd filtered(value.size());
    for (Eigen::Index index = 0; index < value.size(); ++index)
    {
      filtered(index) =
          filters_[static_cast<std::size_t>(index)].filter(value(index), timestamp_sec);
    }
    return filtered;
  }

} // namespace signal_processing
