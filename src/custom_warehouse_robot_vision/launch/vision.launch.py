from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    vision_node = Node(
        package='custom_warehouse_robot_vision',
        executable='vision_processor',
        name='vision_processor',
        output='screen'
    )

    return LaunchDescription([
        vision_node
    ])
