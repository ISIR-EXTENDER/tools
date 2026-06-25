"""Scalar and vector saturation/clamping helpers.

Provides:
    clamp               – Scalar clamp to a closed interval.
    clamp_symmetric     – Component-wise symmetric clamp of sequences.
    rate_limit_per_axis – Per-axis slew-rate limit between successive samples.
    limit_norm          – Scale a vector so its Euclidean norm does not exceed a bound.
"""
from __future__ import annotations

import math
from typing import Iterable


def _is_sequence(value: object) -> bool:
    return isinstance(value, (list, tuple))


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp *value* to the closed interval [*lower*, *upper*].

    If *lower* > *upper* the bounds are swapped before clamping.

    Args:
        value:  Value to clamp.
        lower:  Lower bound (inclusive).
        upper:  Upper bound (inclusive).

    Returns:
        Clamped value in [lower, upper].
    """
    if lower > upper:
        lower, upper = upper, lower
    return max(lower, min(value, upper))


def clamp_symmetric(value, limit):
    """Clamp each component of *value* to [-|limit|, +|limit|].

    *value* and *limit* may each be either a scalar or a sequence.  When both
    are sequences they are zipped together for per-element bounds.

    Args:
        value:  Scalar or sequence of floats.
        limit:  Scalar or per-element symmetric bound (absolute value is taken).

    Returns:
        Clamped scalar or tuple with the same length as *value*.
    """
    if _is_sequence(value):
        if _is_sequence(limit):
            return tuple(clamp(component, -abs(bound), abs(bound)) for component, bound in zip(value, limit))
        magnitude = abs(float(limit))
        return tuple(clamp(component, -magnitude, magnitude) for component in value)

    magnitude = abs(float(limit))
    return clamp(float(value), -magnitude, magnitude)


def rate_limit_per_axis(current: Iterable[float], previous: Iterable[float], max_delta) -> tuple[float, ...]:
    """Limit the per-axis change from *previous* to *current* by *max_delta*.

    Each output component satisfies:  |output_i - previous_i| <= |max_delta_i|

    *max_delta* may be a scalar (same limit on all axes) or a sequence of
    per-axis limits.

    Args:
        current:    New command vector.
        previous:   Previous output vector.
        max_delta:  Scalar or per-axis maximum allowed change per step.

    Returns:
        Tuple of rate-limited values with the same length as *current*.
    """
    if _is_sequence(max_delta):
        return tuple(
            previous_component + clamp(current_component - previous_component, -abs(delta), abs(delta))
            for current_component, previous_component, delta in zip(current, previous, max_delta)
        )

    magnitude = abs(float(max_delta))
    return tuple(
        previous_component + clamp(current_component - previous_component, -magnitude, magnitude)
        for current_component, previous_component in zip(current, previous)
    )


def limit_norm(value: Iterable[float], max_norm: float) -> tuple[float, ...]:
    """Scale *value* so that its Euclidean norm does not exceed *max_norm*.

    Direction is preserved.  If the norm is already within the limit the
    vector is returned unchanged.  If *max_norm* <= 0 a zero vector is returned.

    Args:
        value:    Input vector as a sequence of floats.
        max_norm: Maximum allowed Euclidean norm.

    Returns:
        Norm-limited tuple with the same length as *value*.
    """
    vector = tuple(float(component) for component in value)
    safe_max_norm = abs(float(max_norm))
    if safe_max_norm <= 0.0:
        return tuple(0.0 for _ in vector)

    current_norm = math.sqrt(sum(component * component for component in vector))
    if current_norm <= safe_max_norm or current_norm <= 1e-12:
        return vector

    scale = safe_max_norm / current_norm
    return tuple(component * scale for component in vector)