"""Qt desktop window for interactively testing signal-processing helpers."""
from __future__ import annotations

import sys

from python_qt_binding.QtCore import QLineF, QRectF, QSize, Qt, QTimer, Signal
from python_qt_binding.QtGui import QColor, QFont, QPainter, QPen
from python_qt_binding.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .tester_model import (
    InputNoiseGenerator,
    ProcessingPipeline,
    SignalHistory,
    SignalScale,
    SignalTesterFlow,
    SignalVisualizationGuide,
    collect_signal_visualization_guides,
)


SAMPLE_RATE_HZ = 60.0
SAMPLE_PERIOD_MS = int(1000.0 / SAMPLE_RATE_HZ)


def _event_position(event) -> tuple[float, float]:
    """Return a mouse event position for both Qt 5 and Qt 6 bindings."""
    if hasattr(event, "position"):
        position = event.position()
    else:
        position = event.pos()
    return float(position.x()), float(position.y())


class SignalZoneWidget(QWidget):
    """Square signal display with optional captured drag input."""

    signal_changed = Signal(tuple)

    def __init__(self, title: str, interactive: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._interactive = interactive
        self._dragging = False
        self._scale = SignalScale()
        self._signal = (0.0, 0.0)
        self._visualization_guides: list[SignalVisualizationGuide] = []
        self._accent = QColor("#2563eb" if interactive else "#14b8a6")
        self.setMinimumSize(290, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(False)

    def sizeHint(self) -> QSize:
        """Return the preferred widget size, including title and value text."""
        return QSize(330, 370)

    def set_scale(self, scale: SignalScale) -> None:
        """Set the signal-to-pixel mapping used by the zone."""
        self._scale = scale
        self.update()

    def set_signal(self, signal: tuple[float, float]) -> None:
        """Set the signal value represented by the cursor marker."""
        self._signal = (float(signal[0]), float(signal[1]))
        self.update()

    def set_visualization_guides(self, guides: list[SignalVisualizationGuide]) -> None:
        """Set processing guides drawn over the zone."""
        self._visualization_guides = list(guides)
        self.update()

    def mousePressEvent(self, event) -> None:
        """Begin captured drag input when the interactive zone is pressed."""
        if not self._interactive or event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self._dragging = True
        self.grabMouse()
        self._update_signal_from_event(event)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Update the raw input signal while dragging."""
        if not self._interactive or not self._dragging:
            return super().mouseMoveEvent(event)
        self._update_signal_from_event(event)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """Release captured input and recenter the raw signal at zero."""
        if not self._interactive or not self._dragging or event.button() != Qt.LeftButton:
            return super().mouseReleaseEvent(event)
        self._dragging = False
        self.releaseMouse()
        self._signal = (0.0, 0.0)
        self.signal_changed.emit(self._signal)
        self.update()
        event.accept()

    def _update_signal_from_event(self, event) -> None:
        """Map a mouse event to signal coordinates and emit the new value."""
        x, y = _event_position(event)
        zone = self._zone_rect()
        self._signal = self._scale.signal_from_zone_position(
            x - zone.left(),
            y - zone.top(),
            zone.width(),
        )
        self.signal_changed.emit(self._signal)
        self.update()

    def _zone_rect(self) -> QRectF:
        """Return the square drawing area inside the widget."""
        padding = 18.0
        title_height = 34.0
        available_width = max(1.0, float(self.width()) - 2.0 * padding)
        available_height = max(1.0, float(self.height()) - title_height - padding)
        side = min(available_width, available_height)
        left = (float(self.width()) - side) * 0.5
        top = title_height + (available_height - side) * 0.5
        return QRectF(left, top, side, side)

    def paintEvent(self, event) -> None:
        """Paint the zone background, guides, labels, and cursor."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        zone = self._zone_rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(zone, 8.0, 8.0)

        border_color = QColor("#cbd5e1")
        unclamped_point = self._scale.point_from_signal(
            self._signal,
            zone.width(),
            clamp_to_zone=False,
        )
        clamped_point = self._scale.point_from_signal(
            self._signal,
            zone.width(),
            clamp_to_zone=True,
        )
        is_clipped = (
            abs(unclamped_point[0] - clamped_point[0]) > 0.5
            or abs(unclamped_point[1] - clamped_point[1]) > 0.5
        )
        if is_clipped:
            border_color = QColor("#f59e0b")

        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(zone, 8.0, 8.0)

        self._draw_grid(painter, zone)
        self._draw_visualization_guides(painter, zone)
        self._draw_titles(painter, zone)
        self._draw_cursor(painter, zone, clamped_point, is_clipped)
        painter.end()

    def _draw_grid(self, painter: QPainter, zone: QRectF) -> None:
        """Draw the zone grid and centered x/y axes."""
        painter.save()
        grid_pen = QPen(QColor("#e2e8f0"), 1)
        axis_pen = QPen(QColor("#94a3b8"), 2)
        painter.setPen(grid_pen)
        for index in range(1, 4):
            offset = zone.width() * index / 4.0
            painter.drawLine(QLineF(zone.left() + offset, zone.top(), zone.left() + offset, zone.bottom()))
            painter.drawLine(QLineF(zone.left(), zone.top() + offset, zone.right(), zone.top() + offset))

        painter.setPen(axis_pen)
        painter.drawLine(QLineF(zone.center().x(), zone.top(), zone.center().x(), zone.bottom()))
        painter.drawLine(QLineF(zone.left(), zone.center().y(), zone.right(), zone.center().y()))
        painter.restore()

    def _draw_visualization_guides(self, painter: QPainter, zone: QRectF) -> None:
        """Draw all processing guides in signal-space coordinates."""
        painter.save()
        painter.setClipRect(zone)
        for guide in self._visualization_guides:
            if guide.shape == "axis_band":
                self._draw_axis_dead_zone_guide(painter, zone, guide.value[0])
            elif guide.shape == "axis_lines":
                self._draw_axis_saturation_guide(painter, zone, guide.value[0])
            elif guide.shape == "radius":
                self._draw_radius_guide(painter, zone, guide.value[0], guide.role)
            elif guide.shape == "bounds":
                self._draw_bounds_guide(painter, zone, guide.value[0], guide.value[1])
        painter.restore()

    def _draw_axis_dead_zone_guide(self, painter: QPainter, zone: QRectF, threshold: float) -> None:
        """Draw per-axis dead-zone bands for scalar dead-zone components."""
        if threshold <= 0.0:
            return
        painter.save()
        # Per-axis dead zones affect x and y independently, so they are bands.
        x_negative = self._signal_x_to_zone(-threshold, zone)
        x_positive = self._signal_x_to_zone(threshold, zone)
        y_negative = self._signal_y_to_zone(-threshold, zone)
        y_positive = self._signal_y_to_zone(threshold, zone)
        left = min(x_negative, x_positive)
        right = max(x_negative, x_positive)
        top = min(y_negative, y_positive)
        bottom = max(y_negative, y_positive)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(99, 102, 241, 28))
        painter.drawRect(QRectF(left, zone.top(), right - left, zone.height()))
        painter.drawRect(QRectF(zone.left(), top, zone.width(), bottom - top))

        pen = QPen(QColor(99, 102, 241, 150), 1.5)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        for x in (x_negative, x_positive):
            painter.drawLine(QLineF(x, zone.top(), x, zone.bottom()))
        for y in (y_negative, y_positive):
            painter.drawLine(QLineF(zone.left(), y, zone.right(), y))
        painter.restore()

    def _draw_axis_saturation_guide(self, painter: QPainter, zone: QRectF, limit: float) -> None:
        """Draw per-axis saturation boundaries."""
        if limit <= 0.0:
            return
        painter.save()
        x_negative = self._signal_x_to_zone(-limit, zone)
        x_positive = self._signal_x_to_zone(limit, zone)
        y_negative = self._signal_y_to_zone(-limit, zone)
        y_positive = self._signal_y_to_zone(limit, zone)

        pen = QPen(QColor("#f59e0b"), 2.0)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        for x in (x_negative, x_positive):
            painter.drawLine(QLineF(x, zone.top(), x, zone.bottom()))
        for y in (y_negative, y_positive):
            painter.drawLine(QLineF(zone.left(), y, zone.right(), y))
        painter.restore()

    def _draw_radius_guide(self, painter: QPainter, zone: QRectF, radius: float, role: str) -> None:
        """Draw a norm-based dead-zone or saturation radius."""
        if radius <= 0.0:
            return
        painter.save()
        # Different x/y scales make a signal-space circle appear as an ellipse.
        center_x = self._signal_x_to_zone(0.0, zone)
        center_y = self._signal_y_to_zone(0.0, zone)
        radius_x = abs(self._signal_x_to_zone(radius, zone) - center_x)
        radius_y = abs(self._signal_y_to_zone(radius, zone) - center_y)
        guide_rect = QRectF(center_x - radius_x, center_y - radius_y, radius_x * 2.0, radius_y * 2.0)

        if role == "dead_zone":
            painter.setBrush(QColor(99, 102, 241, 26))
            pen = QPen(QColor(99, 102, 241, 150), 1.5)
        else:
            painter.setBrush(Qt.NoBrush)
            pen = QPen(QColor("#f59e0b"), 2.0)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(guide_rect)
        painter.restore()

    def _draw_bounds_guide(self, painter: QPainter, zone: QRectF, lower: float, upper: float) -> None:
        """Draw a rectangular output clamp range."""
        painter.save()
        x_lower = self._signal_x_to_zone(lower, zone)
        x_upper = self._signal_x_to_zone(upper, zone)
        y_lower = self._signal_y_to_zone(lower, zone)
        y_upper = self._signal_y_to_zone(upper, zone)
        left = min(x_lower, x_upper)
        right = max(x_lower, x_upper)
        top = min(y_lower, y_upper)
        bottom = max(y_lower, y_upper)
        bounds_rect = QRectF(left, top, right - left, bottom - top)

        painter.setBrush(QColor(245, 158, 11, 18))
        pen = QPen(QColor("#f59e0b"), 2.0)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(bounds_rect)
        painter.restore()

    def _signal_x_to_zone(self, value: float, zone: QRectF) -> float:
        """Map a signal x value to a widget x coordinate."""
        point = self._scale.point_from_signal((value, 0.0), zone.width(), clamp_to_zone=False)
        return zone.left() + point[0]

    def _signal_y_to_zone(self, value: float, zone: QRectF) -> float:
        """Map a signal y value to a widget y coordinate."""
        point = self._scale.point_from_signal((0.0, value), zone.width(), clamp_to_zone=False)
        return zone.top() + point[1]

    def _draw_titles(self, painter: QPainter, zone: QRectF) -> None:
        """Draw the zone title and current signal value."""
        painter.save()
        title_font = QFont(self.font())
        title_font.setPointSize(12)
        title_font.setWeight(QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor("#0f172a"))
        painter.drawText(QRectF(18.0, 4.0, self.width() - 36.0, 24.0), Qt.AlignLeft, self._title)

        value_font = QFont(self.font())
        value_font.setPointSize(9)
        painter.setFont(value_font)
        painter.setPen(QColor("#475569"))
        value_text = f"x {self._signal[0]: .3f}    y {self._signal[1]: .3f}"
        painter.drawText(
            QRectF(zone.left(), zone.bottom() + 8.0, zone.width(), 24.0),
            Qt.AlignCenter,
            value_text,
        )
        painter.restore()

    def _draw_cursor(
        self,
        painter: QPainter,
        zone: QRectF,
        point: tuple[float, float],
        is_clipped: bool,
    ) -> None:
        """Draw the cursor marker, using amber when it is visually clipped."""
        painter.save()
        cursor_x = zone.left() + point[0]
        cursor_y = zone.top() + point[1]
        color = QColor("#f59e0b") if is_clipped else self._accent
        painter.setPen(QPen(color, 3))
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 46))
        painter.drawEllipse(QRectF(cursor_x - 10.0, cursor_y - 10.0, 20.0, 20.0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QRectF(cursor_x - 4.0, cursor_y - 4.0, 8.0, 8.0))
        painter.restore()


class SignalPlotWidget(QWidget):
    """Qt-painted live input/output plots for x and y."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._series = {
            "time": [],
            "input_x": [],
            "input_y": [],
            "output_x": [],
            "output_y": [],
        }
        self._scale = SignalScale()
        self.setMinimumHeight(310)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_history(self, history: SignalHistory, scale: SignalScale) -> None:
        """Replace plotted series from the rolling history."""
        self._series = history.series()
        self._scale = scale
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the two stacked x/y input-output plots."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#f8fafc"))

        outer = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        gap = 18.0
        plot_height = max(1.0, (outer.height() - gap) * 0.5)
        x_rect = QRectF(0.0, 0.0, outer.width(), plot_height)
        y_rect = QRectF(0.0, plot_height + gap, outer.width(), plot_height)

        self._draw_axis_plot(
            painter,
            x_rect,
            "x",
            self._series["input_x"],
            self._series["output_x"],
            self._scale.x_bounds,
        )
        self._draw_axis_plot(
            painter,
            y_rect,
            "y",
            self._series["input_y"],
            self._series["output_y"],
            self._scale.y_bounds,
            draw_time_label=True,
        )
        painter.end()

    def _draw_axis_plot(
        self,
        painter: QPainter,
        rect: QRectF,
        axis_label: str,
        input_values: list[float],
        output_values: list[float],
        bounds: tuple[float, float],
        draw_time_label: bool = False,
    ) -> None:
        """Draw one axis plot with input and output traces."""
        plot_rect = QRectF(rect.left() + 44.0, rect.top() + 12.0, rect.width() - 58.0, rect.height() - 34.0)
        if draw_time_label:
            plot_rect.setHeight(max(1.0, plot_rect.height() - 14.0))

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(plot_rect, 8.0, 8.0)
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(plot_rect, 8.0, 8.0)

        time_values = self._series["time"]
        if time_values:
            latest_time = time_values[-1]
            x_min = max(0.0, latest_time - 6.0)
            x_max = max(6.0, latest_time)
        else:
            x_min = 0.0
            x_max = 6.0
        y_min, y_max = self._axis_limits(input_values + output_values, bounds)

        self._draw_plot_grid(painter, plot_rect, x_min, x_max, y_min, y_max)
        self._draw_line(painter, plot_rect, time_values, input_values, x_min, x_max, y_min, y_max, QColor("#2563eb"), 1.7)
        self._draw_line(painter, plot_rect, time_values, output_values, x_min, x_max, y_min, y_max, QColor("#14b8a6"), 2.0)
        self._draw_plot_labels(painter, rect, plot_rect, axis_label, x_min, x_max, y_min, y_max, draw_time_label)
        painter.restore()

    def _draw_plot_grid(
        self,
        painter: QPainter,
        rect: QRectF,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        """Draw plot grid lines and the zero axis when visible."""
        painter.save()
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        for index in range(1, 4):
            x = rect.left() + rect.width() * index / 4.0
            y = rect.top() + rect.height() * index / 4.0
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))

        if y_min <= 0.0 <= y_max:
            zero_y = self._map_y(0.0, rect, y_min, y_max)
            painter.setPen(QPen(QColor("#94a3b8"), 1))
            painter.drawLine(QLineF(rect.left(), zero_y, rect.right(), zero_y))
        painter.restore()

    def _draw_plot_labels(
        self,
        painter: QPainter,
        outer_rect: QRectF,
        plot_rect: QRectF,
        axis_label: str,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        draw_time_label: bool,
    ) -> None:
        """Draw axis labels, tick labels, and the input/output legend."""
        painter.save()
        label_font = QFont(self.font())
        label_font.setPointSize(9)
        label_font.setWeight(QFont.DemiBold)
        painter.setFont(label_font)
        painter.setPen(QColor("#0f172a"))
        painter.drawText(QRectF(0.0, outer_rect.top() + 10.0, 36.0, 20.0), Qt.AlignCenter, axis_label)

        tick_font = QFont(self.font())
        tick_font.setPointSize(8)
        painter.setFont(tick_font)
        painter.setPen(QColor("#64748b"))
        painter.drawText(QRectF(4.0, plot_rect.top() - 2.0, 38.0, 16.0), Qt.AlignRight, f"{y_max:.2g}")
        painter.drawText(QRectF(4.0, plot_rect.bottom() - 14.0, 38.0, 16.0), Qt.AlignRight, f"{y_min:.2g}")
        painter.drawText(QRectF(plot_rect.left(), plot_rect.bottom() + 4.0, 56.0, 16.0), Qt.AlignLeft, f"{x_min:.1f}s")
        painter.drawText(QRectF(plot_rect.right() - 56.0, plot_rect.bottom() + 4.0, 56.0, 16.0), Qt.AlignRight, f"{x_max:.1f}s")

        legend_x = plot_rect.right() - 132.0
        legend_y = plot_rect.top() + 8.0
        self._draw_legend_item(painter, legend_x, legend_y, QColor("#2563eb"), "input")
        self._draw_legend_item(painter, legend_x + 64.0, legend_y, QColor("#14b8a6"), "output")

        if draw_time_label:
            painter.drawText(
                QRectF(plot_rect.left(), plot_rect.bottom() + 18.0, plot_rect.width(), 16.0),
                Qt.AlignCenter,
                "time",
            )
        painter.restore()

    def _draw_legend_item(
        self,
        painter: QPainter,
        x: float,
        y: float,
        color: QColor,
        text: str,
    ) -> None:
        """Draw one compact line legend item."""
        painter.save()
        painter.setPen(QPen(color, 2))
        painter.drawLine(QLineF(x, y + 7.0, x + 18.0, y + 7.0))
        painter.setPen(QColor("#64748b"))
        painter.drawText(QRectF(x + 22.0, y, 40.0, 16.0), Qt.AlignLeft, text)
        painter.restore()

    def _draw_line(
        self,
        painter: QPainter,
        rect: QRectF,
        time_values: list[float],
        values: list[float],
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        color: QColor,
        width: float,
    ) -> None:
        """Draw one clipped time-series line."""
        if len(time_values) < 2 or len(values) < 2:
            return
        painter.save()
        painter.setClipRect(rect)
        painter.setPen(QPen(color, width))
        points = [
            (
                self._map_x(time_value, rect, x_min, x_max),
                self._map_y(value, rect, y_min, y_max),
            )
            for time_value, value in zip(time_values, values)
            if time_value >= x_min
        ]
        for previous, current in zip(points, points[1:]):
            painter.drawLine(QLineF(previous[0], previous[1], current[0], current[1]))
        painter.restore()

    def _axis_limits(self, values: list[float], bounds: tuple[float, float]) -> tuple[float, float]:
        """Return padded y-axis limits that include configured signal bounds."""
        lower, upper = bounds
        plotted_values = values + [lower, upper, 0.0]
        data_lower = min(plotted_values)
        data_upper = max(plotted_values)
        if abs(data_upper - data_lower) < 1e-9:
            data_lower -= 1.0
            data_upper += 1.0
        padding = max((data_upper - data_lower) * 0.08, 0.05)
        return data_lower - padding, data_upper + padding

    def _map_x(self, value: float, rect: QRectF, x_min: float, x_max: float) -> float:
        """Map a plot timestamp to a local x coordinate."""
        if abs(x_max - x_min) < 1e-9:
            return rect.left()
        fraction = (value - x_min) / (x_max - x_min)
        return rect.left() + fraction * rect.width()

    def _map_y(self, value: float, rect: QRectF, y_min: float, y_max: float) -> float:
        """Map a plot signal value to a local y coordinate."""
        if abs(y_max - y_min) < 1e-9:
            return rect.center().y()
        fraction = (value - y_min) / (y_max - y_min)
        return rect.bottom() - fraction * rect.height()


class SignalProcessingTesterWindow(QMainWindow):
    """Main tester window."""

    def __init__(self):
        super().__init__()
        self.scale = SignalScale()
        self.pipeline = ProcessingPipeline(sample_rate_hz=SAMPLE_RATE_HZ)
        self.input_noise = InputNoiseGenerator()
        self.signal_flow = SignalTesterFlow(self.pipeline, self.input_noise)
        self.history = SignalHistory(max_seconds=6.0, sample_rate_hz=SAMPLE_RATE_HZ)
        self.raw_input_signal = (0.0, 0.0)
        self.noisy_input_signal = (0.0, 0.0)
        self.output_signal = (0.0, 0.0)
        self.scale_spin_boxes: dict[str, QDoubleSpinBox] = {}
        self.noise_enabled_box: QCheckBox | None = None
        self.noise_std_spin_box: QDoubleSpinBox | None = None
        self.block_list_layout: QVBoxLayout | None = None
        self.input_zone: SignalZoneWidget | None = None
        self.output_zone: SignalZoneWidget | None = None
        self.plot_widget: SignalPlotWidget | None = None
        self.timer = QTimer(self)

        self.setWindowTitle("Signal Processing Tester")
        self.resize(1380, 860)
        self._build_ui()
        self._apply_style()
        self._reset_processing(clear_history=True)

        self.timer.timeout.connect(self._tick)
        self.timer.start(SAMPLE_PERIOD_MS)

    def _build_ui(self) -> None:
        """Create the window layout and connect top-level controls."""
        central = QWidget()
        central.setObjectName("root")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 18, 20, 20)
        root_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title = QLabel("Signal Processing Tester")
        title.setObjectName("windowTitle")
        subtitle = QLabel("Interactive 2-D signal chain")
        subtitle.setObjectName("windowSubtitle")
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch(1)

        reset_button = QPushButton("Reset")
        reset_button.setObjectName("primaryButton")
        reset_button.clicked.connect(lambda: self._reset_processing(clear_history=True))
        header_layout.addWidget(reset_button)
        root_layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)
        root_layout.addLayout(body_layout, 1)

        self.input_zone = SignalZoneWidget("Input detection zone", interactive=True)
        self.input_zone.signal_changed.connect(self._handle_input_changed)
        body_layout.addWidget(self.input_zone, 1)

        center_panel = QFrame()
        center_panel.setObjectName("centerPanel")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(14)
        self.output_zone = SignalZoneWidget("Processed output zone", interactive=False)
        self.plot_widget = SignalPlotWidget()
        center_layout.addWidget(self.output_zone, 1)
        center_layout.addWidget(self.plot_widget, 1)
        body_layout.addWidget(center_panel, 2)

        body_layout.addWidget(self._build_parameter_panel(), 0)
        self.setCentralWidget(central)

    def _build_parameter_panel(self) -> QScrollArea:
        """Build the right-side scrollable parameter panel."""
        scroll_area = QScrollArea()
        scroll_area.setObjectName("parameterScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(360)
        scroll_area.setMaximumWidth(430)

        content = QWidget()
        content.setObjectName("parameterPanel")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        layout.addWidget(self._build_scale_group())
        layout.addWidget(self._build_noise_group())
        components_title = QLabel("Processing chain")
        components_title.setObjectName("sectionTitle")
        layout.addWidget(components_title)

        block_container = QWidget()
        self.block_list_layout = QVBoxLayout(block_container)
        self.block_list_layout.setContentsMargins(0, 0, 0, 0)
        self.block_list_layout.setSpacing(10)
        layout.addWidget(block_container)
        layout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))
        scroll_area.setWidget(content)

        self._rebuild_block_panel()
        return scroll_area

    def _build_scale_group(self) -> QGroupBox:
        """Build input scale controls."""
        group = QGroupBox("Input scale")
        group.setObjectName("scaleGroup")
        layout = QGridLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        fields = (
            ("x_min", "X min", self.scale.x_min),
            ("x_max", "X max", self.scale.x_max),
            ("y_min", "Y min", self.scale.y_min),
            ("y_max", "Y max", self.scale.y_max),
        )
        for row, (key, label_text, value) in enumerate(fields):
            label = QLabel(label_text)
            spin_box = QDoubleSpinBox()
            spin_box.setRange(-1000.0, 1000.0)
            spin_box.setDecimals(3)
            spin_box.setSingleStep(0.1)
            spin_box.setValue(value)
            spin_box.valueChanged.connect(self._handle_scale_changed)
            self.scale_spin_boxes[key] = spin_box
            layout.addWidget(label, row, 0)
            layout.addWidget(spin_box, row, 1)
        return group

    def _build_noise_group(self) -> QGroupBox:
        """Build input white-noise controls."""
        group = QGroupBox("Input noise")
        group.setObjectName("scaleGroup")
        layout = QGridLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.noise_enabled_box = QCheckBox("Enable")
        self.noise_enabled_box.setChecked(self.input_noise.enabled)
        self.noise_enabled_box.stateChanged.connect(self._handle_noise_enabled_changed)
        layout.addWidget(self.noise_enabled_box, 0, 0, 1, 2)

        std_label = QLabel("Std dev")
        self.noise_std_spin_box = QDoubleSpinBox()
        self.noise_std_spin_box.setRange(0.0, 1000.0)
        self.noise_std_spin_box.setDecimals(4)
        self.noise_std_spin_box.setSingleStep(0.01)
        self.noise_std_spin_box.setValue(self.input_noise.standard_deviation)
        self.noise_std_spin_box.valueChanged.connect(self._handle_noise_std_changed)
        layout.addWidget(std_label, 1, 0)
        layout.addWidget(self.noise_std_spin_box, 1, 1)
        return group

    def _rebuild_block_panel(self) -> None:
        """Recreate processing-block controls from the current chain order."""
        if self.block_list_layout is None:
            return
        while self.block_list_layout.count():
            item = self.block_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, block in enumerate(self.pipeline.blocks):
            self.block_list_layout.addWidget(self._build_block_card(index))

    def _build_block_card(self, index: int) -> QFrame:
        """Build one processing block card with toggle, reorder, and parameters."""
        block = self.pipeline.blocks[index]
        card = QFrame()
        card.setObjectName("componentCard")
        card.setToolTip(block.spec.description)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        enabled_box = QCheckBox()
        enabled_box.setChecked(block.enabled)
        enabled_box.stateChanged.connect(
            lambda state, block_index=index: self._set_block_enabled(block_index, state == Qt.Checked)
        )
        header.addWidget(enabled_box)

        title = QLabel(block.spec.title)
        title.setObjectName("componentTitle")
        header.addWidget(title, 1)

        up_button = QPushButton()
        up_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        up_button.setToolTip("Move earlier")
        up_button.setEnabled(index > 0)
        up_button.clicked.connect(lambda checked=False, block_index=index: self._move_block(block_index, -1))
        header.addWidget(up_button)

        down_button = QPushButton()
        down_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        down_button.setToolTip("Move later")
        down_button.setEnabled(index < len(self.pipeline.blocks) - 1)
        down_button.clicked.connect(lambda checked=False, block_index=index: self._move_block(block_index, 1))
        header.addWidget(down_button)
        layout.addLayout(header)

        for parameter in block.spec.parameters:
            row = QHBoxLayout()
            label = QLabel(parameter.label)
            label.setObjectName("parameterLabel")
            spin_box = QDoubleSpinBox()
            spin_box.setRange(parameter.minimum, parameter.maximum)
            spin_box.setDecimals(parameter.decimals)
            spin_box.setSingleStep(parameter.step)
            spin_box.setValue(block.parameters[parameter.key])
            spin_box.valueChanged.connect(
                lambda value, block_index=index, key=parameter.key: self._set_block_parameter(
                    block_index,
                    key,
                    value,
                )
            )
            row.addWidget(label, 1)
            row.addWidget(spin_box)
            layout.addLayout(row)
        return card

    def _handle_input_changed(self, signal: tuple[float, float]) -> None:
        """Store raw mouse input from the detection zone."""
        self.raw_input_signal = (float(signal[0]), float(signal[1]))

    def _handle_scale_changed(self) -> None:
        """Apply edited signal scale and reset state/history."""
        self.scale = SignalScale(
            self.scale_spin_boxes["x_min"].value(),
            self.scale_spin_boxes["x_max"].value(),
            self.scale_spin_boxes["y_min"].value(),
            self.scale_spin_boxes["y_max"].value(),
        )
        if self.input_zone is not None:
            self.input_zone.set_scale(self.scale)
        if self.output_zone is not None:
            self.output_zone.set_scale(self.scale)
        self._reset_processing(clear_history=True)

    def _handle_noise_enabled_changed(self, state: int) -> None:
        """Toggle input noise and reset state/history."""
        self.input_noise.set_enabled(state == Qt.Checked)
        self._reset_processing(clear_history=True)

    def _handle_noise_std_changed(self, value: float) -> None:
        """Set input-noise standard deviation and reset state/history."""
        self.input_noise.set_standard_deviation(value)
        self._reset_processing(clear_history=True)

    def _set_block_enabled(self, index: int, enabled: bool) -> None:
        """Toggle one processing block and reset state/history."""
        self.pipeline.set_block_enabled(index, enabled)
        self._reset_processing(clear_history=True)

    def _set_block_parameter(self, index: int, key: str, value: float) -> None:
        """Update one block parameter and reset state/history."""
        self.pipeline.update_block_parameter(index, key, value)
        self._reset_processing(clear_history=True)

    def _move_block(self, index: int, offset: int) -> None:
        """Move a processing block earlier or later in the chain."""
        destination = index + offset
        if not 0 <= destination < len(self.pipeline.blocks):
            return
        self.pipeline.move_block(index, destination)
        self._reset_processing(clear_history=True)
        self._rebuild_block_panel()

    def _reset_processing(self, clear_history: bool) -> None:
        """Reset signal state, processing state, guides, and optionally history."""
        self.pipeline.reset()
        self.raw_input_signal = (0.0, 0.0)
        self.noisy_input_signal = (0.0, 0.0)
        self.output_signal = (0.0, 0.0)
        if clear_history:
            self.history.clear()
        if self.input_zone is not None:
            self.input_zone.set_scale(self.scale)
            self.input_zone.set_signal(self.raw_input_signal)
        if self.output_zone is not None:
            self.output_zone.set_scale(self.scale)
            self.output_zone.set_signal(self.output_signal)
        self._update_zone_visualization_guides()
        if self.plot_widget is not None:
            self.plot_widget.update_history(self.history, self.scale)

    def _update_zone_visualization_guides(self) -> None:
        """Refresh dead-zone and saturation guides in both square zones."""
        guides = collect_signal_visualization_guides(self.pipeline.blocks)
        if self.input_zone is not None:
            self.input_zone.set_visualization_guides(guides)
        if self.output_zone is not None:
            self.output_zone.set_visualization_guides(guides)

    def _tick(self) -> None:
        """Advance the live tester by one sample period."""
        self.noisy_input_signal, self.output_signal = self.signal_flow.process(self.raw_input_signal)
        self.history.append(
            self.pipeline.timestamp_sec,
            self.noisy_input_signal,
            self.output_signal,
        )
        if self.output_zone is not None:
            self.output_zone.set_signal(self.output_signal)
        if self.plot_widget is not None:
            self.plot_widget.update_history(self.history, self.scale)

    def _apply_style(self) -> None:
        """Apply the tester window stylesheet."""
        self.setStyleSheet(
            """
            QWidget#root {
              background: #f8fafc;
              color: #0f172a;
              font-family: Inter, Roboto, Ubuntu, Arial, sans-serif;
            }
            QLabel#windowTitle {
              font-size: 24px;
              font-weight: 700;
              color: #0f172a;
            }
            QLabel#windowSubtitle {
              font-size: 12px;
              color: #64748b;
            }
            QLabel#sectionTitle {
              font-size: 13px;
              font-weight: 700;
              color: #334155;
            }
            QScrollArea#parameterScroll {
              border: 1px solid #dbe3ee;
              border-radius: 8px;
              background: #ffffff;
            }
            QWidget#parameterPanel {
              background: #ffffff;
            }
            QGroupBox#scaleGroup {
              border: 1px solid #dbe3ee;
              border-radius: 8px;
              margin-top: 8px;
              font-weight: 700;
              color: #334155;
              background: #ffffff;
            }
            QGroupBox#scaleGroup::title {
              subcontrol-origin: margin;
              left: 10px;
              padding: 0 4px;
            }
            QFrame#componentCard {
              border: 1px solid #e2e8f0;
              border-radius: 8px;
              background: #f8fafc;
            }
            QLabel#componentTitle {
              font-size: 13px;
              font-weight: 700;
              color: #0f172a;
            }
            QLabel#parameterLabel {
              color: #475569;
              font-size: 11px;
            }
            QDoubleSpinBox {
              min-height: 28px;
              border: 1px solid #cbd5e1;
              border-radius: 6px;
              padding: 2px 6px;
              background: #ffffff;
              selection-background-color: #2563eb;
            }
            QPushButton {
              min-height: 28px;
              border: 1px solid #cbd5e1;
              border-radius: 6px;
              padding: 4px 8px;
              background: #ffffff;
              color: #0f172a;
            }
            QPushButton:hover {
              background: #f1f5f9;
              border-color: #94a3b8;
            }
            QPushButton:disabled {
              color: #94a3b8;
              background: #f8fafc;
            }
            QPushButton#primaryButton {
              background: #0f172a;
              color: #ffffff;
              border-color: #0f172a;
              padding-left: 16px;
              padding-right: 16px;
              font-weight: 700;
            }
            QPushButton#primaryButton:hover {
              background: #1e293b;
            }
            QCheckBox::indicator {
              width: 16px;
              height: 16px;
            }
            """
        )


def main(argv: list[str] | None = None) -> int:
    """Run the standalone signal-processing tester application."""
    app_argv = sys.argv if argv is None else argv
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication.instance() or QApplication(app_argv)
    app.setApplicationName("Signal Processing Tester")
    window = SignalProcessingTesterWindow()
    window.show()
    if hasattr(app, "exec"):
        return int(app.exec())
    return int(app.exec_())


if __name__ == "__main__":
    raise SystemExit(main())
