"""Model layer for the interactive signal-processing tester."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random
from typing import Deque, Iterable

from .dead_zone import (
    apply_dead_zone,
    apply_norm_dead_zone,
    apply_scaled_dead_zone_per_axis,
)
from .low_pass_filter import FirstOrderLowPassFilter, compute_low_pass_alpha
from .one_euro_filter import OneEuroFilter
from .saturation import clamp, clamp_symmetric, limit_norm, rate_limit_per_axis


Signal2D = tuple[float, float]

EPSILON = 1e-12


def _as_signal_2d(value: Iterable[float]) -> Signal2D:
    """Return the first two components of an iterable as a float signal pair."""
    components = tuple(float(component) for component in value)
    if len(components) < 2:
        raise ValueError("A 2-D signal requires at least two components.")
    return components[0], components[1]


def _clamp01(value: float) -> float:
    """Clamp a scalar to the normalized drawing interval [0, 1]."""
    return clamp(float(value), 0.0, 1.0)


def _ordered_bounds(lower: float, upper: float) -> tuple[float, float]:
    """Return numeric bounds in ascending order."""
    lower = float(lower)
    upper = float(upper)
    return (lower, upper) if lower <= upper else (upper, lower)


@dataclass
class SignalScale:
    """Mapping between a square zone and signal coordinates."""

    x_min: float = -1.0
    x_max: float = 1.0
    y_min: float = -1.0
    y_max: float = 1.0

    @property
    def x_bounds(self) -> tuple[float, float]:
        """Return x signal bounds in ascending order."""
        return _ordered_bounds(self.x_min, self.x_max)

    @property
    def y_bounds(self) -> tuple[float, float]:
        """Return y signal bounds in ascending order."""
        return _ordered_bounds(self.y_min, self.y_max)

    def signal_from_zone_position(self, x: float, y: float, zone_size: float) -> Signal2D:
        """Convert a local square position to centered y-up signal coordinates."""
        size = max(float(zone_size), 1.0)
        x_fraction = _clamp01(float(x) / size)
        y_fraction = _clamp01(float(y) / size)
        x_min, x_max = self.x_bounds
        y_min, y_max = self.y_bounds

        signal_x = x_min + x_fraction * (x_max - x_min)
        signal_y = y_max - y_fraction * (y_max - y_min)
        return signal_x, signal_y

    def point_from_signal(
        self,
        signal: Iterable[float],
        zone_size: float,
        clamp_to_zone: bool = True,
    ) -> Signal2D:
        """Convert a signal value to a local square position for drawing."""
        signal_x, signal_y = _as_signal_2d(signal)
        size = max(float(zone_size), 1.0)
        x_min, x_max = self.x_bounds
        y_min, y_max = self.y_bounds

        if abs(x_max - x_min) <= EPSILON:
            x_fraction = 0.5
        else:
            x_fraction = (signal_x - x_min) / (x_max - x_min)

        if abs(y_max - y_min) <= EPSILON:
            y_fraction = 0.5
        else:
            y_fraction = (y_max - signal_y) / (y_max - y_min)

        if clamp_to_zone:
            x_fraction = _clamp01(x_fraction)
            y_fraction = _clamp01(y_fraction)

        return x_fraction * size, y_fraction * size

    @property
    def center_signal(self) -> Signal2D:
        """Return the signal value at the geometric center of the zone."""
        x_min, x_max = self.x_bounds
        y_min, y_max = self.y_bounds
        return (x_min + x_max) * 0.5, (y_min + y_max) * 0.5


class InputNoiseGenerator:
    """Add independent zero-mean Gaussian noise to 2-D input samples."""

    def __init__(
        self,
        enabled: bool = False,
        standard_deviation: float = 0.05,
        seed: int | None = None,
    ):
        self.enabled = bool(enabled)
        self.standard_deviation = max(0.0, float(standard_deviation))
        self._random = random.Random(seed)

    def reset(self, seed: int | None = None) -> None:
        """Optionally reseed the random stream used for deterministic tests."""
        if seed is not None:
            self._random.seed(seed)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable noise generation without changing its amplitude."""
        self.enabled = bool(enabled)

    def set_standard_deviation(self, standard_deviation: float) -> None:
        """Set the Gaussian standard deviation in signal units."""
        self.standard_deviation = max(0.0, float(standard_deviation))

    def apply(self, signal: Iterable[float]) -> Signal2D:
        """Return the input signal with optional independent x/y Gaussian noise."""
        value = _as_signal_2d(signal)
        if not self.enabled or self.standard_deviation <= 0.0:
            return value
        return (
            value[0] + self._random.gauss(0.0, self.standard_deviation),
            value[1] + self._random.gauss(0.0, self.standard_deviation),
        )


