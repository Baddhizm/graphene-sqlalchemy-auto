import ast
import re

import setuptools

_version_re = re.compile(r"version\s+=\s+(.*)")

with open("pyproject.toml", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()
requirements = [
    # To keep things simple, we only support newer versions of Graphene
    "graphene-sqlalchemy>=2.3.0",
    "inflection"
]
setuptools.setup(
    name="graphene-sqlalchemy-auto-filter",  # Replace with your own username
    version=version,
    author="golsee, baddhizm",
    author_email="z.shj726@gmail.com, frenggy@gmail.com",
    description="generate default graphene schema with filters from sqlalchemy model base on graphene-sqlalchemy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/goodking-bq/graphene-sqlalchemy-auto.git",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
    dependency_links=[
        "git+git://github.com/Baddhizm/graphene-sqlalchemy-filter-py35#egg=graphene-sqlalchemy-filter"
    ]
)
