#!/usr/bin/env python3
"""
Setup script for SSH Config Studio

A native Python + GTK desktop application for managing SSH configuration files.
"""

from setuptools import setup, find_packages
import os

def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ssh-config-studio",
    version="1.0.0",
    author="SSH Config Studio Team",
    author_email="team@sshconfigstudio.com",
    description="A native Python + GTK desktop application for managing SSH configuration files",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/sshconfigstudio/ssh-config-studio",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Networking",
        "Topic :: Desktop Environment :: Desktop Environment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "ssh-config-studio=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.css", "*.glade", "*.ui"],
    },
    keywords="ssh config gtk desktop application",
    project_urls={
        "Bug Reports": "https://github.com/sshconfigstudio/ssh-config-studio/issues",
        "Source": "https://github.com/sshconfigstudio/ssh-config-studio",
        "Documentation": "https://github.com/sshconfigstudio/ssh-config-studio/wiki",
    },
)
