"""Ensure that the pyproject and module metadata never drift out of sync

The next best thing to having one source of truth is having a way to ensure all of your
sources of truth agree with each other.
"""
from pathlib import Path

import toml

import vault2vault


def test_metadata():
    """Test that module metadata matches pyproject poetry metadata"""

    with (Path(__file__).resolve().parent / ".." / "pyproject.toml").open() as infile:
        pyproject = toml.load(infile, _dict=dict)

    assert pyproject["tool"]["poetry"]["name"] == vault2vault.__title__
    assert pyproject["tool"]["poetry"]["version"] == vault2vault.__version__
    assert pyproject["tool"]["poetry"]["license"] == vault2vault.__license__
    assert pyproject["tool"]["poetry"]["description"] == vault2vault.__summary__
    assert pyproject["tool"]["poetry"]["repository"] == vault2vault.__url__
    assert (
        all(
            item in vault2vault.__authors__
            for item in pyproject["tool"]["poetry"]["authors"]
        )
        is True
    )
    assert (
        all(
            item in pyproject["tool"]["poetry"]["authors"]
            for item in vault2vault.__authors__
        )
        is True
    )
