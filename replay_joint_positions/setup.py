import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'replay_joint_positions'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='megane',
    maintainer_email='megane@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'save_joint_positions = replay_joint_positions.manual_save_joint_positions:main',
            'replay_joint_positions = replay_joint_positions.replay_joint_positions:main'
        ],
    },
)
