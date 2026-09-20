#!/usr/bin/env python3
"""Bridge RViz '2D Pose Estimate' (/initialpose) into Gazebo model pose."""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from gazebo_msgs.msg import EntityState
from gazebo_msgs.srv import SetEntityState


class InitialPoseToGazebo(Node):
    def __init__(self):
        super().__init__('initialpose_to_gazebo')
        self.entity_name = self.declare_parameter(
            'entity_name', 'titan_warehouse_amr').get_parameter_value().string_value
        self._cli = self.create_client(SetEntityState, '/set_entity_state')
        self._cli_alt = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.create_subscription(
            PoseWithCovarianceStamped, '/initialpose', self._on_pose, 10)
        self.get_logger().info(
            f'Listening on /initialpose → Gazebo entity "{self.entity_name}"')

    def _on_pose(self, msg: PoseWithCovarianceStamped):
        cli = self._cli if self._cli.service_is_ready() else self._cli_alt
        if not cli.service_is_ready():
            if not cli.wait_for_service(timeout_sec=1.0):
                self.get_logger().warn('Gazebo set_entity_state service not available')
                return

        req = SetEntityState.Request()
        req.state = EntityState()
        req.state.name = self.entity_name
        req.state.pose = msg.pose.pose
        # Keep wheels on the ground
        if req.state.pose.position.z < 0.05:
            req.state.pose.position.z = 0.08
        req.state.twist.linear.x = 0.0
        req.state.twist.linear.y = 0.0
        req.state.twist.linear.z = 0.0
        req.state.twist.angular.x = 0.0
        req.state.twist.angular.y = 0.0
        req.state.twist.angular.z = 0.0
        req.state.reference_frame = 'world'

        future = cli.call_async(req)

        def _done(fut):
            try:
                res = fut.result()
                if res.success:
                    self.get_logger().info(
                        f'Gazebo pose set to '
                        f'({req.state.pose.position.x:.2f}, {req.state.pose.position.y:.2f})')
                else:
                    self.get_logger().warn(f'set_entity_state failed: {res.status_message}')
            except Exception as exc:  # noqa: BLE001
                self.get_logger().error(f'set_entity_state call failed: {exc}')

        future.add_done_callback(_done)


def main():
    rclpy.init()
    node = InitialPoseToGazebo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
