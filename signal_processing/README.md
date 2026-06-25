# signal_processing

Reusable signal-processing helpers for the workspace.

This package provides both:

- C++ headers and a small exported library for controller-side use
- A pure-Python module for tooling and Python nodes

The first version includes:

- one euro filtering
- scalar and vector saturation helpers
- dead-zone helpers
- first-order low-pass filtering helpers

The package stays ROS-agnostic at the algorithm layer so downstream packages can adapt the outputs to their own message types.