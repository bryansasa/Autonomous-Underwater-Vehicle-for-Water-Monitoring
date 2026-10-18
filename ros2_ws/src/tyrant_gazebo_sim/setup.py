import os
from glob import glob
from setuptools import setup

package_name = 'tyrant_gazebo_sim'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'models', 'tyrant_rov'), glob('models/tyrant_rov/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bryan Gabriel Izaac Sasabone',
    maintainer_email='bryan@telkomuniversity.ac.id',
    description='Paket Simulasi Gazebo ROV/AUV dan Subsistem EA-DSRA Waduk Saguling',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'saguling_field_server = tyrant_gazebo_sim.saguling_field_server:main',
            'ea_dsra_node = tyrant_gazebo_sim.ea_dsra_node:main',
            'rov_teleop_key = tyrant_gazebo_sim.rov_teleop_key:main',
        ],
    },
)
