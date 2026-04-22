#!/usr/bin/env python3
"""
Setup script for DeskBuddy CLI
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deskbuddy-cli",
    version="2.0.0",
    author="DeskBuddy Team",
    description="Terminal-based Bluetooth/WiFi/Alert manager for ESP32",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/deskbuddy-python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Console",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
    install_requires=[
        "bleak>=0.21.0",
        "rich>=13.0.0",
        "click>=8.0.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.900",
        ],
    },
    entry_points={
        "console_scripts": [
            "deskbuddy=main:main",
        ],
    },
)
