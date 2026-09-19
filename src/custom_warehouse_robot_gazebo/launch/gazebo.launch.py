import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    pkg_robot_desc = get_package_share_directory('custom_warehouse_robot_description')
    pkg_robot_gazebo = get_package_share_directory('custom_warehouse_robot_gazebo')

    # Models path
    gazebo_models_path = os.path.join(pkg_robot_gazebo, 'models')
    if 'GAZEBO_MODEL_PATH' in os.environ:
        model_path = os.environ['GAZEBO_MODEL_PATH'] + ':' + gazebo_models_path
    else:
        model_path = gazebo_models_path

    world_path = os.path.join(pkg_robot_gazebo, 'worlds', 'warehouse.world')

    # Launch Configurations
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='-8.0')
    y_pose = LaunchConfiguration('y_pose', default='-5.5')
    z_pose = LaunchConfiguration('z_pose', default='0.05')
    yaw_pose = LaunchConfiguration('yaw_pose', default='0.0')
    gui = LaunchConfiguration('gui', default='true')

    # Declare arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use sim time')
    declare_x_cmd = DeclareLaunchArgument(
        'x_pose', default_value='-8.0', description='Initial X position')
    declare_y_cmd = DeclareLaunchArgument(
        'y_pose', default_value='-5.5', description='Initial Y position')
    declare_z_cmd = DeclareLaunchArgument(
        'z_pose', default_value='0.05', description='Initial Z position')
    declare_yaw_cmd = DeclareLaunchArgument(
        'yaw_pose', default_value='0.0', description='Initial Yaw orientation')
    declare_gui_cmd = DeclareLaunchArgument(
        'gui', default_value='true', description='Whether to start Gazebo GUI')

    # Set Gazebo Model Path
    set_model_path_cmd = SetEnvironmentVariable('GAZEBO_MODEL_PATH', model_path)

    # Robot State Publisher
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_desc, 'launch', 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Gazebo Server
    gzserver_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world_path}.items()
    )

    # Gazebo Client (GUI)
    gzclient_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')
        ),
        launch_arguments={'gui': gui}.items()
    )

    # Spawn Robot Entity in Gazebo
    spawn_robot_cmd = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'titan_warehouse_amr',
            '-topic', 'robot_description',
            '-x', x_pose,
            '-y', y_pose,
            '-z', z_pose,
            '-Y', yaw_pose
        ],
        output='screen'
    )

    return LaunchDescription([
        set_model_path_cmd,
        declare_use_sim_time_cmd,
        declare_x_cmd,
        declare_y_cmd,
        declare_z_cmd,
        declare_yaw_cmd,
        declare_gui_cmd,
        robot_state_publisher_cmd,
        gzserver_cmd,
        gzclient_cmd,
        spawn_robot_cmd
    ])
