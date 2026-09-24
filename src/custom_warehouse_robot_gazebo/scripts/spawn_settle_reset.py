#!/usr/bin/env python3
"""After Gazebo spawn, wait for physics settle then snap the robot back to the
intended pose with zero twist. Stops the post-spawn roll from impact/casters."""
import math
import time

import rclpy
from gazebo_msgs.msg import EntityState
from gazebo_msgs.srv import SetEntityState
from rclpy.node import Node


class SettleReset(Node):
    def __init__(self):
        super().__init__('spawn_settle_reset')
        self.declare_parameter('entity', 'titan_warehouse_amr')
        self.declare_parameter('x', 0.0)
        self.declare_parameter('y', -5.0)
        self.declare_parameter('z', 0.05)
        self.declare_parameter('yaw', 0.0)
        self.declare_parameter('delay', 3.0)
        self._cli = self.create_client(SetEntityState, '/set_entity_state')
        self._done = False
        self._t0 = time.monotonic()
        self.create_timer(0.2, self._tick)

    def _tick(self):
        if self._done:
            return
        delay = float(self.get_parameter('delay').value)
        if time.monotonic() - self._t0 < delay:
            return
        if not self._cli.service_is_ready():
            return
        yaw = float(self.get_parameter('yaw').value)
        st = EntityState()
        st.name = str(self.get_parameter('entity').value)
        st.reference_frame = 'world'
        st.pose.position.x = float(self.get_parameter('x').value)
        st.pose.position.y = float(self.get_parameter('y').value)
        st.pose.position.z = float(self.get_parameter('z').value)
        st.pose.orientation.z = math.sin(yaw * 0.5)
        st.pose.orientation.w = math.cos(yaw * 0.5)
        req = SetEntityState.Request()
        req.state = st
        fut = self._cli.call_async(req)

        def _done(f):
            ok = False
            try:
                ok = bool(f.result().success)
            except Exception:  # noqa: BLE001
                ok = False
            self.get_logger().info(
                f'spawn settle reset → ({st.pose.position.x:.2f},'
                f'{st.pose.position.y:.2f}) success={ok}'
            )
            self._done = True
            # leave process running idle so launch doesn't respawn it
            self.create_timer(3600.0, lambda: None)

        fut.add_done_callback(_done)


def main():
    rclpy.init()
    node = SettleReset()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
