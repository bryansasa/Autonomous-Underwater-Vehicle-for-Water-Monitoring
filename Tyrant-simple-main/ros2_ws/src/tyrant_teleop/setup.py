from glob import glob
from setuptools import find_packages, setup

package_name = 'tyrant_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Tyrant AUV',
    maintainer_email='devnull@example.com',
    description='PS/joystick teleoperation mapping for Tyrant AUV.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tyrant_teleop = tyrant_teleop.teleop_node:main',
            'tyrant_joy_probe = tyrant_teleop.joy_probe:main',
        ],
    },
)
