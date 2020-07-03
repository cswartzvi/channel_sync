from setuptools import setup, find_packages

setup(
    name='isoconda',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'conda',
        'pyyaml',
        'requests'
    ],
    entry_points={
        'console_scripts': [
            'isoconda = isoconda.isoconda:update',
        ],
    },
)
