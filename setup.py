from setuptools import setup
import os

VERSION = "0.7.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="datasette-ripgrep",
    description="Web interface for searching your code using ripgrep, built as a Datasette plugin",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/datasette-ripgrep",
    project_urls={
        "Issues": "https://github.com/simonw/datasette-ripgrep/issues",
        "CI": "https://github.com/simonw/datasette-ripgrep/actions",
        "Changelog": "https://github.com/simonw/datasette-ripgrep/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["datasette_ripgrep"],
    entry_points={"datasette": ["ripgrep = datasette_ripgrep"]},
    package_data={"datasette_ripgrep": ["templates/*.html"]},
    install_requires=["datasette"],
    extras_require={"test": ["pytest", "pytest-asyncio", "httpx"]},
    tests_require=["datasette-ripgrep[test]"],
    python_requires=">=3.6",
)
