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
    "legendarium",
    "requests",
    "articlemetaapi>=1.26.6",
    "picles.plumber",
    "lxml",
    "scielo-documentstore",
    "packtools",
    "paginate",
    "minio",
    "tqdm",
    "fs",
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
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
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
    python_requires=">=3.6",
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
    dependency_links=[
        "git://github.com/scieloorg/document-store.git@96585ce99fb09503605416dceb5207a4ac70c43e#egg=scielo_documentstore",
    ],

    entry_points="""\
        [console_scripts]
            ds_migracao=documentstore_migracao.main:main_migrate_articlemeta
            ds_tools=documentstore_migracao.main:tools
            migrate_isis=documentstore_migracao.main:main_migrate_isis
        [paste.app_factory]
            main=documentstore_migracao.webserver:main
    """,
)
