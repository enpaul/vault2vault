#!/usr/bin/env bash
#
# Environment setup script for the local project. Intended to be used with automation
# to create a repeatable local environment for tests to be run in. The python env
# this script creates can be accessed at the location defined by the CI_VENV variable
# below.
#
# POETRY_VERSION can be set to install a specific version of Poetry

set -e;

CI_CACHE=$HOME/.cache;
INSTALL_POETRY_VERSION="${POETRY_VERSION:-1.3.2}";

mkdir --parents "$CI_CACHE";

command -v python;
python3.10 --version;

curl --location https://install.python-poetry.org \
  --output "$CI_CACHE/install-poetry.py" \
  --silent \
  --show-error;
python "$CI_CACHE/install-poetry.py" \
  --version "$INSTALL_POETRY_VERSION" \
  --yes;
poetry --version --no-ansi;
poetry run pip --version;

poetry install \
  --sync \
  --no-ansi \
  --no-root \
  --only ci;

poetry env info;
poetry run tox --version;
