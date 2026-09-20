#!/usr/bin/env bash
# Kill Gazebo, RViz, Nav2, teleop, and related warehouse bringup processes.
set -eo pipefail

echo "Stopping warehouse / Gazebo / Nav2 processes..."

killall -9 gzserver gzclient rviz2 2>/dev/null || true

pkill -9 -f 'ros2 launch custom_warehouse_robot' 2>/dev/null || true
pkill -9 -f 'warehouse_bringup' 2>/dev/null || true
pkill -9 -f 'nav2_' 2>/dev/null || true
pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
pkill -9 -f 'teleop_twist|teleop_hold' 2>/dev/null || true
pkill -9 -f 'twist_mux' 2>/dev/null || true
pkill -9 -f 'async_slam_toolbox|slam_toolbox' 2>/dev/null || true
pkill -9 -f 'vision_processor|auto_docking|lifter_controller' 2>/dev/null || true
pkill -9 -f 'spawn_entity.py' 2>/dev/null || true
pkill -9 -f 'initialpose_to_gazebo' 2>/dev/null || true

sleep 1

echo "Remaining related processes (if any):"
pgrep -af 'gzserver|gzclient|rviz2|nav2_|warehouse_bringup|teleop|twist_mux|slam_toolbox' 2>/dev/null || echo "  (none)"

echo "Done."
