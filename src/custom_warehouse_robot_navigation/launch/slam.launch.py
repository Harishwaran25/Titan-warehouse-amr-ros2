import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, EqualsSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    pkg_nav = get_package_share_directory('custom_warehouse_robot_navigation')
    default_slam_params = os.path.join(pkg_nav, 'config', 'slam_toolbox_params.yaml')
    default_cartographer_config = os.path.join(pkg_nav, 'config')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam_type = LaunchConfiguration('slam_type', default='slam_toolbox')
    params_file = LaunchConfiguration('params_file', default=default_slam_params)

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use sim time')
    declare_slam_type_cmd = DeclareLaunchArgument(
        'slam_type', default_value='slam_toolbox',
        description='SLAM method: slam_toolbox or cartographer')
    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file', default_value=default_slam_params,
        description='Full path to SLAM parameters file')

    # SLAM Toolbox Node
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}],
        condition=IfCondition(EqualsSubstitution(slam_type, 'slam_toolbox'))
    )

    # Cartographer Nodes (Alternative / Fallback)
    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-configuration_directory', default_cartographer_config,
            '-configuration_basename', 'cartographer.lua'
        ],
        remappings=[('echoes', 'scan')],
        condition=IfCondition(EqualsSubstitution(slam_type, 'cartographer'))
    )

    cartographer_occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='occupancy_grid_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
        condition=IfCondition(EqualsSubstitution(slam_type, 'cartographer'))
    )

    return LaunchDescription([
        declare_use_sim_time_cmd,
        declare_slam_type_cmd,
        declare_params_file_cmd,
        slam_toolbox_node,
        cartographer_node,
        cartographer_occupancy_grid_node
    ])
