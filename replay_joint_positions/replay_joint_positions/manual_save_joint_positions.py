import sys, termios, tty, os
import threading

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from joint_position_interpolator.msg import JointPositionCommand


import pickle as pkl

# A dictionary to hold the settings for the terminal
original_terminal_settings = termios.tcgetattr(sys.stdin)

class JointPositionSaver(Node):
    def __init__(self):
        super().__init__("joint_position_saver")

        self.declare_parameter('topic_to_record', '/joint_states')
        self.declare_parameter("joint_names", ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"])
        self.declare_parameter("filename", "joint_position")
        
        topic_name = self.get_parameter("topic_to_record").get_parameter_value().string_value
        self.joint_names = self.get_parameter("joint_names").value 
        self.filename = self.get_parameter("filename").get_parameter_value().string_value

        self.recorded_data = {'joint_positions': []}
        self.data_lock = threading.Lock()
        self.nb_pause = 0
        self.sub = self.create_subscription(
            JointState,
            topic_name,
            self.joint_state_callback,
            10)
        
        # Start the keyboard input thread
        self.input_thread = threading.Thread(target=self.keyboard_input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()

    def keyboard_input_loop(self):
        while rclpy.ok():
            key = self.get_key()
            if key == '\r':  # Enter key
                self.record_current_position()
            elif key == 'q' or key == 'Q':
                self.get_logger().info("'q' pressed, shutting down and saving.")
                rclpy.shutdown()
                break

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
        return ch
    
    def joint_state_callback(self, msg):
        with self.data_lock:
            self.latest_joint_state = msg

    def record_current_position(self):
        with self.data_lock:
            if self.latest_joint_state is None:
                self.get_logger().warn("No pose received yet. Cannot record.")
                return
            else:
                msg = JointPositionCommand()
                msg.joint_names = self.joint_names
                for n in self.joint_names:
                    index = self.latest_joint_state.name.index(n)
                    msg.desired_position.append(self.latest_joint_state.position[index])

                self.recorded_data["joint_positions"].append(msg)
                self.nb_pause += 1
                self.get_logger().info(f"Pose #{self.nb_pause} recorded!")
            

    def save_data(self):
        if not self.recorded_data['joint_positions']:
            self.get_logger().warn("No data was recorded, not saving file.")
            return
            
        file_path = os.path.join(os.getcwd(), self.filename + '.pkl')
        self.get_logger().info(f"Saving {len(self.recorded_data['joint_positions'])} cartesian poses to {file_path}")
        with open(file_path, 'wb') as file:
            pkl.dump(self.recorded_data, file)
        self.get_logger().info("Data saved successfully.")

def main(args=None):
    rclpy.init(args=args)
    joint_state_recorder = JointPositionSaver()
    if not rclpy.ok():
        return
    try:
        rclpy.spin(joint_state_recorder)
    except KeyboardInterrupt:
        # Fallback if Ctrl+C is used
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
        if rclpy.ok(): 
             joint_state_recorder.get_logger().info("Ctrl+C detected, shutting down.")
             joint_state_recorder.destroy_node()
             rclpy.shutdown()
        joint_state_recorder.save_data()

if __name__ == '__main__':
    main()