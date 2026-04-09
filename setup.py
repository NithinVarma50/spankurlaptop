from setuptools import setup, find_packages
import os

# Read the long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='spankurlaptop',
    version='1.0.1',
    description='A terminal background tool that gives your laptop senses.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NithinVarma50/spankurlaptop",
    author='NithinVarma50',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'spankurlaptop': ['audio.zip'],
    },
    python_requires='>=3.8',
    install_requires=[
        'sounddevice',
        'numpy',
        'pygame',
        'psutil',
        'winrt-Windows.Devices.Sensors; sys_platform == "win32"',
        'keyboard',
        'pywebview'
    ],
    entry_points={
        'console_scripts': [
            'spankurlaptop=spankurlaptop:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
