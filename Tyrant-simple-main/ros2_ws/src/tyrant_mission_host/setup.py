from glob import glob
from setuptools import find_packages, setup
name = 'tyrant_mission_host'
setup(name=name, version='0.1.0', packages=find_packages(exclude=['test']),
      data_files=[('share/ament_index/resource_index/packages', ['resource/'+name]),
                  ('share/'+name, ['package.xml']),
                  ('share/'+name+'/config', glob('config/*.yaml')),
                  ('share/'+name+'/launch', glob('launch/*.launch.py'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='Tyrant AUV', maintainer_email='devnull@example.com',
      description='Mission sampling coordinator and recorder.', license='MIT',
      entry_points={'console_scripts': ['mission_host = tyrant_mission_host.node:main']})
