#include "signal_processing/low_pass_filter.hpp"

#include <algorithm>
#include <stdexcept>

namespace signal_processing
{

  double computeLowPassAlpha(double sample_period, double time_constant)
  {
    if (sample_period <= 0.0 || time_constant <= 0.0)
    {
      return 1.0;
    }

    return std::clamp(sample_period / (sample_period + time_constant), 0.0, 1.0);
  }

  double exponentialSmoothing(double input, double previous, double alpha)
  {
    const double safe_alpha = std::clamp(alpha, 0.0, 1.0);
    return safe_alpha * input + (1.0 - safe_alpha) * previous;
  }

  Eigen::VectorXd exponentialSmoothing(const Eigen::VectorXd &input,
                                       const Eigen::VectorXd &previous, double alpha)
  {
    if (input.size() != previous.size())
    {
      throw std::invalid_argument("exponentialSmoothing requires vectors with the same size");
    }

    const double safe_alpha = std::clamp(alpha, 0.0, 1.0);
    return safe_alpha * input + (1.0 - safe_alpha) * previous;
  }

  void FirstOrderLowPassFilter::reset()
  {
    initialized_ = false;
    state_ = 0.0;
  }

  double FirstOrderLowPassFilter::state() const
  {
    return state_;
  }

  bool FirstOrderLowPassFilter::initialized() const
  {
    return initialized_;
  }

  double FirstOrderLowPassFilter::filter(double input, double alpha)
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

  void FirstOrderLowPassFilterVector::reset()
  {
    initialized_ = false;
    state_.resize(0);
  }

  const Eigen::VectorXd &FirstOrderLowPassFilterVector::state() const
  {
    return state_;
  }

  bool FirstOrderLowPassFilterVector::initialized() const
  {
    return initialized_;
  }

  Eigen::VectorXd FirstOrderLowPassFilterVector::filter(const Eigen::VectorXd &input, double alpha)
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

} // namespace signal_processing