class SignalTesterFlow:
    """Apply tester input noise before the processing pipeline."""

    def __init__(
        self,
        pipeline: ProcessingPipeline,
        noise: InputNoiseGenerator | None = None,
    ):
        self.pipeline = pipeline
        self.noise = noise if noise is not None else InputNoiseGenerator()

    def process(self, raw_input_signal: Iterable[float]) -> tuple[Signal2D, Signal2D]:
        """Apply input noise first, then process the noisy signal through the chain."""
        noisy_input_signal = self.noise.apply(raw_input_signal)
        output_signal = self.pipeline.process(noisy_input_signal)
        return noisy_input_signal, output_signal


@dataclass(frozen=True)
class SignalVisualizationGuide:
    """Description of a signal-space guide to draw in tester zones.

    ``shape`` selects the drawing primitive, ``role`` selects dead-zone or
    saturation styling, and ``value`` stores the signal-space threshold(s).
    """

    shape: str
    role: str
    value: tuple[float, ...]


@dataclass(frozen=True)
class ParameterSpec:
    """Numeric parameter metadata used to build component controls."""

    key: str
    label: str
    default: float
    minimum: float
    maximum: float
    step: float
    decimals: int = 3


@dataclass(frozen=True)
class ComponentSpec:
    """Processing component metadata used by the tester UI."""

    kind: str
    title: str
    description: str
    parameters: tuple[ParameterSpec, ...]


COMPONENT_SPECS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        "clamp",
        "Clamp per axis",
        "Clamp x and y independently to a lower and upper bound.",
        (
            ParameterSpec("lower", "Lower", -1.0, -1000.0, 1000.0, 0.1),
            ParameterSpec("upper", "Upper", 1.0, -1000.0, 1000.0, 0.1),
        ),
    ),
    ComponentSpec(
        "symmetric_clamp",
        "Symmetric clamp",
        "Clamp x and y independently to +/- limit.",
        (ParameterSpec("limit", "Limit", 1.0, 0.0, 1000.0, 0.05),),
    ),
    ComponentSpec(
        "rate_limit",
        "Rate limit",
        "Limit the per-sample change on each axis.",
        (ParameterSpec("max_delta", "Max delta", 0.05, 0.0, 1000.0, 0.01),),
    ),
    ComponentSpec(
        "norm_limit",
        "Norm limit",
        "Scale the 2-D vector so its Euclidean norm stays inside a maximum.",
        (ParameterSpec("max_norm", "Max norm", 1.0, 0.0, 1000.0, 0.05),),
    ),
    ComponentSpec(
        "hard_dead_zone",
        "Hard dead zone",
        "Zero each axis while it is inside the threshold.",
        (ParameterSpec("threshold", "Threshold", 0.1, 0.0, 1000.0, 0.01),),
    ),
    ComponentSpec(
        "scaled_dead_zone",
        "Scaled dead zone",
        "Apply a per-axis ramp from the dead-zone boundary to saturation.",
        (
            ParameterSpec("dead_zone", "Dead zone", 0.1, 0.0, 1000.0, 0.01),
            ParameterSpec("saturation_zone", "Saturation", 1.0, 0.0, 1000.0, 0.05),
        ),
    ),
    ComponentSpec(
        "norm_dead_zone",
        "Norm dead zone",
        "Apply a radial dead zone while preserving direction.",
        (
            ParameterSpec("dead_zone", "Dead zone", 0.1, 0.0, 1000.0, 0.01),
            ParameterSpec("saturation_zone", "Saturation", 1.0, 0.0, 1000.0, 0.05),
        ),
    ),
    ComponentSpec(
        "low_pass",
        "Low-pass filter",
        "First-order low-pass filter using the tester sample period.",
        (ParameterSpec("time_constant", "Time constant", 0.15, 0.0, 10.0, 0.01),),
    ),
    ComponentSpec(
        "one_euro",
        "One Euro filter",
        "Adaptive low-pass filter tuned by signal speed.",
        (
            ParameterSpec("frequency", "Frequency", 60.0, 0.001, 1000.0, 1.0),
            ParameterSpec("min_cutoff", "Min cutoff", 1.0, 0.000001, 1000.0, 0.05),
            ParameterSpec("beta", "Beta", 0.1, 0.0, 1000.0, 0.01),
            ParameterSpec("d_cutoff", "Derivative cutoff", 1.0, 0.000001, 1000.0, 0.05),
        ),
    ),
)

