# vault2vault

Like
[`ansible-vault rekey`](https://docs.ansible.com/ansible/latest/cli/ansible-vault.html#rekey)
but works recursively on encrypted files and in-line variables

[![CI Status](https://github.com/enpaul/vault2vault/workflows/CI/badge.svg?event=push)](https://github.com/enpaul/vault2vault/actions)
[![PyPI Version](https://img.shields.io/pypi/v/vault2vault)](https://pypi.org/project/vault2vault/)
[![License](https://img.shields.io/pypi/l/vault2vault)](https://opensource.org/licenses/MIT)
[![Python Supported Versions](https://img.shields.io/pypi/pyversions/vault2vault)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

⚠️ **This project is alpha software and is under active development** ⚠️

- [What is this?](#what-is-this)
- [Installing](#installing)
- [Using](#using)
- [Developing](#developer-documentation)

## What is this?

If you use [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
then you may have encountered the problem of needing to role your vault password. Maybe
you found it written down on a sticky note, maybe a coworker who knows it left the
company, maybe you accidentally typed it into Slack when you thought the focus was on your
terminal. Whatever, these things happen.

The builtin tool Ansible provides,
[`ansible-vault rekey`](https://docs.ansible.com/ansible/latest/cli/ansible-vault.html#rekey),
works suffers from two main drawbacks: first, it only works on vault encrypted files and
not on vault encrypted YAML data; and second, it only works on a single vault encrypted
file at a time. To rekey everything in a large project you'd need to write a script that
goes through every file and rekeys everything in every format it can find.

This is that script.

## Installing

If you're using [Poetry](https://python-poetry.org/) or
[Pipenv](https://pipenv.pypa.io/en/latest/) to manage your Ansible runtime environment,
you can just add `vault2vault` to that same environment:

```
# using poetry
poetry add vault2vault --dev

# using pipenv
pipenv install vault2vault
```

If you're using Ansible from your system package manager, it's probably easier to just
install `vault2vault` using [PipX](https://pypa.github.io/pipx/) and the `ansible` extra:

```
pipx install vault2vault[ansible]
```

**Note: vault2vault requires an Ansible installation to function. If you are installing to a standalone virtual environment (like with PipX) then you must install it with the `ansible` extra to ensure a version of Ansible is available to the application.**

## Using

These docs are pretty sparse, largely because this project is still under active design
and redevelopment. Here are the command line options:

```
> vault2vault --help
usage: vault2vault [-h] [--version] [--interactive] [-v] [-b] [-i VAULT_ID] [--ignore-undecryptable] [--old-pass-file OLD_PASS_FILE]
                   [--new-pass-file NEW_PASS_FILE]
                   [paths ...]

Recursively rekey ansible-vault encrypted files and in-line variables

positional arguments:
  paths                 Paths to search for Ansible Vault encrypted content

options:
  -h, --help            show this help message and exit
  --version             Show program version and exit
  --interactive         Step through files and variables interactively, prompting for confirmation before making each change
  -v, --verbose         Increase verbosity; can be repeated
  -b, --backup          Write a backup of every file to be modified, suffixed with '.bak'
  -i VAULT_ID, --vault-id VAULT_ID
                        Limit rekeying to encrypted secrets with the specified Vault ID
  --ignore-undecryptable
                        Ignore any file or variable that is not decryptable with the provided vault secret instead of raising an error
  --old-pass-file OLD_PASS_FILE
                        Path to a file with the old vault password to decrypt secrets with
  --new-pass-file NEW_PASS_FILE
                        Path to a file with the new vault password to rekey secrets with
```

Please report any bugs or issues you encounter on
[Github](https://github.com/enpaul/vault2vault/issues).

## Developer Documentation

All project contributors and participants are expected to adhere to the
[Contributor Covenant Code of Conduct, v2](CODE_OF_CONDUCT.md) ([external link](https://www.contributor-covenant.org/version/2/0/code_of_conduct/)).

The `devel` branch has the latest (and potentially unstable) changes. The stable releases
are tracked on [Github](https://github.com/enpaul/vault2vault/releases),
[PyPi](https://pypi.org/project/vault2vault/#history), and in the
[Changelog](CHANGELOG.md).

- To report a bug, request a feature, or ask for assistance, please
  [open an issue on the Github repository](https://github.com/enpaul/vault2vault/issues/new).
- To report a security concern or code of conduct violation, please contact the project
  author directly at **‌me \[at‌\] enp dot‎ ‌one**.
- To submit an update, please
  [fork the repository](https://docs.github.com/en/enterprise/2.20/user/github/getting-started-with-github/fork-a-repo)
  and [open a pull request](https://github.com/enpaul/vault2vault/compare).

Developing this project requires [Python 3.7+](https://www.python.org/downloads/) and
[Poetry 1.0](https://python-poetry.org/docs/#installation) or later. GNU Make can
optionally be used to quickly setup a local development environment, but this is not
required.

To setup a local development environment:

```bash
# Clone the repository...
# ...over HTTPS
git clone https://github.com/enpaul/vault2vault.git
# ...over SSH
git clone git@github.com:enpaul/vault2vault.git

cd vault2vault/

# Create and configure the local development environment...
make dev

# Run tests and CI locally...
make test

# See additional make targets
make help
```
