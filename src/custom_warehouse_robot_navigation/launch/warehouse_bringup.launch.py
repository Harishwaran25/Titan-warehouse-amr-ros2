import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_nav = get_package_share_directory('custom_warehouse_robot_navigation')
    pkg_gazebo = get_package_share_directory('custom_warehouse_robot_gazebo')
    pkg_vision = get_package_share_directory('custom_warehouse_robot_vision')
    pkg_autonomy = get_package_share_directory('custom_warehouse_robot_autonomy')
    default_rviz_config = os.path.join(pkg_nav, 'rviz', 'warehouse_navigation.rviz')
    # install/setup.bash relative to share/<pkg>
    install_setup = os.path.abspath(os.path.join(pkg_nav, '..', '..', '..', 'setup.bash'))

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gazebo = LaunchConfiguration('gazebo', default='true')
    rviz = LaunchConfiguration('rviz', default='true')
    teleop = LaunchConfiguration('teleop', default='true')
    slam = LaunchConfiguration('slam', default='false')
    autonav = LaunchConfiguration('autonav', default='true')
    # Default off so a plain bringup is Gazebo + RViz + teleop + Nav2
    vision = LaunchConfiguration('vision', default='false')
    autonomy = LaunchConfiguration('autonomy', default='false')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use sim time')
    declare_gazebo_cmd = DeclareLaunchArgument(
        'gazebo', default_value='true', description='Whether to start Gazebo simulation')
    declare_rviz_cmd = DeclareLaunchArgument(
        'rviz', default_value='true', description='Whether to start RViz visualization')
    declare_teleop_cmd = DeclareLaunchArgument(
        'teleop', default_value='true',
        description='Whether to open keyboard teleop in a new terminal')
    declare_slam_cmd = DeclareLaunchArgument(
        'slam', default_value='false',
        description='Whether to run SLAM mapping instead of AMCL localization')
    declare_autonav_cmd = DeclareLaunchArgument(
        'autonav', default_value='true',
        description='Whether to launch Nav2 planners and controllers')
    declare_vision_cmd = DeclareLaunchArgument(
        'vision', default_value='false', description='Whether to launch vision processing node')
    declare_autonomy_cmd = DeclareLaunchArgument(
        'autonomy', default_value='false',
        description='Whether to launch auto-docking and lifter nodes')

    # 1. Gazebo Simulation & Spawner (GUI on)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
        ),
        condition=IfCondition(gazebo),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'gui': 'true',
        }.items()
    )

    # 2. SLAM Mapping (active when slam:=true)
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'slam.launch.py')
        ),
        condition=IfCondition(slam),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 3. AMCL Localization (active when slam:=false)
    # Avoid arg name 'params_file' — conflicts with gazebo_ros gzserver.launch.py
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'localization.launch.py')
        ),
        condition=UnlessCondition(slam),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'localization_params_file': os.path.join(pkg_nav, 'config', 'nav2_params.yaml'),
            'map': os.path.join(pkg_nav, 'maps', 'warehouse_map.yaml'),
        }.items()
    )

    # 4. Nav2 Navigation Stack (Planners, Controllers, BT)
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'navigation.launch.py')
        ),
        condition=IfCondition(autonav),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'nav_params_file': os.path.join(pkg_nav, 'config', 'nav2_params.yaml'),
        }.items()
    )

    # 5. Vision Processing Pipeline
    vision_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_vision, 'launch', 'vision.launch.py')
        ),
        condition=IfCondition(vision)
    )

    # 6. Autonomy Subsystems (Auto-Docking & Lifter mechanism)
    autonomy_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_autonomy, 'launch', 'autonomy.launch.py')
        ),
        condition=IfCondition(autonomy)
    )

    # 7. RViz2 Visualization
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', default_rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(rviz)
    )

    # 8. Mux Nav2 + teleop onto /cmd_vel (teleop wins while keys are pressed)
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        output='screen',
        parameters=[
            os.path.join(pkg_nav, 'config', 'twist_mux.yaml'),
            {'use_sim_time': use_sim_time},
        ],
        remappings=[('cmd_vel_out', '/cmd_vel')],
    )

    # 9. Hold-to-move keyboard teleop (unstamped Twist; release → stop)
    teleop_bash = (
        f'source /opt/ros/humble/setup.bash && source {install_setup} && '
        'echo "Hold-to-move teleop — click this window"; '
        'echo "Hold i/j/k/l to drive, release to stop"; '
        'ros2 run custom_warehouse_robot_navigation teleop_hold.py '
        '--ros-args -r cmd_vel:=/cmd_vel_teleop '
        '-p speed:=0.35 -p turn:=0.8 -p release_timeout:=0.25; '
        'exec bash'
    )
    teleop_terminal = ExecuteProcess(
        cmd=['gnome-terminal', '--', 'bash', '-c', teleop_bash],
        output='screen',
        condition=IfCondition(teleop)
    )

    return LaunchDescription([
        declare_use_sim_time_cmd,
        declare_gazebo_cmd,
        declare_rviz_cmd,
        declare_teleop_cmd,
        declare_slam_cmd,
        declare_autonav_cmd,
        declare_vision_cmd,
        declare_autonomy_cmd,
        gazebo_launch,
        slam_launch,
        localization_launch,
        navigation_launch,
        vision_launch,
        autonomy_launch,
        rviz_node,
        twist_mux_node,
        teleop_terminal
    ])
