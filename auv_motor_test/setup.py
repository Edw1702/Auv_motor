import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'auv_motor_test'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Eduardo',
    maintainer_email='eduardo@auv.org',
    description='Sistema de Teste dos Motores do AUV',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_controller = auv_motor_test.motor_controller:main',
            'gui_node = auv_motor_test.gui_node:main',
        ],
    },
)