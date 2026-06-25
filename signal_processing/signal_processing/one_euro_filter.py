"""One Euro filter for scalar and 3-D vector signals.

The One Euro filter (Casiez et al., CHI 2012) is an adaptive low-pass filter
that automatically adjusts its cutoff frequency based on the estimated signal
speed.  It reduces lag for fast-moving signals while still smoothing slow
noisy ones.

Cutoff frequency at each step::

    fc = min_cutoff + β * |dx̂/dt|

where dx̂/dt is itself a first-order smoothed derivative with cutoff
frequency *d_cutoff*.

Tuning guidance:
    - Increase *min_cutoff* to reduce lag at the cost of more jitter at rest.
    - Increase *beta* to reduce lag during fast motion.
    - *d_cutoff* usually needs no tuning (default 1 Hz works well).

Classes:
    OneEuroFilter   – Scalar signal.  User supplies wall-clock timestamps.
    OneEuroFilter3D – Per-axis independent filtering of 3-element sequences.

Reference:
    Casiez, G., Roussel, N., & Vogel, D. (2012). 1€ Filter: A simple
    speed-based low-pass filter for noisy input in interactive systems.
    Proc. ACM CHI 2012.
"""
from __future__ import annotations

import math

from .low_pass_filter import exponential_smoothing


def _smoothing_factor(dt: float, cutoff: float) -> float:
    """Compute EMA smoothing coefficient α from a time step and cutoff frequency.

    Uses α = 1 / (1 + τ/dt) where τ = 1 / (2π fc).
    Returns 1.0 (no smoothing) when either argument is non-positive.

    Args:
        dt:     Time elapsed since the last sample (seconds).
        cutoff: Cutoff frequency fc (Hz).

    Returns:
        α ∈ (0, 1].
    """
    if dt <= 0.0 or cutoff <= 0.0:
        return 1.0
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    """Adaptive scalar One Euro filter.

    Maintains internal state (last value, last derivative, last timestamp)
    across calls.  Call :meth:`reset` to reinitialise before a new signal
    segment.

    The first call to :meth:`filter` initialises the state and returns
    *value* unchanged.  Non-monotonic timestamps are handled gracefully:
    a dt <= 0 is replaced by 1/frequency so the filter does not divide by zero.
    """

    def __init__(
        self,
        frequency: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.1,
        d_cutoff: float = 1.0,
    ):
        """
        Args:
            frequency:   Nominal input sampling frequency (Hz).  Used only as a
                         fallback when consecutive timestamps are non-monotonic.
            min_cutoff:  Minimum cutoff frequency (Hz).  Controls smoothing at rest.
            beta:        Speed coefficient.  Higher values reduce lag during motion.
            d_cutoff:    Cutoff frequency of the derivative low-pass pre-filter (Hz).
        """
        self.frequency = max(float(frequency), 1e-3)
        self.min_cutoff = max(float(min_cutoff), 1e-6)
        self.beta = max(float(beta), 0.0)
        self.d_cutoff = max(float(d_cutoff), 1e-6)
        self.last_value = 0.0        # Filtered value from the previous step.
        self.last_derivative = 0.0   # Smoothed derivative from the previous step.
        self.last_timestamp = -1.0   # Timestamp of the previous step (-1 = uninitialised).

    def reset(self) -> None:
        """Reset internal state; the next :meth:`filter` call will re-initialise."""
        self.last_value = 0.0
        self.last_derivative = 0.0
        self.last_timestamp = -1.0

    def filter(self, value: float, timestamp_sec: float) -> float:  # noqa: A003
        """Filter one scalar sample.

        Args:
            value:          Raw input sample.
            timestamp_sec:  Monotonic wall-clock timestamp of this sample (seconds).

        Returns:
            Filtered value.
        """
        value = float(value)
        timestamp_sec = float(timestamp_sec)

        if self.last_timestamp < 0.0:
            # First sample: warm-start the filter state.
            self.last_value = value
            self.last_derivative = 0.0
            self.last_timestamp = timestamp_sec
            return value

        dt = timestamp_sec - self.last_timestamp
        if dt <= 0.0:
            # Non-monotonic timestamp: fall back to nominal period.
            dt = 1.0 / self.frequency

        # Smooth the derivative to estimate signal speed.
        derivative = (value - self.last_value) / dt
        derivative_alpha = _smoothing_factor(dt, self.d_cutoff)
        filtered_derivative = exponential_smoothing(derivative, self.last_derivative, derivative_alpha)

        # Adapt cutoff frequency based on signal speed.
        cutoff = self.min_cutoff + self.beta * abs(filtered_derivative)
        alpha = _smoothing_factor(dt, cutoff)
        filtered_value = exponential_smoothing(value, self.last_value, alpha)

        self.last_value = filtered_value
        self.last_derivative = filtered_derivative
        self.last_timestamp = timestamp_sec
        return filtered_value


class OneEuroFilter3D:
    """One Euro filter applied independently to each axis of a 3-element sequence.

    Wraps three scalar :class:`OneEuroFilter` instances sharing the same
    parameters.  All three axes receive the same timestamp; their filtered
    outputs are assembled back into a tuple.

    See :class:`OneEuroFilter` for parameter descriptions and tuning guidance.
    """

    def __init__(
        self,
        frequency: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.1,
        d_cutoff: float = 1.0,
    ):
        """
        Args:
            frequency:   Nominal input sampling frequency (Hz).
            min_cutoff:  Minimum cutoff frequency (Hz).
            beta:        Speed coefficient.
            d_cutoff:    Cutoff of the derivative pre-filter (Hz).
        """
        self.filters = [
            OneEuroFilter(frequency, min_cutoff, beta, d_cutoff),
            OneEuroFilter(frequency, min_cutoff, beta, d_cutoff),
            OneEuroFilter(frequency, min_cutoff, beta, d_cutoff),
        ]

    def reset(self) -> None:
        """Reset all three axis filters."""
        for filter_instance in self.filters:
            filter_instance.reset()

    def filter(self, value, timestamp_sec: float):  # noqa: A003
        """Filter one 3-element sample.

        Args:
            value:          Raw 3-element input (x, y, z) as any iterable of floats.
            timestamp_sec:  Monotonic wall-clock timestamp (seconds).

        Returns:
            Filtered tuple of three floats (x, y, z).
        """
        return tuple(
            filter_instance.filter(component, timestamp_sec)
            for filter_instance, component in zip(self.filters, value)
        )