COMPONENT_SPECS_BY_KIND = {spec.kind: spec for spec in COMPONENT_SPECS}


@dataclass
class ProcessingBlock:
    """One reorderable processing component in the tester pipeline."""

    kind: str
    enabled: bool = False
    parameters: dict[str, float] = field(default_factory=dict)
    _low_pass_filter: FirstOrderLowPassFilter = field(init=False, repr=False)
    _rate_initialized: bool = field(default=False, init=False, repr=False)
    _rate_previous: Signal2D = field(default=(0.0, 0.0), init=False, repr=False)
    _one_euro_x: OneEuroFilter | None = field(default=None, init=False, repr=False)
    _one_euro_y: OneEuroFilter | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Merge caller parameters with the component defaults."""
        if self.kind not in COMPONENT_SPECS_BY_KIND:
            raise ValueError(f"Unknown processing component kind: {self.kind}")
        defaults = {
            parameter.key: parameter.default
            for parameter in COMPONENT_SPECS_BY_KIND[self.kind].parameters
        }
        defaults.update({key: float(value) for key, value in self.parameters.items()})
        self.parameters = defaults
        self._low_pass_filter = FirstOrderLowPassFilter()

    @property
    def spec(self) -> ComponentSpec:
        """Return metadata for this block kind."""
        return COMPONENT_SPECS_BY_KIND[self.kind]

    def reset(self) -> None:
        """Reset stateful processing state while keeping parameters and enabled state."""
        self._low_pass_filter.reset()
        self._rate_initialized = False
        self._rate_previous = (0.0, 0.0)
        self._one_euro_x = None
        self._one_euro_y = None

    def set_parameter(self, key: str, value: float) -> None:
        """Set a block parameter and reset state that depends on it."""
        if key not in self.parameters:
            raise KeyError(f"{self.kind} has no parameter named {key}")
        self.parameters[key] = float(value)
        self.reset()

    def process(
        self,
        signal: Iterable[float],
        sample_period: float,
        timestamp_sec: float,
    ) -> Signal2D:
        """Process one 2-D sample if the block is enabled."""
        value = _as_signal_2d(signal)
        if not self.enabled:
            return value

        if self.kind == "clamp":
            lower = self.parameters["lower"]
            upper = self.parameters["upper"]
            return clamp(value[0], lower, upper), clamp(value[1], lower, upper)

        if self.kind == "symmetric_clamp":
            return _as_signal_2d(clamp_symmetric(value, self.parameters["limit"]))

        if self.kind == "rate_limit":
            if not self._rate_initialized:
                self._rate_previous = value
                self._rate_initialized = True
                return value
            limited = _as_signal_2d(
                rate_limit_per_axis(value, self._rate_previous, self.parameters["max_delta"])
            )
            self._rate_previous = limited
            return limited

        if self.kind == "norm_limit":
            return _as_signal_2d(limit_norm(value, self.parameters["max_norm"]))

        if self.kind == "hard_dead_zone":
            threshold = self.parameters["threshold"]
            return apply_dead_zone(value[0], threshold), apply_dead_zone(value[1], threshold)

        if self.kind == "scaled_dead_zone":
            return _as_signal_2d(
                apply_scaled_dead_zone_per_axis(
                    value,
                    self.parameters["dead_zone"],
                    self.parameters["saturation_zone"],
                )
            )

        if self.kind == "norm_dead_zone":
            return _as_signal_2d(
                apply_norm_dead_zone(
                    value,
                    self.parameters["dead_zone"],
                    self.parameters["saturation_zone"],
                )
            )

        if self.kind == "low_pass":
            alpha = compute_low_pass_alpha(sample_period, self.parameters["time_constant"])
            return _as_signal_2d(self._low_pass_filter.filter(value, alpha))

        if self.kind == "one_euro":
            self._ensure_one_euro_filters()
            assert self._one_euro_x is not None
            assert self._one_euro_y is not None
            return (
                self._one_euro_x.filter(value[0], timestamp_sec),
                self._one_euro_y.filter(value[1], timestamp_sec),
            )

        raise ValueError(f"Unhandled processing component kind: {self.kind}")

    def _ensure_one_euro_filters(self) -> None:
        """Create scalar One Euro filters lazily from the current parameters."""
        if self._one_euro_x is not None and self._one_euro_y is not None:
            return
        self._one_euro_x = OneEuroFilter(
            self.parameters["frequency"],
            self.parameters["min_cutoff"],
            self.parameters["beta"],
            self.parameters["d_cutoff"],
        )
        self._one_euro_y = OneEuroFilter(
            self.parameters["frequency"],
            self.parameters["min_cutoff"],
            self.parameters["beta"],
            self.parameters["d_cutoff"],
        )


def collect_signal_visualization_guides(
    blocks: Iterable[ProcessingBlock],
) -> list[SignalVisualizationGuide]:
    """Collect enabled dead-zone and saturation guides for square-zone drawing."""
    guides: list[SignalVisualizationGuide] = []
    for block in blocks:
        if not block.enabled:
            continue

        if block.kind == "hard_dead_zone":
            guides.append(
                SignalVisualizationGuide(
                    "axis_band",
                    "dead_zone",
                    (abs(block.parameters["threshold"]),),
                )
            )
        elif block.kind == "scaled_dead_zone":
            guides.append(
                SignalVisualizationGuide(
                    "axis_band",
                    "dead_zone",
                    (abs(block.parameters["dead_zone"]),),
                )
            )
            guides.append(
                SignalVisualizationGuide(
                    "axis_lines",
                    "saturation",
                    (abs(block.parameters["saturation_zone"]),),
                )
            )
        elif block.kind == "norm_dead_zone":
            guides.append(
                SignalVisualizationGuide(
                    "radius",
                    "dead_zone",
                    (abs(block.parameters["dead_zone"]),),
                )
            )
            guides.append(
                SignalVisualizationGuide(
                    "radius",
                    "saturation",
                    (abs(block.parameters["saturation_zone"]),),
                )
            )
        elif block.kind == "clamp":
            lower, upper = _ordered_bounds(block.parameters["lower"], block.parameters["upper"])
            guides.append(SignalVisualizationGuide("bounds", "saturation", (lower, upper)))
        elif block.kind == "symmetric_clamp":
            limit = abs(block.parameters["limit"])
            guides.append(SignalVisualizationGuide("bounds", "saturation", (-limit, limit)))
        elif block.kind == "norm_limit":
            guides.append(
                SignalVisualizationGuide(
                    "radius",
                    "saturation",
                    (abs(block.parameters["max_norm"]),),
                )
            )

    return guides


def create_default_blocks() -> list[ProcessingBlock]:
    """Create one disabled block for each component exposed by the tester."""
    return [ProcessingBlock(spec.kind, enabled=False) for spec in COMPONENT_SPECS]


class ProcessingPipeline:
    """Ordered chain of enabled processing blocks."""

    def __init__(
        self,
        blocks: list[ProcessingBlock] | None = None,
        sample_rate_hz: float = 60.0,
    ):
        self.blocks = blocks if blocks is not None else create_default_blocks()
        self.sample_rate_hz = max(float(sample_rate_hz), 0.001)
        self.sample_period = 1.0 / self.sample_rate_hz
        self.timestamp_sec = 0.0

    def reset(self) -> None:
        """Reset chain timestamp and every stateful block."""
        self.timestamp_sec = 0.0
        for block in self.blocks:
            block.reset()

    def process(self, signal: Iterable[float], timestamp_sec: float | None = None) -> Signal2D:
        """Process one sample through the ordered block list."""
        if timestamp_sec is None:
            self.timestamp_sec += self.sample_period
        else:
            self.timestamp_sec = float(timestamp_sec)

        value = _as_signal_2d(signal)
        for block in self.blocks:
            value = block.process(value, self.sample_period, self.timestamp_sec)
        return value

    def move_block(self, source_index: int, destination_index: int) -> None:
        """Move one block to a new chain position and reset state."""
        if source_index == destination_index:
            return
        if not 0 <= source_index < len(self.blocks):
            raise IndexError("source_index is outside the processing block list")
        if not 0 <= destination_index < len(self.blocks):
            raise IndexError("destination_index is outside the processing block list")
        block = self.blocks.pop(source_index)
        self.blocks.insert(destination_index, block)
        self.reset()

    def set_block_enabled(self, index: int, enabled: bool) -> None:
        """Set one block's enabled state and reset stateful processing."""
        self.blocks[index].enabled = bool(enabled)
        self.reset()

    def update_block_parameter(self, index: int, key: str, value: float) -> None:
        """Update one block parameter and reset stateful processing."""
        self.blocks[index].set_parameter(key, value)
        self.reset()


