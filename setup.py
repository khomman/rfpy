from setuptools import find_packages, setup

setup(
    name='rfpy',
    version='0.9.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'numpy',
        'obspy',
        'matplotlib',
        'cartopy'
    ],
    entry_points={
        'console_scripts': [
            'rfpy=rfpy.scripts.rfpy:run'
        ]
    }
)
