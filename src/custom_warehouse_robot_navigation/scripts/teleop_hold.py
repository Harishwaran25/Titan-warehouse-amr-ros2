#!/usr/bin/env python3
"""Hold-to-move keyboard teleop (unstamped Twist). Release key → stop."""
import select
import sys
import termios
import tty

import geometry_msgs.msg
import rclpy
from rclpy.node import Node


MOVE = {
    'i': (1.0, 0.0),
    ',': (-1.0, 0.0),
    'j': (0.0, 1.0),
    'l': (0.0, -1.0),
    'u': (1.0, 1.0),
    'o': (1.0, -1.0),
    'm': (-1.0, -1.0),
    '.': (-1.0, 1.0),
    'k': (0.0, 0.0),
    ' ': (0.0, 0.0),
}

HELP = """
Hold-to-move teleop (publishes /cmd_vel — for mapping)
----------------------------------------------------
   u  i  o
   j  k  l
   m  ,  .

Hold a key to drive, release to stop.
q/z : faster/slower    CTRL-C : quit
"""


class HoldTeleop(Node):
    def __init__(self):
        super().__init__('teleop_hold')
        self.speed = self.declare_parameter('speed', 0.35).value
        self.turn = self.declare_parameter('turn', 0.8).value
        # If no key arrives within this time, publish zero (release-to-stop)
        self.release_timeout = self.declare_parameter('release_timeout', 0.25).value
        self.rate_hz = self.declare_parameter('rate', 20.0).value
        self.pub = self.create_publisher(geometry_msgs.msg.Twist, 'cmd_vel', 10)
        self._lin = 0.0
        self._ang = 0.0
        self._last_key_time = self.get_clock().now()
        # After a move, publish one zero then go silent (no continuous zero flood).
        self._was_moving = False
        self.create_timer(1.0 / self.rate_hz, self._on_timer)

    def handle_key(self, key: str):
        now = self.get_clock().now()
        if key in MOVE:
            self._lin, self._ang = MOVE[key]
            self._last_key_time = now
        elif key == 'q':
            self.speed *= 1.1
            self.turn *= 1.1
            self.get_logger().info(f'speed={self.speed:.2f} turn={self.turn:.2f}')
        elif key == 'z':
            self.speed *= 0.9
            self.turn *= 0.9
            self.get_logger().info(f'speed={self.speed:.2f} turn={self.turn:.2f}')
        elif key == '\x03':
            return False
        else:
            # unknown key → stop immediately
            self._lin = 0.0
            self._ang = 0.0
            self._last_key_time = now
        return True

    def _on_timer(self):
        now = self.get_clock().now()
        age = (now - self._last_key_time).nanoseconds * 1e-9
        moving = age <= self.release_timeout and (self._lin != 0.0 or self._ang != 0.0)
        if moving:
            msg = geometry_msgs.msg.Twist()
            msg.linear.x = self._lin * self.speed
            msg.angular.z = self._ang * self.turn
            self.pub.publish(msg)
            self._was_moving = True
        elif self._was_moving:
            # Release: one zero to stop, then silence.
            self.pub.publish(geometry_msgs.msg.Twist())
            self._was_moving = False
        # idle: do not publish

    def stop(self):
        self.pub.publish(geometry_msgs.msg.Twist())


def get_key(settings, timeout: float):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    key = sys.stdin.read(1) if rlist else ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main():
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = HoldTeleop()
    print(HELP)
    print(f'speed={node.speed:.2f} turn={node.turn:.2f}')
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            key = get_key(settings, timeout=0.05)
            if key:
                if not node.handle_key(key):
                    break
    except Exception as exc:  # noqa: BLE001
        print(exc)
    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
