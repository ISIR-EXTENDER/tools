import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from joint_position_interpolator.msg import JointPositionCommand

import pickle
import os
import threading
import sys
import termios
import tty

original_terminal_settings = termios.tcgetattr(sys.stdin)

class JointPositionReplay(Node):
    def __init__(self):
        super().__init__('joint_position_replay')

        self.declare_parameter('input_file', 'joint_position.pkl')
        self.declare_parameter('state_publish_topic', '/replay/joint_states')
        self.declare_parameter("send_position_topic", "/joint_position_desired")


        self.input_file = self.get_parameter('input_file').get_parameter_value().string_value
        state_publish_topic = self.get_parameter('state_publish_topic').get_parameter_value().string_value
        position_topic = self.get_parameter("send_position_topic").get_parameter_value().string_value
        
        self.latest_joint_state = None
        self.state_subscriber = self.create_subscription(
            JointState, '/joint_states', self.joint_state_callback, 10)
        self.state_publisher = self.create_publisher(JointState, state_publish_topic, 10)
        self.position_publisher = self.create_publisher(JointPositionCommand, position_topic, 10)
        self.current_index = -1
        self.publish = False

        self.input_thread = threading.Thread(target=self.keyboard_input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()
        
        self.load_poses()

    def load_poses(self):
        file_path = os.path.join(os.getcwd(), self.input_file)
        self.get_logger().info(f"Loading trajectory from {file_path}")
        try:
            with open(file_path, 'rb') as file:
                recorded_data = pickle.load(file)
            self.positions = recorded_data["joint_positions"]
            self.get_logger().info(f"Successfully loaded.")
        except FileNotFoundError:
            self.get_logger().error(f"File not found: {file_path}. Shutting down.")
            sys.exit(1)
        except Exception as e:
            self.get_logger().error(f"Failed to load trajectory: {e}. Shutting down.")
            sys.exit(1)

    def keyboard_input_loop(self):
        self.print_instructions()
        while rclpy.ok():
            key = self.get_key()
            if key == 'n':
                self.current_index += 1
                self.send_next_point()
                self.nb_state = 0
                self.publish = False
            elif key == 'r':
                self.current_index = -1
                self.get_logger().info("Reset to index 0.")
            elif key == "p":
                self.publish = True
            elif key == 'q' or key == 'Q':
                self.get_logger().info("'q' pressed, shutting down.")
                rclpy.shutdown()
                break

    def send_next_point(self):
        if self.current_index >= len(self.positions):
            self.get_logger().warn("End of trajectory list reached.")
            return
        
        # 1. Get the target positions
        target_position = self.positions[self.current_index]
        self.get_logger().info(f"{target_position}")

        self.position_publisher.publish(target_position)

    def print_instructions(self):
        self.get_logger().info(
            "\n"
            "------------------------------------\n"
            "| Interactive Trajectory Replayer    |\n"
            "------------------------------------\n"
            "| 'n' -> Move to NEXT waypoint     |\n"
            "| 'p' -> PUBLISH current state     |\n"
            "| 'q' -> Quit                      |\n"
            "------------------------------------"
        )

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
        return ch


    def joint_state_callback(self, msg):
        self.latest_joint_state = msg
        if self.publish is True and self.nb_state <= 100:
            self.state_publisher.publish(msg)
            self.nb_state += 1


def main(args=None):
    try:
        rclpy.init(args=args)
        stepper_node = JointPositionReplay()
        rclpy.spin(stepper_node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()