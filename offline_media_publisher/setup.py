from setuptools import find_packages, setup

package_name = 'offline_media_publisher'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/image_publisher_launch.py',
            'launch/video_publisher_launch.py'
        ]),
        ('share/' + package_name + '/config', [
            'config/image_publisher.yaml',
            'config/video_publisher.yaml'
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='emoullet',
    maintainer_email='etienne.moullet@gmail.com',
    description='Publish images or video frames as simulated camera streams for testing.',
    license='BSD-3-Clause',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'image_publisher = offline_media_publisher.image_publisher_node:main',
            'video_publisher = offline_media_publisher.video_publisher_node:main',
        ],
    },
)
