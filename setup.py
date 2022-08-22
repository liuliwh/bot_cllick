#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="bot_click",
    packages=find_packages(include=["bot_click", "examples"]),
    python_requires=">=3.10",
)
