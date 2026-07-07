"""Scalar and vector dead-zone application helpers.

Three complementary strategies are provided:

    apply_dead_zone                 – Hard threshold: zero inside, unchanged outside.
    apply_scaled_dead_zone          – Ramp from 0 at the dead-zone to ±1 at saturation.
    apply_scaled_dead_zone_per_axis – Per-component scaled dead-zone for sequences.
    apply_norm_dead_zone            – Norm-based ramp preserving direction of a vector.
"""
from __future__ import annotations

import math
from typing import Iterable

from .saturation import clamp


def apply_dead_zone(value: float, threshold: float) -> float:
    """Apply a hard dead-zone to a scalar.

    Returns 0 when ``|value| <= |threshold|``, otherwise returns *value*
    unchanged.

    Args:
        value:      Input signal.
        threshold:  Dead-zone radius (absolute value is taken).

    Returns:
        0 inside the dead-zone, *value* outside.
    """
    return 0.0 if abs(value) <= abs(threshold) else float(value)


def apply_scaled_dead_zone(value: float, dead_zone: float, saturation_zone: float) -> float:
    """Apply a scaled dead-zone with linear ramp to a scalar.

    Maps input magnitude to output in [0, 1]:

    * 0               when ``|value| <= dead_zone``
    * linear ramp     when ``dead_zone < |value| < saturation_zone``
    * ±1 (saturated)  when ``|value| >= saturation_zone``

    Sign of *value* is preserved in the output.
    If *saturation_zone* == *dead_zone* the ramp collapses to a step.

    Args:
        value:           Input signal.
        dead_zone:       Inner threshold below which the output is 0.
        saturation_zone: Outer threshold above which the output saturates at ±1.

    Returns:
        Scaled signal in [-1, 1].
    """
    magnitude = abs(float(value))
    safe_dead_zone = abs(float(dead_zone))
    safe_saturation_zone = max(abs(float(saturation_zone)), safe_dead_zone)

    if magnitude <= safe_dead_zone:
        return 0.0

    if safe_saturation_zone - safe_dead_zone <= 1e-12:
        return 1.0 if value >= 0.0 else -1.0

    scaled_magnitude = clamp(
        (magnitude - safe_dead_zone) / (safe_saturation_zone - safe_dead_zone),
        0.0,
        1.0,
    )
    return math.copysign(scaled_magnitude, value)


def apply_scaled_dead_zone_per_axis(value: Iterable[float], dead_zone: float, saturation_zone: float) -> tuple[float, ...]:
    """Apply a scaled dead-zone independently to each element of *value*.

    Each component is passed through :func:`apply_scaled_dead_zone` with the
    same *dead_zone* and *saturation_zone*.

    Args:
        value:           Input sequence of floats.
        dead_zone:       Per-component inner threshold.
        saturation_zone: Per-component outer saturation threshold.

    Returns:
        Tuple of component-wise dead-zoned values.
    """
    return tuple(apply_scaled_dead_zone(component, dead_zone, saturation_zone) for component in value)


def apply_norm_dead_zone(value: Iterable[float], dead_zone: float, saturation_zone: float) -> tuple[float, ...]:
    """Apply a scaled dead-zone to the Euclidean norm of a vector.

    The magnitude is transformed by :func:`apply_scaled_dead_zone` while the
    direction is preserved.  Suitable for joystick-style inputs where a
    spherical dead-zone is preferred over independent per-axis thresholds.

    Output magnitude:

    * 0               when ``||value|| <= dead_zone``
    * ramp from 0 to 1 when ``dead_zone < ||value|| < saturation_zone``
    * 1 (saturated)   when ``||value|| >= saturation_zone``

    Args:
        value:           Input vector as a sequence of floats.
        dead_zone:       Spherical dead-zone radius.
        saturation_zone: Spherical saturation radius.

    Returns:
        Direction-preserving, norm-scaled tuple with the same length as *value*.
    """
    vector = tuple(float(component) for component in value)
    norm = math.sqrt(sum(component * component for component in vector))
    safe_dead_zone = abs(float(dead_zone))
    safe_saturation_zone = max(abs(float(saturation_zone)), safe_dead_zone)

    if norm <= safe_dead_zone or norm <= 1e-12:
        return tuple(0.0 for _ in vector)

    scaled_norm = abs(apply_scaled_dead_zone(norm, safe_dead_zone, safe_saturation_zone))
    return tuple((component / norm) * scaled_norm for component in vector)