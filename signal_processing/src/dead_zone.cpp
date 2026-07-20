#include "signal_processing/dead_zone.hpp"

#include <algorithm>
#include <cmath>

namespace signal_processing
{
  double applyDeadZone(double value, double threshold)
  {
    return std::abs(value) <= std::abs(threshold) ? 0.0 : value;
  }

  double applyScaledDeadZone(double value, double dead_zone, double saturation_zone,
                             double max_value)
  {
    const double magnitude = std::abs(value);
    const double safe_dead_zone = std::abs(dead_zone);
    const double safe_saturation_zone = std::max(std::abs(saturation_zone), safe_dead_zone);
    const double safe_max_value = std::abs(max_value);

    if (magnitude <= safe_dead_zone)
    {
      return 0.0;
    }

    if (safe_saturation_zone - safe_dead_zone <= 1e-12)
    {
      return value >= 0.0 ? safe_max_value : -safe_max_value;
    }

    const double scaled_magnitude =
        std::clamp((magnitude - safe_dead_zone) / (safe_saturation_zone - safe_dead_zone), 0.0,
                   1.0) *
        safe_max_value;

    return value >= 0.0 ? scaled_magnitude : -scaled_magnitude;
  }

  Eigen::VectorXd applyScaledDeadZonePerAxis(const Eigen::VectorXd &values, double dead_zone,
                                             double saturation_zone, double max_value)
  {
    Eigen::VectorXd result = values;
    for (Eigen::Index index = 0; index < values.size(); ++index)
    {
      result(index) = applyScaledDeadZone(values(index), dead_zone, saturation_zone, max_value);
    }
    return result;
  }

  Eigen::VectorXd applyScaledDeadZoneVector(const Eigen::VectorXd &values, double dead_zone,
                                            double saturation_zone, double max_value)
  {
    return applyScaledDeadZonePerAxis(values, dead_zone, saturation_zone, max_value);
  }

  bool isInsideNormDeadZone(const Eigen::VectorXd &value, double dead_zone)
  {
    return value.norm() <= std::abs(dead_zone);
  }

  Eigen::VectorXd applyNormDeadZone(const Eigen::VectorXd &values, double dead_zone,
                                    double saturation_zone, double max_value)
  {

    const double norm = values.norm();
    if (norm <= 1e-12)
    {
      return Eigen::VectorXd::Zero(values.size());
    }

    const double scaled_norm = applyScaledDeadZone(norm, dead_zone, saturation_zone, max_value);
    return values * (scaled_norm / norm);
  }
} // namespace signal_processing
