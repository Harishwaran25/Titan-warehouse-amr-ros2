import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    pkg_robot_desc = get_package_share_directory('custom_warehouse_robot_description')
    pkg_robot_gazebo = get_package_share_directory('custom_warehouse_robot_gazebo')

    gazebo_models_path = os.path.join(pkg_robot_gazebo, 'models')
    desc_share = pkg_robot_desc

    # AWS RoboMaker shelves/walls/clutter (optional; used by warehouse_pallets.world)
    aws_models_path = ''
    try:
        aws_share = get_package_share_directory('aws_robomaker_small_warehouse_world')
        aws_models_path = os.path.join(aws_share, 'models')
    except Exception:
        pass

    # Always keep Gazebo-11 system media/models/plugins. Overwriting RESOURCE_PATH
    # with only the robot package breaks gzclient (Camera shared_ptr assert).
    system_model = '/usr/share/gazebo-11/models'
    system_resource = '/usr/share/gazebo-11:/usr/share/gazebo-11/media'
    system_plugin = '/usr/lib/x86_64-linux-gnu/gazebo-11/plugins'

    model_path = ':'.join(filter(None, [
        os.environ.get('GAZEBO_MODEL_PATH', ''),
        system_model,
        gazebo_models_path,
        aws_models_path,
    ]))
    resource_path = ':'.join(filter(None, [
        os.environ.get('GAZEBO_RESOURCE_PATH', ''),
        system_resource,
        desc_share,
    ]))
    plugin_path = ':'.join(filter(None, [
        os.environ.get('GAZEBO_PLUGIN_PATH', ''),
        system_plugin,
    ]))

    # Default: pallet-rich AWS-based world. Restore old layout with world:=warehouse.world
    default_world = os.path.join(pkg_robot_gazebo, 'worlds', 'warehouse_pallets.world')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default=default_world)
    x_pose = LaunchConfiguration('x_pose', default='0.0')
    y_pose = LaunchConfiguration('y_pose', default='-5.0')
    z_pose = LaunchConfiguration('z_pose', default='0.05')
    yaw_pose = LaunchConfiguration('yaw_pose', default='0.0')
    gui = LaunchConfiguration('gui', default='true')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='true', description='Use sim time')
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=default_world,
        description='Gazebo world file. Use warehouse.world to restore the previous layout.')
    declare_x_cmd = DeclareLaunchArgument(
        'x_pose', default_value='0.0', description='Initial X position')
    declare_y_cmd = DeclareLaunchArgument(
        'y_pose', default_value='-5.0', description='Initial Y position')
    declare_z_cmd = DeclareLaunchArgument(
        'z_pose', default_value='0.05',
        description='Initial Z (keep near wheel radius to avoid spawn roll)')
    declare_yaw_cmd = DeclareLaunchArgument(
        'yaw_pose', default_value='0.0', description='Initial Yaw orientation')
    declare_gui_cmd = DeclareLaunchArgument(
        'gui', default_value='true', description='Whether to start Gazebo GUI')

    set_model_path_cmd = SetEnvironmentVariable('GAZEBO_MODEL_PATH', model_path)
    set_resource_path_cmd = SetEnvironmentVariable('GAZEBO_RESOURCE_PATH', resource_path)
    set_plugin_path_cmd = SetEnvironmentVariable('GAZEBO_PLUGIN_PATH', plugin_path)
    set_no_db_cmd = SetEnvironmentVariable('GAZEBO_MODEL_DATABASE_URI', '')

    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_desc, 'launch', 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    gzserver_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world}.items()
    )

    # Start GUI after world + spawn so rendering camera initializes cleanly
    gzclient_cmd = TimerAction(
        period=6.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')
                ),
                condition=IfCondition(gui),
            )
        ]
    )

    spawn_robot_cmd = TimerAction(
        period=2.0,
        actions=[
            Node(
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
        ]
    )

    # Snap pose back after physics settle (casters/impact can shove the robot)
    settle_reset_cmd = TimerAction(
        period=2.5,
        actions=[
            Node(
                package='custom_warehouse_robot_gazebo',
                executable='spawn_settle_reset.py',
                name='spawn_settle_reset',
                output='screen',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'entity': 'titan_warehouse_amr',
                    'x': 0.0,
                    'y': -5.0,
                    'z': 0.05,
                    'yaw': 0.0,
                    'delay': 2.5,
                }],
            )
        ]
    )

    return LaunchDescription([
        set_model_path_cmd,
        set_resource_path_cmd,
        set_plugin_path_cmd,
        set_no_db_cmd,
        declare_use_sim_time_cmd,
        declare_world_cmd,
        declare_x_cmd,
        declare_y_cmd,
        declare_z_cmd,
        declare_yaw_cmd,
        declare_gui_cmd,
        robot_state_publisher_cmd,
        gzserver_cmd,
        spawn_robot_cmd,
        settle_reset_cmd,
        gzclient_cmd,
    ])
