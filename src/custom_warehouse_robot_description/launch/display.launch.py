import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('custom_warehouse_robot_description')
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'robot_model.rviz')

    use_gui = LaunchConfiguration('use_gui', default='true')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    declare_use_gui_cmd = DeclareLaunchArgument(
        'use_gui',
        default_value='true',
        description='Whether to display joint state publisher GUI'
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true'
    )

    robot_state_pub_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    joint_state_pub_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        condition=UnlessCondition(use_gui),
        parameters=[{'use_sim_time': use_sim_time}]
    )

    joint_state_pub_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        condition=IfCondition(use_gui)
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        declare_use_gui_cmd,
        declare_use_sim_time_cmd,
        robot_state_pub_launch,
        joint_state_pub_node,
        joint_state_pub_gui_node,
        rviz_node
    ])
