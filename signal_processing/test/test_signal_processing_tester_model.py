import pytest

from signal_processing import (
    OneEuroFilter,
    apply_dead_zone,
    apply_norm_dead_zone,
    apply_scaled_dead_zone_per_axis,
    clamp,
    clamp_symmetric,
    compute_low_pass_alpha,
    limit_norm,
    rate_limit_per_axis,
)
from signal_processing.tester_model import (
    COMPONENT_SPECS,
    InputNoiseGenerator,
    ProcessingBlock,
    ProcessingPipeline,
    SignalHistory,
    SignalScale,
    SignalTesterFlow,
    SignalVisualizationGuide,
    collect_signal_visualization_guides,
    create_default_blocks,
)


def test_signal_scale_maps_centered_y_up_coordinates():
    scale = SignalScale()

    assert scale.signal_from_zone_position(100.0, 100.0, 200.0) == pytest.approx((0.0, 0.0))
    assert scale.signal_from_zone_position(200.0, 0.0, 200.0) == pytest.approx((1.0, 1.0))
    assert scale.signal_from_zone_position(0.0, 200.0, 200.0) == pytest.approx((-1.0, -1.0))

    assert scale.point_from_signal((0.0, 0.0), 200.0) == pytest.approx((100.0, 100.0))
    assert scale.point_from_signal((1.0, 1.0), 200.0) == pytest.approx((200.0, 0.0))


def test_signal_scale_clamps_positions_at_zone_edges():
    scale = SignalScale(x_min=-2.0, x_max=2.0, y_min=-4.0, y_max=4.0)

    assert scale.signal_from_zone_position(-50.0, -25.0, 200.0) == pytest.approx((-2.0, 4.0))
    assert scale.signal_from_zone_position(250.0, 300.0, 200.0) == pytest.approx((2.0, -4.0))
    assert scale.point_from_signal((10.0, -10.0), 200.0) == pytest.approx((200.0, 200.0))


def test_default_pipeline_starts_with_disabled_components():
    blocks = create_default_blocks()
    pipeline = ProcessingPipeline(blocks, sample_rate_hz=60.0)

    assert len(blocks) == len(COMPONENT_SPECS)
    assert all(not block.enabled for block in blocks)
    assert pipeline.process((0.25, -0.5)) == pytest.approx((0.25, -0.5))


def test_pipeline_enable_disable_and_reorder_behavior():
    clamp_block = ProcessingBlock(
        "clamp",
        enabled=False,
        parameters={"lower": -0.5, "upper": 0.5},
    )
    scaled_dead_zone = ProcessingBlock(
        "scaled_dead_zone",
        enabled=True,
        parameters={"dead_zone": 0.25, "saturation_zone": 0.5},
    )
    pipeline = ProcessingPipeline([clamp_block, scaled_dead_zone], sample_rate_hz=60.0)

    assert pipeline.process((1.0, 0.0)) == pytest.approx((1.0, 0.0))

    pipeline.set_block_enabled(0, True)
    assert pipeline.process((1.0, 0.0)) == pytest.approx((1.0, 0.0))

    pipeline.move_block(1, 0)
    assert pipeline.process((1.0, 0.0)) == pytest.approx((0.5, 0.0))


def test_pipeline_reset_clears_stateful_rate_limit():
    block = ProcessingBlock("rate_limit", enabled=True, parameters={"max_delta": 0.1})
    pipeline = ProcessingPipeline([block], sample_rate_hz=60.0)

    assert pipeline.process((1.0, 0.0)) == pytest.approx((1.0, 0.0))
    assert pipeline.process((0.0, 0.0)) == pytest.approx((0.9, 0.0))

    pipeline.reset()
    assert pipeline.process((0.0, 0.0)) == pytest.approx((0.0, 0.0))


def test_disabled_input_noise_returns_raw_signal():
    noise = InputNoiseGenerator(enabled=False, standard_deviation=10.0, seed=1)

    assert noise.apply((1.0, -2.0)) == pytest.approx((1.0, -2.0))


