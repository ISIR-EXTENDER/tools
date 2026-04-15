# Dynamic Parameters Identification for Robot Manipulators

A ROS2 package for identifying dynamic parameters (masses, centers of mass, inertias, friction coefficients) of robot manipulators. Uses  least-squares estimation regularization, signal processing, to extract model parameters from trajectory and torque measurements.

## Overview

This package implements a complete identification pipeline for extracting robot dynamics parameters from experimental data. It both generates the sinusoids trajectories and then allows to process recorded data for parameters identification.

## Installation & Prerequisites

### System Requirements

```bash
# Install Python dependencies
sudo apt install python3-pinocchio python3-scipy python3-matplotlib

# Or using pip
pip install pinocchio scipy numpy matplotlib
```

### Robot Requirements

Your robot must provide:
- **Joint state topic**: `/joint_states` (sensor_msgs/JointState)
- **Joint trajectory controller**: accepting goal_configurations via action interface
- **URDF file**: with all link masses and inertias defined (or reasonable defaults)
- **Kinematics**: forward kinematics computation available (via Pinocchio)

## Quick Start

### Step 1: Generate Excitation Trajectory

Launch the trajectory generator to create multi-frequency sinusoidal motions across all joints:

```bash
ros2 launch dynamic_parameters_identification joint_sine_trajectory.launch.py
```

### Step 2: Run Parameter Identification

In a new terminal, launch the identification node to collect sensor data and compute parameters:

```bash
ros2 launch dynamic_parameters_identification parameters_identification_robust.launch.py
```

## Package Structure

```
dynamic_parameters_identification/
├── parameters_identification.py           # Simplified identification interface
├── joints_sinusoids.py                    # Multi-frequency trajectory generator
├── bringup/
│   ├── config/                            # Configuration files
│   │   ├── parameters_identification_params.yaml
│   │   └── joint_sine_trajectory_params.yaml
│   └── launch/                            # ROS2 launch files
│       ├── parameters_identification.launch.py
│       └── joint_sine_trajectory.launch.py
└── README.md                              # This file
```

## License

Part of Extender Workspace (ROS2 Humble)
