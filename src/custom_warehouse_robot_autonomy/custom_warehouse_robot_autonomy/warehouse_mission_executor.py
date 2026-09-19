#!/usr/bin/env python3
import time
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import Trigger
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

def create_pose_stamped(navigator, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.position.z = 0.0
    # Convert yaw to quaternion (Z axis)
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose

def main():
    rclpy.init()
    navigator = BasicNavigator()

    print("=========================================================")
    print("   TITAN AMR AUTONOMOUS WAREHOUSE MISSION EXECUTOR       ")
    print("=========================================================")

    # Wait for Nav2 to become active
    print("Waiting for Nav2 autonomy stack to activate...")
    navigator.waitUntilNav2Active()
    print("Nav2 stack is online and ready!")

    # Helper client node for Lifter and Docking services
    cli_node = Node('mission_helper_cli')
    cli_dock = cli_node.create_client(Trigger, '/dock_robot')
    cli_undock = cli_node.create_client(Trigger, '/undock_robot')
    cli_lift_up = cli_node.create_client(Trigger, '/lifter/raise')
    cli_lift_down = cli_node.create_client(Trigger, '/lifter/lower')

    def call_trigger_service(cli, name):
        if cli.wait_for_service(timeout_sec=2.0):
            req = Trigger.Request()
            future = cli.call_async(req)
            rclpy.spin_until_future_complete(cli_node, future, timeout_sec=3.0)
            if future.result():
                print(f"[{name}] Result: {future.result().message}")
                return
        print(f"[{name}] Service call skipped (service not ready).")

    # Step 1: Undock
    print("\n--- [STEP 1/6]: Undocking from Charging Station ---")
    call_trigger_service(cli_undock, "Undock")
    time.sleep(2.0)

    # Step 2: Navigate to Storage Pod 1 (Aisle 1)
    print("\n--- [STEP 2/6]: Navigating to Storage Aisle 1 (x=2.0, y=2.5) ---")
    goal1 = create_pose_stamped(navigator, 2.0, 2.5, 0.0)
    navigator.goToPose(goal1)

    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback:
            print(f"Distance remaining: {feedback.distance_remaining:.2f} m", end='\r')
        time.sleep(0.5)

    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        print("\nArrived at Storage Pod in Aisle 1!")
    else:
        print(f"\nNavigation to Aisle 1 ended with status: {result}")

    # Step 3: Raise Lifter Plate
    print("\n--- [STEP 3/6]: Hoisting Storage Pod (Lifter UP) ---")
    call_trigger_service(cli_lift_up, "Lifter Raise")
    time.sleep(1.5)

    # Step 4: Transport Pod to Dispatch / Staging Area
    print("\n--- [STEP 4/6]: Transporting Pod to Staging Area (x=6.0, y=-5.5) ---")
    goal2 = create_pose_stamped(navigator, 6.0, -5.5, -1.57)
    navigator.goToPose(goal2)

    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback:
            print(f"Distance remaining: {feedback.distance_remaining:.2f} m", end='\r')
        time.sleep(0.5)

    print("\nArrived at Staging / Dispatch area!")

    # Step 5: Lower Lifter Plate
    print("\n--- [STEP 5/6]: Offloading Pod (Lifter DOWN) ---")
    call_trigger_service(cli_lift_down, "Lifter Lower")
    time.sleep(1.5)

    # Step 6: Return to Charging Bay and Auto-Dock
    print("\n--- [STEP 6/6]: Returning to Charging Bay (x=-7.0, y=-5.5) ---")
    goal3 = create_pose_stamped(navigator, -7.0, -5.5, 3.1415)
    navigator.goToPose(goal3)

    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback:
            print(f"Distance remaining: {feedback.distance_remaining:.2f} m", end='\r')
        time.sleep(0.5)

    print("\nArrived at Charging Bay Approach Waypoint. Initiating Auto-Docking...")
    call_trigger_service(cli_dock, "Auto-Docking")

    print("\n=========================================================")
    print("      WAREHOUSE MISSION COMPLETED SUCCESSFULLY!          ")
    print("=========================================================")

    cli_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