@dataclass(frozen=True)
class HistorySample:
    timestamp_sec: float
    input_signal: Signal2D
    output_signal: Signal2D


class SignalHistory:
    """Fixed-size rolling input/output signal history."""

    def __init__(self, max_seconds: float = 6.0, sample_rate_hz: float = 60.0):
        capacity = max(1, int(max_seconds * sample_rate_hz))
        self._samples: Deque[HistorySample] = deque(maxlen=capacity)

    def append(
        self,
        timestamp_sec: float,
        input_signal: Iterable[float],
        output_signal: Iterable[float],
    ) -> None:
        """Append one input/output sample pair to the rolling history."""
        self._samples.append(
            HistorySample(
                float(timestamp_sec),
                _as_signal_2d(input_signal),
                _as_signal_2d(output_signal),
            )
        )

    def clear(self) -> None:
        """Remove all stored history samples."""
        self._samples.clear()

    def series(self) -> dict[str, list[float]]:
        """Return history as plot-ready time, input, and output arrays."""
        if not self._samples:
            return {
                "time": [],
                "input_x": [],
                "input_y": [],
                "output_x": [],
                "output_y": [],
            }

        origin = self._samples[0].timestamp_sec
        return {
            "time": [sample.timestamp_sec - origin for sample in self._samples],
            "input_x": [sample.input_signal[0] for sample in self._samples],
            "input_y": [sample.input_signal[1] for sample in self._samples],
            "output_x": [sample.output_signal[0] for sample in self._samples],
            "output_y": [sample.output_signal[1] for sample in self._samples],
        }
