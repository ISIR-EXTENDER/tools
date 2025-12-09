# Replay Joint Positions

This ros2 package allows to save joint positions and then replay them, by using the joint position interpolator controller or any controller that accepts the message `joint_position_interpolator/JointPositionCommand`.
There's two nodes : 
- `save_joint_positions` 
- `replay_joint_positions`

## `save_joint_positions`

This node allows to save joint positions. It uses keyboard input, and subscribe to the topic `/joint_states` to get access to the joint positions. 
When the user is done recording positions, it saves them in a pickle file.
```
ros2 run replay_joint_positions save_joint_positions --ros-args --params-file $(ros2 pkg prefix replay_joint_positions)/share/replay_joint_positions/config/save_config.yaml
```

## `replay_joint_positions`

This node reads a file, where joint positions are stored. It then sends them on the topic `/desired_joint_position` for a controller to pick up. It can then forward the topic `/joint_states` to the topic `/replay/joint_states` for a 100 timestamps.
```
ros2 run replay_joint_positions replay_joint_positions --ros-args --params-file $(ros2 pkg prefix replay_joint_positions)/share/replay_joint_positions/config/replay_config.yaml
```