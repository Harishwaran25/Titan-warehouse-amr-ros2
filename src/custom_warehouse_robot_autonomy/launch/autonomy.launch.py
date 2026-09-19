from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    auto_docking_node = Node(
        package='custom_warehouse_robot_autonomy',
        executable='auto_docking_server',
        name='auto_docking_server',
        output='screen'
    )

    lifter_node = Node(
        package='custom_warehouse_robot_autonomy',
        executable='lifter_controller',
        name='lifter_controller',
        output='screen'
    )

    return LaunchDescription([
        auto_docking_node,
        lifter_node
    ])
