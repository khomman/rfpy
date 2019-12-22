from setuptools import find_packages, setup

setup(
    name='rfpy',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'numpy',
        'obspy',
        'matplotlib'
    ],
    entry_points={
        'console_scripts': [
            'rfpy=rfpy.scripts.rfpy:run'
        ]
    }
)
