#!/usr/bin/env python
from setuptools import setup, find_packages

dependencies = [
    "chia-blockchain",
    "chia-dev-tools"
]

setup(
    name='example',
    version='0.1.0',
    packages=find_packages(include=['ownable_singleton', 'ownable_singleton.*']),
    install_requires=dependencies,
)