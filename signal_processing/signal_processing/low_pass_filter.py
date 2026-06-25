"""First-order discrete low-pass filter utilities.

Implements exponential smoothing (EMA / IIR first-order low-pass):

    y[n] = α * x[n] + (1 − α) * y[n-1]

where α = T / (T + τ), T is the sample period and τ is the time constant.

Provided helpers:
    compute_low_pass_alpha  – Convert period + time-constant to α.
    exponential_smoothing   – Single-shot stateless application for scalars or sequences.
    FirstOrderLowPassFilter – Stateful filter object for repeated calls.
"""
from __future__ import annotations

from typing import Iterable

from .saturation import clamp


def compute_low_pass_alpha(sample_period: float, time_constant: float) -> float:
    """Compute the smoothing coefficient α for a first-order low-pass filter.

    Uses the formula α = T / (T + τ) where T is the sample period and τ is
    the time constant.  Returns 1.0 (no filtering) when either argument is
    non-positive.

    Args:
        sample_period:  Sampling period T (seconds).
        time_constant:  Filter time constant τ (seconds).

    Returns:
        α ∈ [0, 1].  Close to 1 → fast response; close to 0 → heavy smoothing.
    """
    if sample_period <= 0.0 or time_constant <= 0.0:
        return 1.0
    return clamp(sample_period / (sample_period + time_constant), 0.0, 1.0)


def exponential_smoothing(input_value, previous_value, alpha: float):
    """Apply one step of exponential smoothing without maintaining state.

    Computes ``y = α * input + (1 − α) * previous`` with α clamped to [0, 1].
    Accepts both scalar and sequence (list/tuple) inputs; sequences are
    processed element-wise.

    Args:
        input_value:    Current raw sample x[n].
        previous_value: Previously filtered output y[n-1].
        alpha:          Filter coefficient α ∈ [0, 1].

    Returns:
        Filtered value y[n] with the same type as *input_value*.
    """
    safe_alpha = clamp(alpha, 0.0, 1.0)
    if isinstance(input_value, (list, tuple)):
        return tuple(
            safe_alpha * current + (1.0 - safe_alpha) * previous
            for current, previous in zip(input_value, previous_value)
        )
    return safe_alpha * input_value + (1.0 - safe_alpha) * previous_value


class FirstOrderLowPassFilter:
    """Stateful first-order low-pass filter.

    Maintains internal state across calls so consumers do not need to track
    the previous filtered value themselves.

    The first call to :meth:`filter` initialises the state to the input value
    (warm-start) to avoid a large transient at startup.  Call :meth:`reset`
    to reinitialise before a new signal segment.

    Supports both scalar and sequence inputs; the state type is inferred from
    the first sample passed to :meth:`filter`.

    Example::

        lpf = FirstOrderLowPassFilter()
        alpha = compute_low_pass_alpha(0.01, 0.05)  # T=10 ms, τ=50 ms
        for sample in samples:
            smoothed = lpf.filter(sample, alpha)
    """

    def __init__(self):
        self._initialized = False
        self._state = 0.0

    def reset(self) -> None:
        """Reset internal state; the next :meth:`filter` call will re-initialise."""
        self._initialized = False
        self._state = 0.0

    @property
    def initialized(self) -> bool:
        """True after the first call to :meth:`filter` has initialised the state."""
        return self._initialized

    @property
    def state(self):
        """Current internal (filtered) state value."""
        return self._state

    def filter(self, input_value, alpha: float):
        """Filter one sample.

        On the first call (not yet initialised) the state is set to
        *input_value* directly and returned unchanged.  Subsequent calls
        apply :func:`exponential_smoothing` with the supplied *alpha*.

        Args:
            input_value: New raw sample x[n] (scalar or sequence).
            alpha:       Filter coefficient α ∈ [0, 1].

        Returns:
            Filtered value y[n].
        """
        if not self._initialized:
            self._state = input_value
            self._initialized = True
            return self._state

        self._state = exponential_smoothing(input_value, self._state, alpha)
        return self._state