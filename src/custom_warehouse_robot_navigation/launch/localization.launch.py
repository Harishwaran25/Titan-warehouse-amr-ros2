import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_nav = get_package_share_directory('custom_warehouse_robot_navigation')
    default_map_file = os.path.join(pkg_nav, 'maps', 'warehouse_map.yaml')
    # NOTE: must NOT be named 'params_file' — gazebo_ros/gzserver.launch.py
    # declares that arg with default '' and it leaks into the shared launch context.
    default_params_file = os.path.join(pkg_nav, 'config', 'nav2_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('localization_params_file')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use sim time')
    declare_map_cmd = DeclareLaunchArgument(
        'map', default_value=default_map_file, description='Full path to map yaml file')
    declare_params_file_cmd = DeclareLaunchArgument(
        'localization_params_file', default_value=default_params_file,
        description='Full path to Nav2 params file for map_server/amcl')

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[params_file, {'yaml_filename': map_file, 'use_sim_time': use_sim_time}]
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[params_file, {'use_sim_time': use_sim_time}]
    )

    lifecycle_mgr = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
        }]
    )

    return LaunchDescription([
        declare_use_sim_time_cmd,
        declare_map_cmd,
        declare_params_file_cmd,
        map_server_node,
        amcl_node,
        lifecycle_mgr
    ])