def test_zero_std_dev_input_noise_returns_raw_signal():
    noise = InputNoiseGenerator(enabled=True, standard_deviation=0.0, seed=1)

    assert noise.apply((1.0, -2.0)) == pytest.approx((1.0, -2.0))


def test_seeded_input_noise_is_deterministic():
    first = InputNoiseGenerator(enabled=True, standard_deviation=0.25, seed=42)
    second = InputNoiseGenerator(enabled=True, standard_deviation=0.25, seed=42)

    assert first.apply((1.0, -2.0)) == pytest.approx(second.apply((1.0, -2.0)))
    assert first.apply((1.0, -2.0)) == pytest.approx(second.apply((1.0, -2.0)))


def test_input_noise_affects_axes_independently():
    noise = InputNoiseGenerator(enabled=True, standard_deviation=0.25, seed=7)

    noisy_x, noisy_y = noise.apply((0.0, 0.0))

    assert noisy_x != pytest.approx(0.0)
    assert noisy_y != pytest.approx(0.0)
    assert noisy_x != pytest.approx(noisy_y)


def test_signal_flow_feeds_noisy_input_to_pipeline_and_history():
    class FixedNoise:
        def apply(self, signal):
            return (9.0, -9.0)

    pipeline = ProcessingPipeline(
        [
            ProcessingBlock(
                "clamp",
                enabled=True,
                parameters={"lower": -2.0, "upper": 2.0},
            )
        ],
        sample_rate_hz=60.0,
    )
    flow = SignalTesterFlow(pipeline, FixedNoise())
    history = SignalHistory(max_seconds=1.0, sample_rate_hz=60.0)

    noisy_input, output = flow.process((0.1, 0.2))
    history.append(pipeline.timestamp_sec, noisy_input, output)

    assert noisy_input == pytest.approx((9.0, -9.0))
    assert output == pytest.approx((2.0, -2.0))
    assert history.series()["input_x"] == pytest.approx([9.0])
    assert history.series()["input_y"] == pytest.approx([-9.0])


def test_visualization_guides_ignore_disabled_blocks():
    blocks = [
        ProcessingBlock(
            "scaled_dead_zone",
            enabled=False,
            parameters={"dead_zone": 0.2, "saturation_zone": 0.8},
        )
    ]

    assert collect_signal_visualization_guides(blocks) == []


def test_visualization_guides_include_dead_zone_and_saturation_shapes():
    blocks = [
        ProcessingBlock("hard_dead_zone", enabled=True, parameters={"threshold": 0.2}),
        ProcessingBlock(
            "scaled_dead_zone",
            enabled=True,
            parameters={"dead_zone": 0.1, "saturation_zone": 0.9},
        ),
        ProcessingBlock(
            "norm_dead_zone",
            enabled=True,
            parameters={"dead_zone": 0.3, "saturation_zone": 1.1},
        ),
    ]

    assert collect_signal_visualization_guides(blocks) == [
        SignalVisualizationGuide("axis_band", "dead_zone", (0.2,)),
        SignalVisualizationGuide("axis_band", "dead_zone", (0.1,)),
        SignalVisualizationGuide("axis_lines", "saturation", (0.9,)),
        SignalVisualizationGuide("radius", "dead_zone", (0.3,)),
        SignalVisualizationGuide("radius", "saturation", (1.1,)),
    ]


def test_visualization_guides_include_saturation_limits():
    blocks = [
        ProcessingBlock("clamp", enabled=True, parameters={"lower": 0.75, "upper": -0.25}),
        ProcessingBlock("symmetric_clamp", enabled=True, parameters={"limit": -0.5}),
        ProcessingBlock("norm_limit", enabled=True, parameters={"max_norm": 1.25}),
    ]

    assert collect_signal_visualization_guides(blocks) == [
        SignalVisualizationGuide("bounds", "saturation", (-0.25, 0.75)),
        SignalVisualizationGuide("bounds", "saturation", (-0.5, 0.5)),
        SignalVisualizationGuide("radius", "saturation", (1.25,)),
    ]


