from setuptools import setup, find_packages

setup(
    name='spankurlaptop',
    version='1.0.0',
    description='A terminal background tool that gives your laptop senses.',
    author='NithinVarma50',
    packages=find_packages(),
    package_data={
        'spankurlaptop': ['audio.zip'],
    },
    install_requires=[
        'sounddevice',
        'numpy',
        'pygame',
        'psutil'
    ],
    entry_points={
        'console_scripts': [
            'spankurlaptop=spankurlaptop:main',
        ],
    },
)
