# signal_processing

Reusable signal-processing helpers for the workspace.

This package provides both:

- C++ headers and a small exported library for controller-side use
- A pure-Python module for tooling and Python nodes

## Build

Build this package from the workspace root, not from the package directory:

```bash
cd /path/to/ros_workspace
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

The first version includes:

- scalar, vector, and conjoint velocity-twist saturation helpers
- dead-zone helpers
- one euro filtering
- first-order low-pass filtering helpers

## Filtering advice: 
Go to https://gery.casiez.net/1euro/InteractiveDemo/ to have insights on the compared behaviour of usual filters (and the superiority of one euro filter...)


The generic `limitVelocityTwistNorm` helper accepts any copyable command with Eigen-like
`linear` and `angular` fields. It enforces enabled norm limits with one shared scale, preserving
the relationship between both parts without coupling this package to a ROS command type.

The package stays ROS-agnostic at the algorithm layer so downstream packages can adapt the outputs to their own message types.
