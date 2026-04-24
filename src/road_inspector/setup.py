from setuptools import find_packages, setup

package_name = 'road_inspector'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='boda240',
    maintainer_email='abdelrahmanaly065@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
    'console_scripts': [
        'gui_node = road_inspector.gui_node:main',
        'navigation_node = road_inspector.navigation_node:main',
        'camera_node = road_inspector.camera_node:main',
        'check_camera = road_inspector.check_camera:main',
        'ai_node = road_inspector.ai_node:main',
    ],
    }, 
)

