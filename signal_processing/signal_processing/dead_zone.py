"""Scalar and vector dead-zone application helpers.

Three complementary strategies are provided:

    apply_dead_zone                 – Hard threshold: zero inside, unchanged outside.
    apply_scaled_dead_zone          – Ramp from 0 at the dead-zone to ±max at saturation.
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


def apply_scaled_dead_zone(
    value: float,
    dead_zone: float,
    saturation_zone: float,
    max_value: float = 1.0,
) -> float:
    """Apply a scaled dead-zone with linear ramp to a scalar.

    Maps input magnitude to output in [0, max_value]:

    * 0               when ``|value| <= dead_zone``
    * linear ramp     when ``dead_zone < |value| < saturation_zone``
    * ±max (saturated)  when ``|value| >= saturation_zone``

    Sign of *value* is preserved in the output.
    If *saturation_zone* == *dead_zone* the ramp collapses to a step.

    Args:
        value:           Input signal.
        dead_zone:       Inner threshold below which the output is 0.
        saturation_zone: Outer input threshold above which the output saturates.
        max_value:       Output magnitude at and above *saturation_zone*.

    Returns:
        Scaled signal in [-|max_value|, |max_value|].
    """
    magnitude = abs(float(value))
    safe_dead_zone = abs(float(dead_zone))
    safe_saturation_zone = max(abs(float(saturation_zone)), safe_dead_zone)
    safe_max_value = abs(float(max_value))

    if magnitude <= safe_dead_zone:
        return 0.0

    if safe_saturation_zone - safe_dead_zone <= 1e-12:
        return safe_max_value if value >= 0.0 else -safe_max_value

    scaled_magnitude = clamp(
        (magnitude - safe_dead_zone) / (safe_saturation_zone - safe_dead_zone),
        0.0,
        1.0,
    ) * safe_max_value
    return math.copysign(scaled_magnitude, value)


def apply_scaled_dead_zone_per_axis(
    value: Iterable[float],
    dead_zone: float,
    saturation_zone: float,
    max_value: float = 1.0,
) -> tuple[float, ...]:
    """Apply a scaled dead-zone independently to each element of *value*.

    Each component is passed through :func:`apply_scaled_dead_zone` with the
    same *dead_zone*, *saturation_zone*, and *max_value*.

    Args:
        value:           Input sequence of floats.
        dead_zone:       Per-component inner threshold.
        saturation_zone: Per-component outer saturation threshold.
        max_value:       Per-component output magnitude at saturation.

    Returns:
        Tuple of component-wise dead-zoned values.
    """
    return tuple(
        apply_scaled_dead_zone(component, dead_zone, saturation_zone, max_value)
        for component in value
    )


def apply_norm_dead_zone(
    value: Iterable[float],
    dead_zone: float,
    saturation_zone: float,
    max_value: float = 1.0,
) -> tuple[float, ...]:
    """Apply a scaled dead-zone to the Euclidean norm of a vector.

    The magnitude is transformed by :func:`apply_scaled_dead_zone` while the
    direction is preserved.  Suitable for joystick-style inputs where a
    spherical dead-zone is preferred over independent per-axis thresholds.

    Output magnitude:

    * 0                  when ``||value|| <= dead_zone``
    * ramp from 0 to max when ``dead_zone < ||value|| < saturation_zone``
    * max (saturated)    when ``||value|| >= saturation_zone``

    Args:
        value:           Input vector as a sequence of floats.
        dead_zone:       Spherical dead-zone radius.
        saturation_zone: Spherical saturation radius.
        max_value:       Output norm at and above *saturation_zone*.

    Returns:
        Direction-preserving, norm-scaled tuple with the same length as *value*.
    """
    vector = tuple(float(component) for component in value)
    norm = math.sqrt(sum(component * component for component in vector))
    safe_dead_zone = abs(float(dead_zone))
    safe_saturation_zone = max(abs(float(saturation_zone)), safe_dead_zone)

    if norm <= safe_dead_zone or norm <= 1e-12:
        return tuple(0.0 for _ in vector)

    scaled_norm = abs(
        apply_scaled_dead_zone(norm, safe_dead_zone, safe_saturation_zone, max_value)
    )
    return tuple((component / norm) * scaled_norm for component in vector)
