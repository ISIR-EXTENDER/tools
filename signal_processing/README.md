# signal_processing

Reusable signal-processing helpers for the workspace.

This package provides both:

- C++ headers and a small exported library for controller-side use
- A pure-Python module for tooling and Python nodes

## Build

Build this package from the workspace root, not from the package directory:

```bash
cd /home/emoullet/dev/extender_workspace
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install --packages-select signal_processing
source install/setup.bash
```

If your shell is already inside `src/`, move one level up first:

```bash
cd ..
colcon build --symlink-install --packages-select signal_processing
```

Run the package tests with:

```bash
colcon test --packages-select signal_processing
colcon test-result --verbose
```

If a symlink-install build fails because an existing Python package path is a directory, clean the stale package build artifact and rebuild:

```bash
rm -rf build/signal_processing/ament_cmake_python/signal_processing/signal_processing
colcon build --symlink-install --packages-select signal_processing
```

## Interactive tester

The package installs a desktop tester for exploring the processing helpers on a live 2-D signal:

```bash
cd /home/emoullet/dev/extender_workspace
source install/setup.bash
ros2 run signal_processing signal_processing_tester
```

The tester window uses a square input zone on the left. Click and drag inside the zone to generate a centered, y-up input signal: right is positive x, up is positive y, and release recenters the raw input at zero. The current signal scale is controlled from the right panel with `X min`, `X max`, `Y min`, and `Y max`; these values change the signal range at the zone limits without changing the display size.

The middle panel shows the processed output in a matching square zone and two rolling time plots for x and y. The plotted input signal is the signal entering the processing chain. If input noise is enabled, the raw cursor remains visually stable, while the plotted input and processing chain receive the noisy signal.

The right panel contains:

- input scale controls
- optional Gaussian white noise on the input signal, configured by standard deviation in signal units
- a reorderable processing chain with enable toggles and live parameters for each component
- a reset button that clears history, recenters the signal, and resets stateful filters

Dead-zone and saturation/limit components also draw guides in both square zones:

- purple bands or circles show dead-zone regions
- amber dashed lines, rectangles, or circles show saturation and limiting boundaries

The tester is launched through a small static wrapper before Python starts. This keeps the tool usable from shells where Snap runtime paths have leaked into `LD_LIBRARY_PATH`.

The first version includes:

- one euro filtering
- scalar and vector saturation helpers
- dead-zone helpers
- first-order low-pass filtering helpers

The package stays ROS-agnostic at the algorithm layer so downstream packages can adapt the outputs to their own message types.
