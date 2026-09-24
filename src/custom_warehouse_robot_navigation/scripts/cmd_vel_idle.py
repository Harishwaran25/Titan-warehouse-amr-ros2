#!/usr/bin/env python3
"""Publish zero Twist on /cmd_vel_idle so twist_mux never leaves Gazebo
holding the last non-zero /cmd_vel when Nav2 goes quiet."""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelIdle(Node):
    def __init__(self):
        super().__init__('cmd_vel_idle')
        self._pub = self.create_publisher(Twist, 'cmd_vel_idle', 10)
        self.create_timer(0.05, self._tick)  # 20 Hz

    def _tick(self):
        self._pub.publish(Twist())


def main():
    rclpy.init()
    node = CmdVelIdle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
