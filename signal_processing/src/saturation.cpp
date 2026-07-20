#include "signal_processing/saturation.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace signal_processing
{
  namespace
  {
    void requireSameSize(const Eigen::VectorXd &first, const Eigen::VectorXd &second,
                         const char *function_name)
    {
      if (first.size() != second.size())
      {
        throw std::invalid_argument(std::string(function_name) +
                                    " requires vectors with the same size");
      }
    }
  } // namespace

  double clampSymmetric(double value, double limit)
  {
    const double magnitude = std::abs(limit);
    return std::clamp(value, -magnitude, magnitude);
  }

  Eigen::VectorXd clampSymmetric(const Eigen::VectorXd &value, double limit)
  {
    const double magnitude = std::abs(limit);
    return value.cwiseMax(-magnitude).cwiseMin(magnitude);
  }

  Eigen::VectorXd clampSymmetric(const Eigen::VectorXd &value, const Eigen::VectorXd &limit)
  {
    requireSameSize(value, limit, "clampSymmetric");

    const Eigen::VectorXd magnitude = limit.cwiseAbs();
    return value.cwiseMax(-magnitude).cwiseMin(magnitude);
  }

  Eigen::VectorXd rateLimitPerAxis(const Eigen::VectorXd &current, const Eigen::VectorXd &previous,
                                   const Eigen::VectorXd &max_delta)
  {
    requireSameSize(current, previous, "rateLimitPerAxis");
    requireSameSize(current, max_delta, "rateLimitPerAxis");

    const Eigen::VectorXd safe_max_delta = max_delta.cwiseAbs();
    return previous + (current - previous).cwiseMax(-safe_max_delta).cwiseMin(safe_max_delta);
  }

  Eigen::VectorXd rateLimitPerAxis(const Eigen::VectorXd &current, const Eigen::VectorXd &previous,
                                   double max_delta)
  {
    requireSameSize(current, previous, "rateLimitPerAxis");

    const Eigen::VectorXd per_axis = Eigen::VectorXd::Constant(current.size(), std::abs(max_delta));
    return rateLimitPerAxis(current, previous, per_axis);
  }

  Eigen::VectorXd limitNorm(const Eigen::VectorXd &value, double max_norm)
  {
    const double safe_max_norm = std::abs(max_norm);
    if (safe_max_norm <= 0.0)
    {
      return Eigen::VectorXd::Zero(value.size());
    }

    const double current_norm = value.norm();
    if (current_norm <= safe_max_norm || current_norm <= 1e-12)
    {
      return value;
    }

    return value * (safe_max_norm / current_norm);
  }

} // namespace signal_processing
