cmake_minimum_required(VERSION 3.8)
project(custom_warehouse_robot_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY worlds models launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/spawn_settle_reset.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
