from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='auv_motor_test',
            executable='motor_controller',
            name='motor_controller',
            output='screen'
        ),
        Node(
            package='auv_motor_test',
            executable='gui_node',
            name='motor_gui_node',
            output='screen'
        )
    ])