#!/usr/bin/env python3
import os, setuptools


def fix(item):
    if "==" in item:
        return item.replace("==", ">=")
    if item.startswith("-e"):
        return item[item.rfind("=") + 1 :]
    return item


setup_path = os.path.dirname(__file__)

with open(os.path.join(setup_path, "README.md")) as readme:
    long_description = readme.read()

with open(os.path.join(setup_path, "requirements.txt")) as f:
    install_requires = f.read().splitlines()
    install_requires = [fix(item) for item in install_requires]


setuptools.setup(
    name="documentstore-migracao",
    version="0.1",
    author="Cesar Augustp",
    author_email="cesar.bruschetta@scielo.org",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="2-clause BSD",
    packages=setuptools.find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    include_package_data=False,
    python_requires=">=3.6",
    install_requires=install_requires,
    test_suite="tests",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Other Environment",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: OS Independent",
    ],
    entry_points="""\
        [console_scripts]
            documentstore_migracao=documentstore_migracao.main:main
    """,
)
