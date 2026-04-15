from glob import glob
from setuptools import find_packages, setup

package_name = 'dynamic_parameters_identification'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/bringup/config', glob('bringup/config/*.yaml')),
        ('share/' + package_name + '/bringup/launch', glob('bringup/launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='megane',
    maintainer_email='millan@isir.upmc.fr',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joints_sine_trajectory = dynamic_parameters_identification.joints_sinusoids:main',
            'excitation_trajectory = dynamic_parameters_identification.generate_excitation_trajectory:main',
            'parameters_identification = dynamic_parameters_identification.parameters_identification:main'
        ],
    },
)
