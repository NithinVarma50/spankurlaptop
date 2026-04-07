from setuptools import setup

setup(
    name='spankurlaptop',
    version='1.0.0',
    description='A terminal background tool that gives your laptop senses.',
    author='NithinVarma50',
    py_modules=['spankurlaptop'],
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
