import os
import numpy as np
import pinocchio as pin
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import matplotlib.pyplot as plt

class ParametersIdentification(Node):
    def __init__(self):
        super().__init__('parameters_identification')
        
        # Parameters
        self.declare_parameter('joint_names', [f'joint_{i+1}' for i in range(7)])
        self.declare_parameter('urdf_path', '')
        self.declare_parameter('max_samples', 12000) 
        self.declare_parameter('downsample_factor', 10)
        # --- New parameter for WLS ---
        self.declare_parameter('wls_epsilon', 1e-4, 
            description="Small value to prevent division by zero in weights. Higher values flatten the weights.")

        self.joint_names = self.get_parameter('joint_names').value
        self.urdf_path = self.get_parameter('urdf_path').value
        self.max_samples = self.get_parameter('max_samples').value
        self.downsample_factor = self.get_parameter('downsample_factor').value
        self.wls_epsilon = self.get_parameter('wls_epsilon').value

        # Load Pinocchio Model
        if not os.path.exists(self.urdf_path):
            self.get_logger().error(f"URDF path invalid: {self.urdf_path}")
            rclpy.shutdown()
            return
        
        self.model = pin.buildModelFromUrdf(self.urdf_path)
        self.data = self.model.createData()
        self.nv = self.model.nv
        
        # Buffers
        self.q_buffer = []
        self.tau_buffer = []
        self.time_buffer = []
        self.is_collecting = True

        self.subscription = self.create_subscription(
            JointState, '/joint_states', self.joint_state_callback, 10)
        
        self.get_logger().info(f"Node started. Collecting {self.max_samples} samples...")

    def joint_state_callback(self, msg: JointState):
        if not self.is_collecting:
            return

        try:
            # Map joint names to correct indices
            msg_name_to_idx = {name: i for i, name in enumerate(msg.name)}
            target_indices = [msg_name_to_idx[name] for name in self.joint_names]
            
            self.q_buffer.append([msg.position[i] for i in target_indices])
            self.tau_buffer.append([msg.effort[i] for i in target_indices])
            self.time_buffer.append(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)
        except (KeyError, IndexError):
            self.get_logger().warn("Could not find all joint names in JointState message. Skipping.", throttle_duration_sec=5)
            return

        if len(self.q_buffer) >= self.max_samples:
            self.is_collecting = False
            self.get_logger().info("Collection complete. Processing...")
            self.process_and_solve()

    def process_and_solve(self):
        Q = np.array(self.q_buffer)[::self.downsample_factor]
        Tau = np.array(self.tau_buffer)[::self.downsample_factor]
        T = np.array(self.time_buffer)[::self.downsample_factor]
        dt = np.mean(np.diff(T))
        num_samples = Q.shape[0]

        v = np.gradient(Q, dt, axis=0)
        a = np.gradient(v, dt, axis=0)
        
        num_model_params = 10 * self.nv 
        num_friction_params = 2 * self.nv
        total_params = num_model_params + num_friction_params

        Y = np.zeros((num_samples * self.nv, total_params))
        tau_vec = Tau.flatten()
        weights = np.zeros(num_samples * self.nv)

        for i in range(num_samples):
            Yi_pin = pin.computeJointTorqueRegressor(self.model, self.data, Q[i], v[i], a[i])
            Yi_friction = np.hstack([np.diag(v[i]), np.diag(np.sign(v[i]))])
            
            Yi_full = np.hstack([Yi_pin, Yi_friction])
            Y[i*self.nv : (i+1)*self.nv, :] = Yi_full

            v_norm_sq = np.linalg.norm(v[i])**2
            weight_i = 1.0 / (v_norm_sq + self.wls_epsilon)
            weights[i*self.nv : (i+1)*self.nv] = weight_i

        W = np.diag(weights)
        Y_w = np.dot(W, Y)
        tau_w = np.dot(W, tau_vec)

        theta, residuals, rank, s = np.linalg.lstsq(Y_w, tau_w, rcond=1e-4)

        self.get_logger().info(f"Identification complete. Matrix rank: {rank}/{Y.shape[1]}")
        self.print_parameters(theta)
        
        # Predict Torques for Validation
        tau_est_vec = Y @ theta
        tau_est = tau_est_vec.reshape(num_samples, self.nv)
        self.plot_results(T, Tau, tau_est)

    def print_parameters(self, theta):
        self.get_logger().info("--- Identified Parameters ---")
        friction_start_idx = 10 * self.nv

        for i in range(self.nv):
            params = theta[i*10 : (i+1)*10]
            mass, mcx, mcy, mcz = params[0], params[1], params[2], params[3]
            
            # Friction params are at the end of the theta vector
            fv = theta[friction_start_idx + i]
            fc = theta[friction_start_idx + self.nv + i]

            joint_name = self.model.names[i+1] # Pinocchio names are 1-indexed
            self.get_logger().info(f"Joint: {joint_name}")
            self.get_logger().info(f"  Mass:    {mass:8.4f} kg")
            self.get_logger().info(f"  mc:      [{mcx:8.4f}, {mcy:8.4f}, {mcz:8.4f}] kg*m")
            self.get_logger().info(f"  Friction: Viscous={fv:8.4f}, Coulomb={fc:8.4f}")
        self.get_logger().info("-" * 30)

    def plot_results(self, t, tau_meas, tau_est):
        fig, axes = plt.subplots(self.nv, 1, figsize=(12, 2 * self.nv), sharex=True)
        if self.nv == 1: axes = [axes]
        
        for i in range(self.nv):
            axes[i].plot(t, tau_meas[:, i], 'r.', label='Measured', markersize=2, alpha=0.5)
            axes[i].plot(t, tau_est[:, i], 'b-', label='Identified Model')
            axes[i].set_ylabel(f'Joint {i+1} [Nm]')
            axes[i].legend()
            axes[i].grid(True)
        
        axes[-1].set_xlabel('Time (s)')
        fig.suptitle('Joint Torque Identification: Measured vs. Predicted')
        plt.tight_layout()
        plt.show()

def main(args=None):
    rclpy.init(args=args)
    node = ParametersIdentification()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()