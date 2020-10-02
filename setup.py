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
    "graphene-sqlalchemy>=2.3.0",
    "graphene-sqlalchemy-filter==1.12.1",
    "inflection==0.5.0"
]

setuptools.setup(
    name="graphene-sqlalchemy-auto-filter",  # Replace with your own username
    version=version,
    author="golsee, baddhizm",
    author_email="z.shj726@gmail.com, frenggy@gmail.com",
    license="MIT",
    description="generate default graphene schema with filters from sqlalchemy model base on graphene-sqlalchemy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Baddhizm/graphene-sqlalchemy-auto-filter.git",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    python_requires='>=3.6'
)
