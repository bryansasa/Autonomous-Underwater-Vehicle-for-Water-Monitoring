from glob import glob
from setuptools import find_packages, setup

package_name = 'tyrant_sim'

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
    description='Reduced HIL plant simulation and SysID excitation for Tyrant AUV.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tyrant_plant_sim = tyrant_sim.plant_node:main',
            'tyrant_sysid_excitation = tyrant_sim.excitation_node:main',
        ],
    },
)
