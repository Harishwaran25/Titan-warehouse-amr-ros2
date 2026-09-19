#!/usr/bin/env python3
import time
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import LaserScan, BatteryState
from std_msgs.msg import String, Bool
from std_srvs.srv import Trigger

class AutoDockingServer(Node):
    """
    Autonomous Precision Docking & Charging Server for Titan Warehouse AMR.
    Features:
    - Multi-stage closed loop docking sequence (Vision + Laser guidance)
    - Closed-loop creep speed control
    - Contact lock and battery charging emulation
    - Clean reverse undock maneuver
    """

    STATE_IDLE = "IDLE"
    STATE_ALIGNING = "ALIGNING"
    STATE_APPROACHING = "APPROACHING"
    STATE_DOCKED_CHARGING = "DOCKED_CHARGING"
    STATE_UNDOCKING = "UNDOCKING"

    def __init__(self):
        super().__init__('auto_docking_server')

        self.state = self.STATE_IDLE
        self.dock_pose = None
        self.min_rear_scan = 10.0
        self.min_front_scan = 10.0
        self.dock_detected = False
        self.battery_pct = 0.85
        self.state_start_time = time.time()

        # Services
        self.srv_dock = self.create_service(Trigger, '/dock_robot', self.handle_dock_request)
        self.srv_undock = self.create_service(Trigger, '/undock_robot', self.handle_undock_request)

        # Publishers
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_status = self.create_publisher(String, '/robot/docking_status', 10)
        self.pub_battery = self.create_publisher(BatteryState, '/robot/battery_state', 10)

        # Subscriptions
        self.sub_dock_pose = self.create_subscription(
            PoseStamped, '/vision/docking_target', self.dock_pose_callback, 10)
        self.sub_dock_detected = self.create_subscription(
            Bool, '/vision/dock_detected', self.dock_detected_callback, 10)
        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)

        # Control Loop (20 Hz)
        self.timer = self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Titan AMR Auto-Docking Server initialized and ready.")

    def dock_pose_callback(self, msg: PoseStamped):
        self.dock_pose = msg

    def dock_detected_callback(self, msg: Bool):
        self.dock_detected = msg.data

    def scan_callback(self, msg: LaserScan):
        # Scan has 720 samples from -pi to +pi
        # Index 360 is forward (0 rad), Index 0 is rear (-pi rad), Index 719 is rear (+pi rad)
        n = len(msg.ranges)
        mid = n // 2
        # Front sector (+/- 15 deg)
        front_ranges = [r for r in msg.ranges[mid - 30: mid + 30] if not math.isnan(r) and not math.isinf(r) and r > 0.05]
        self.min_front_scan = min(front_ranges) if front_ranges else 10.0

        # Rear sector (outer edges: 0..30 and n-30..n)
        rear_ranges = [r for r in (msg.ranges[:30] + msg.ranges[-30:]) if not math.isnan(r) and not math.isinf(r) and r > 0.05]
        self.min_rear_scan = min(rear_ranges) if rear_ranges else 10.0

    def handle_dock_request(self, request, response):
        if self.state == self.STATE_DOCKED_CHARGING:
            response.success = True
            response.message = "Robot is already docked and charging."
            return response

        self.get_logger().info("Auto-Docking sequence initiated!")
        self.state = self.STATE_ALIGNING
        self.state_start_time = time.time()
        response.success = True
        response.message = "Docking sequence started."
        return response

    def handle_undock_request(self, request, response):
        if self.state != self.STATE_DOCKED_CHARGING:
            response.success = False
            response.message = f"Cannot undock: Robot is in state {self.state}."
            return response

        self.get_logger().info("Undocking maneuver initiated!")
        self.state = self.STATE_UNDOCKING
        self.state_start_time = time.time()
        response.success = True
        response.message = "Undocking maneuver started."
        return response

    def control_loop(self):
        cmd = Twist()
        now = time.time()
        elapsed = now - self.state_start_time

        # Update battery simulation
        if self.state == self.STATE_DOCKED_CHARGING:
            self.battery_pct = min(1.0, self.battery_pct + 0.0008)
        else:
            self.battery_pct = max(0.05, self.battery_pct - 0.00005)

        # State Machine Logic
        if self.state == self.STATE_IDLE:
            pass

        elif self.state == self.STATE_ALIGNING:
            # Check vision or laser target alignment
            if self.dock_detected and self.dock_pose is not None:
                lateral_error = self.dock_pose.pose.position.x
                if abs(lateral_error) > 0.04:
                    cmd.angular.z = -1.2 * lateral_error  # Proportional yaw correction
                else:
                    self.get_logger().info("Dock aligned! Transitioning to APPROACHING.")
                    self.state = self.STATE_APPROACHING
                    self.state_start_time = now
            else:
                # Fallback: slow search rotation
                cmd.angular.z = 0.2
                if elapsed > 10.0:
                    self.get_logger().warn("Docking alignment timeout: moving forward with laser guidance.")
                    self.state = self.STATE_APPROACHING
                    self.state_start_time = now

        elif self.state == self.STATE_APPROACHING:
            # Creep forward towards the dock plate
            # Stop when laser or vision detects contact distance (< 0.35m from lidar center)
            if self.min_front_scan < 0.40 or (self.dock_pose and self.dock_pose.pose.position.z < 0.42):
                cmd.linear.x = 0.0
                cmd.angular.z = 0.0
                self.get_logger().info("Docking contact established! Status: DOCKED_CHARGING.")
                self.state = self.STATE_DOCKED_CHARGING
                self.state_start_time = now
            else:
                cmd.linear.x = 0.08  # Slow creep speed (8 cm/s)
                # Fine centering if vision target is visible
                if self.dock_detected and self.dock_pose is not None:
                    cmd.angular.z = -0.8 * self.dock_pose.pose.position.x

        elif self.state == self.STATE_DOCKED_CHARGING:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0

        elif self.state == self.STATE_UNDOCKING:
            # Reverse straight out for 3 seconds, then stop
            if elapsed < 3.5:
                cmd.linear.x = -0.12  # Reverse at 12 cm/s
            elif elapsed < 7.0:
                cmd.linear.x = 0.0
                cmd.angular.z = 0.5   # Turn 180 degrees to face aisle
            else:
                cmd.linear.x = 0.0
                cmd.angular.z = 0.0
                self.get_logger().info("Undock completed. Robot is IDLE and ready for missions.")
                self.state = self.STATE_IDLE

        # Publish commands
        self.pub_cmd_vel.publish(cmd)

        # Publish status string
        status_msg = String()
        status_msg.data = f"{self.state} | Battery: {self.battery_pct*100.0:.1f}%"
        self.pub_status.publish(status_msg)

        # Publish BatteryState
        bat_msg = BatteryState()
        bat_msg.header.stamp = self.get_clock().now().to_msg()
        bat_msg.voltage = 24.0 * self.battery_pct
        bat_msg.percentage = float(self.battery_pct)
        bat_msg.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING
            if self.state == self.STATE_DOCKED_CHARGING
            else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        )
        self.pub_battery.publish(bat_msg)

def main(args=None):
    rclpy.init(args=args)
    node = AutoDockingServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
