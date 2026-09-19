#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from std_msgs.msg import String, Float64

class LifterController(Node):
    """
    Titan AMR Cargo Bed Lifter Mechanism Controller.
    Provides services to raise, lower, and inspect the cargo plate.
    """

    def __init__(self):
        super().__init__('lifter_controller')

        self.is_raised = False
        self.current_height = 0.0 # meters (0.0 = lowered, 0.06 = raised)

        # Services
        self.srv_raise = self.create_service(Trigger, '/lifter/raise', self.handle_raise)
        self.srv_lower = self.create_service(Trigger, '/lifter/lower', self.handle_lower)
        self.srv_toggle = self.create_service(Trigger, '/lifter/toggle', self.handle_toggle)
        self.srv_status = self.create_service(Trigger, '/lifter/status', self.handle_status)

        # Publishers
        self.pub_status = self.create_publisher(String, '/robot/lifter_state', 10)
        self.pub_height = self.create_publisher(Float64, '/robot/lifter_height', 10)

        # Timer to broadcast status (5 Hz)
        self.timer = self.create_timer(0.2, self.publish_status)
        self.get_logger().info("Titan AMR Lifter Mechanism Controller active (Default: LOWERED).")

    def handle_raise(self, request, response):
        if self.is_raised:
            response.success = True
            response.message = "Lifter already fully RAISED (0.06m)."
            return response

        self.get_logger().info("RAISING cargo lift plate...")
        self.is_raised = True
        self.current_height = 0.06
        response.success = True
        response.message = "Lifter plate raised successfully to 0.06m."
        return response

    def handle_lower(self, request, response):
        if not self.is_raised:
            response.success = True
            response.message = "Lifter already fully LOWERED (0.00m)."
            return response

        self.get_logger().info("LOWERING cargo lift plate...")
        self.is_raised = False
        self.current_height = 0.00
        response.success = True
        response.message = "Lifter plate lowered successfully to 0.00m."
        return response

    def handle_toggle(self, request, response):
        if self.is_raised:
            return self.handle_lower(request, response)
        else:
            return self.handle_raise(request, response)

    def handle_status(self, request, response):
        response.success = True
        response.message = f"Lifter status: {'RAISED' if self.is_raised else 'LOWERED'} ({self.current_height:.3f}m)"
        return response

    def publish_status(self):
        msg_str = String()
        msg_str.data = "RAISED" if self.is_raised else "LOWERED"
        self.pub_status.publish(msg_str)

        msg_height = Float64()
        msg_height.data = self.current_height
        self.pub_height.publish(msg_height)

def main(args=None):
    rclpy.init(args=args)
    node = LifterController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
