#!/usr/bin/env python3
import os, setuptools

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md")) as f:
    README = f.read()
with open(os.path.join(here, "CHANGES.txt")) as f:
    CHANGES = f.read()

requires = [
    "pyramid",
    "pyramid_jinja2",
    "pyramid_debugtoolbar",
    "waitress",
    "legendarium==2.0.2",
    "requests==2.21.0",
    "articlemetaapi==1.26.5",
    "picles.plumber==0.11",
    "lxml==4.3.1",
    "packtools",
    "paginate",
    "minio",
]

tests_require = [
    "WebTest >= 1.3.1",  # py3 compat
    "pytest",  # includes virtualenv
    "pytest-cov",
    "coverage==4.5.2",
    "nose==1.3.7",
]

setuptools.setup(
    name="documentstore-migracao",
    version="0.1",
    author="Cesar Augustp",
    author_email="cesar.bruschetta@scielo.org",
    description="",
    long_description=README + "\n\n" + CHANGES,
    long_description_content_type="text/markdown",
    license="2-clause BSD",
    packages=setuptools.find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    include_package_data=True,
    extras_require={"testing": tests_require},
    install_requires=requires,
    python_requires=">=3.5",
    test_suite="tests",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Other Environment",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Operating System :: OS Independent",
    ],
    entry_points="""\
        [console_scripts]
            ds_migracao=documentstore_migracao.main:main
            ds_tools=documentstore_migracao.main:tools
            migrate_isis=documentstore_migracao.main:main_migrate_isis
        [paste.app_factory]
            main=documentstore_migracao.webserver:main
    """,
)
