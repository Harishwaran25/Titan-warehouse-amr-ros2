#!/usr/bin/env bash
set -e

echo "=== Installing Titan AMR Dependencies for ROS 2 Humble ==="
sudo apt update
sudo apt install -y \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-plugins \
  ros-humble-slam-toolbox \
  ros-humble-joint-state-publisher \
  ros-humble-joint-state-publisher-gui \
  ros-humble-xacro \
  python3-pip \
  python3-opencv

echo "=== Dependencies Installed Successfully ==="
