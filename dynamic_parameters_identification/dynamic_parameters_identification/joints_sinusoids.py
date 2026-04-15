import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import math

class MultiFreqSinePublisher(Node):
    def __init__(self):
        super().__init__('multi_freq_sine_publisher')
        
        # Topic name for the trajectory controller
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/joint_trajectory_controller/joint_trajectory', 
            10
        )
        
        self.declare_parameter('joint_names', [f'joint_{i+1}' for i in range(7)])
        self.declare_parameter('frequencies', [0.1, 0.13, 0.22, 0.2, 0.18, 0.08, 0.15])
        self.declare_parameter('amplitudes', [0.6, 0.5, 0.6, 0.5, 0.7, 0.7, 0.5])
        self.declare_parameter('total_duration', 120.0)
        self.declare_parameter('sampling_rate', 10.0)
        
        self.joint_names = self.get_parameter('joint_names').value
        self.base_freqs = self.get_parameter('frequencies').value
        self.amplitudes = self.get_parameter('amplitudes').value
        self.total_duration = self.get_parameter('total_duration').value
        self.sampling_rate = self.get_parameter('sampling_rate').value

        # Start the process
        self.timer = self.create_timer(1.0, self.publish_trajectory)
        self.get_logger().info('Node started. Waiting 1s to publish multi-frequency trajectory...')

    def publish_trajectory(self):
        self.timer.cancel() # Only run once

        msg = JointTrajectory()
        msg.joint_names = self.joint_names
        
        num_points = int(self.total_duration * self.sampling_rate)

        for i in range(num_points + 1):
            t = i / self.sampling_rate
            point = JointTrajectoryPoint()
            
            positions = []
            velocities = []

            # Calculate individual sine wave for each joint
            for j in range(len(self.joint_names)):
                f = self.frequencies[j]
                a = self.amplitudes[j]
                
                # Position: p(t) = A * sin(2 * pi * f * t)
                pos = a * math.sin(2 * math.pi * f * t)
                # Velocity: v(t) = A * 2 * pi * f * cos(2 * pi * f * t)
                vel = a * 2 * math.pi * f * math.cos(2 * math.pi * f * t)
                
                positions.append(pos)
                velocities.append(vel)

            point.positions = positions
            point.velocities = velocities
            point.time_from_start = Duration(
                sec=int(t), 
                nanosec=int((t - int(t)) * 1e9)
            )
            
            msg.points.append(point)

        self.get_logger().info(f'Sending {len(msg.points)} waypoints...')
        self.publisher_.publish(msg)
        self.get_logger().info('Trajectory Published!')

def main():
    rclpy.init()
    node = MultiFreqSinePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()