@pytest.mark.parametrize(
    ("kind", "parameters", "value", "expected"),
    [
        (
            "clamp",
            {"lower": -0.75, "upper": 0.5},
            (2.0, -2.0),
            (clamp(2.0, -0.75, 0.5), clamp(-2.0, -0.75, 0.5)),
        ),
        (
            "symmetric_clamp",
            {"limit": 0.5},
            (2.0, -2.0),
            clamp_symmetric((2.0, -2.0), 0.5),
        ),
        (
            "norm_limit",
            {"max_norm": 2.5},
            (3.0, 4.0),
            limit_norm((3.0, 4.0), 2.5),
        ),
        (
            "hard_dead_zone",
            {"threshold": 0.1},
            (0.05, -0.2),
            (apply_dead_zone(0.05, 0.1), apply_dead_zone(-0.2, 0.1)),
        ),
        (
            "scaled_dead_zone",
            {"dead_zone": 0.1, "saturation_zone": 1.0},
            (0.55, -2.0),
            apply_scaled_dead_zone_per_axis((0.55, -2.0), 0.1, 1.0),
        ),
        (
            "norm_dead_zone",
            {"dead_zone": 0.1, "saturation_zone": 1.1},
            (0.55, 0.0),
            apply_norm_dead_zone((0.55, 0.0), 0.1, 1.1),
        ),
    ],
)
def test_stateless_processing_blocks_match_existing_helpers(kind, parameters, value, expected):
    block = ProcessingBlock(kind, enabled=True, parameters=parameters)

    assert block.process(value, 1.0 / 60.0, 0.0) == pytest.approx(expected)


def test_rate_limit_block_matches_existing_helper_after_warm_start():
    block = ProcessingBlock("rate_limit", enabled=True, parameters={"max_delta": 0.25})

    previous = block.process((0.0, 0.0), 1.0 / 60.0, 0.0)
    assert block.process((1.0, -1.0), 1.0 / 60.0, 1.0 / 60.0) == pytest.approx(
        rate_limit_per_axis((1.0, -1.0), previous, 0.25)
    )


def test_low_pass_block_matches_existing_helper_after_warm_start():
    sample_period = 1.0 / 60.0
    block = ProcessingBlock(
        "low_pass",
        enabled=True,
        parameters={"time_constant": sample_period},
    )

    assert block.process((0.0, 0.0), sample_period, 0.0) == pytest.approx((0.0, 0.0))
    alpha = compute_low_pass_alpha(sample_period, sample_period)
    assert block.process((1.0, -1.0), sample_period, sample_period) == pytest.approx((alpha, -alpha))


def test_one_euro_block_matches_existing_scalar_filters():
    sample_period = 1.0 / 60.0
    parameters = {
        "frequency": 60.0,
        "min_cutoff": 1.0,
        "beta": 0.1,
        "d_cutoff": 1.0,
    }
    block = ProcessingBlock("one_euro", enabled=True, parameters=parameters)
    expected_x = OneEuroFilter(**parameters)
    expected_y = OneEuroFilter(**parameters)

    first_time = sample_period
    assert block.process((0.0, 0.0), sample_period, first_time) == pytest.approx(
        (
            expected_x.filter(0.0, first_time),
            expected_y.filter(0.0, first_time),
        )
    )

    second_time = 2.0 * sample_period
    assert block.process((1.0, -1.0), sample_period, second_time) == pytest.approx(
        (
            expected_x.filter(1.0, second_time),
            expected_y.filter(-1.0, second_time),
        )
    )


def test_signal_history_keeps_rolling_series():
    history = SignalHistory(max_seconds=1.0, sample_rate_hz=2.0)

    history.append(0.0, (0.0, 0.0), (0.0, 0.0))
    history.append(0.5, (1.0, 2.0), (3.0, 4.0))
    history.append(1.0, (5.0, 6.0), (7.0, 8.0))

    assert history.series() == {
        "time": [0.0, 0.5],
        "input_x": [1.0, 5.0],
        "input_y": [2.0, 6.0],
        "output_x": [3.0, 7.0],
        "output_y": [4.0, 8.0],
    }
