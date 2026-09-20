#!/usr/bin/env bash
# Single-command warehouse bringup: Gazebo GUI + RViz + teleop + Nav2
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping old Gazebo / Nav2 / RViz processes..."
killall -9 gzserver gzclient rviz2 2>/dev/null || true
pkill -9 -f 'nav2_|robot_state_publisher|teleop_twist|vision_processor|auto_docking|lifter_controller|warehouse_bringup' 2>/dev/null || true
sleep 1

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# setup.sh is not executable; must be sourced (not run)
# shellcheck disable=SC1091
source /usr/share/gazebo-11/setup.sh
# shellcheck disable=SC1091
source "${ROOT}/install/setup.bash"

export GAZEBO_MODEL_DATABASE_URI=""

echo "Launching warehouse bringup (Gazebo + RViz + teleop + Nav2)..."
exec ros2 launch custom_warehouse_robot_navigation warehouse_bringup.launch.py \
  slam:=false autonav:=true teleop:=true vision:=false autonomy:=false
