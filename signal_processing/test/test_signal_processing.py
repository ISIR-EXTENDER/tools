import pytest

from signal_processing import (
    FirstOrderLowPassFilter,
    OneEuroFilter,
    OneEuroFilter3D,
    apply_norm_dead_zone,
    apply_scaled_dead_zone,
    apply_scaled_dead_zone_per_axis,
    clamp,
    compute_low_pass_alpha,
    limit_norm,
    rate_limit_per_axis,
)


def test_clamp_and_rate_limit():
    # Values outside the requested interval should saturate to the nearest bound.
    assert clamp(3.0, -1.0, 1.0) == 1.0
    assert clamp(-3.0, -1.0, 1.0) == -1.0

    # Deltas larger than 0.75 are clipped per axis, while smaller deltas pass through.
    assert rate_limit_per_axis((2.0, -2.0, 0.5), (0.0, 0.0, 0.0), 0.75) == (0.75, -0.75, 0.5)


def test_limit_norm_and_dead_zone():
    # The 3-4-5 vector is scaled by 0.5 so its direction is preserved at norm 2.5.
    limited = limit_norm((3.0, 4.0, 0.0), 2.5)
    assert limited == (1.5, 2.0, 0.0)

    # The dead-zone boundary and magnitudes below it are both treated as inactive input.
    assert apply_norm_dead_zone((0.1, 0.0, 0.0), 0.1, 1.0) == (0.0, 0.0, 0.0)
    assert apply_scaled_dead_zone(0.05, 0.1, 1.0) == 0.0

    # Per-axis deadbands leave each component independent, including sign and saturation.
    per_axis = apply_scaled_dead_zone_per_axis((0.05, -0.55, 2.0), 0.1, 1.0)
    assert per_axis == pytest.approx((0.0, -0.5, 1.0))

    # Between dead-zone and saturation, the norm follows a linear ramp: (0.55 - 0.1) / 1.0.
    ramped = apply_norm_dead_zone((0.55, 0.0, 0.0), 0.1, 1.1)
    assert ramped[0] == pytest.approx(0.45)
    assert ramped[1] == pytest.approx(0.0)
    assert ramped[2] == pytest.approx(0.0)


def test_low_pass_filter_state():
    # Equal sample period and time constant give alpha = T / (T + tau) = 0.5.
    assert compute_low_pass_alpha(0.1, 0.1) == 0.5

    # The first sample warm-starts the state; the next sample blends halfway toward input.
    filter_instance = FirstOrderLowPassFilter()
    assert filter_instance.filter((1.0, 2.0, 3.0), 0.2) == (1.0, 2.0, 3.0)
    assert filter_instance.filter((3.0, 2.0, 1.0), 0.5) == (2.0, 2.0, 2.0)


def test_one_euro_filter_scalar_and_vector():
    # The scalar filter initializes from the first sample, then smooths toward the next value.
    filter_instance = OneEuroFilter(30.0, 1.0, 0.0, 1.0)
    assert filter_instance.filter(0.0, 0.0) == 0.0
    second = filter_instance.filter(1.0, 0.1)
    assert 0.0 < second < 1.0

    # The 3D wrapper warm-starts all axes, then filters each axis independently.
    vector_filter = OneEuroFilter3D(30.0, 1.0, 0.0, 1.0)
    assert vector_filter.filter((0.0, 0.0, 0.0), 0.0) == (0.0, 0.0, 0.0)

    # Each axis should move toward its own target without crossing or reaching it in one step.
    filtered = vector_filter.filter((1.0, -1.0, 2.0), 0.1)
    assert 0.0 < filtered[0] < 1.0
    assert -1.0 < filtered[1] < 0.0
    assert 0.0 < filtered[2] < 2.0
