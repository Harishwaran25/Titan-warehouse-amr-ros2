cmake_minimum_required(VERSION 3.8)
project(custom_warehouse_robot_navigation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config maps launch rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/initialpose_to_gazebo.py
  scripts/teleop_hold.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
