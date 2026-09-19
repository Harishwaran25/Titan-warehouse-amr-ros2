from setuptools import setup
import os
from glob import glob

package_name = 'custom_warehouse_robot_vision'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Harish',
    maintainer_email='harish@todo.todo',
    description='Vision processing pipeline, OpenCV integration, docking target detector, and future AI vision hooks',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'vision_processor = custom_warehouse_robot_vision.vision_processor_node:main',
            'docking_detector = custom_warehouse_robot_vision.docking_vision_detector:main',
        ],
    },
)
