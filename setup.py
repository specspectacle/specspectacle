"""
SpecSpectacle - Turn specs into spectacles
YAML user journeys to live product demos
"""

import os

from setuptools import find_packages, setup


# Read README for long description
def read_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            return f.read()
    return __doc__


# Read requirements
def read_requirements(filename):
    req_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(req_path):
        with open(req_path, encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#") and not line.startswith("-r")
            ]
    return []


setup(
    name="specspectacle",
    version="0.1.0",
    description="Turn specs into spectacles – YAML user journeys to live product demos",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author="Fedrick Nishant",
    author_email="fednish@gmail.com",
    url="https://github.com/fedricknishant/specspectacle",
    license="Apache-2.0",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("requirements-dev.txt"),
    },
    # CLI entry point
    entry_points={
        "console_scripts": [
            "specspectacle=specspectacle.cli.main:cli",
        ],
    },
    # PyPI classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Software Development :: Testing",
        "Topic :: Multimedia :: Video",
        "Topic :: Documentation",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Console",
        "Natural Language :: English",
        "Typing :: Typed",
    ],
    keywords="video demo automation playwright yaml cli tts text-to-speech narration product-demo",
    project_urls={
        "Homepage": "https://github.com/fedricknishant/specspectacle",
        "Bug Reports": "https://github.com/fedricknishant/specspectacle/issues",
        "Source": "https://github.com/fedricknishant/specspectacle",
        "Documentation": "https://github.com/fedricknishant/specspectacle/tree/main/docs",
        "Changelog": "https://github.com/fedricknishant/specspectacle/releases",
    },
)
