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

- one euro filtering
- scalar and vector saturation helpers
- dead-zone helpers
- first-order low-pass filtering helpers

The package stays ROS-agnostic at the algorithm layer so downstream packages can adapt the outputs to their own message types.
