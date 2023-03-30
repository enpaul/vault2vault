# vault2vault

Like
[`ansible-vault rekey`](https://docs.ansible.com/ansible/latest/cli/ansible-vault.html#rekey)
but works recursively on encrypted files and in-line variables

[![CI Status](https://github.com/enpaul/vault2vault/workflows/CI/badge.svg?event=push)](https://github.com/enpaul/vault2vault/actions)
[![PyPI Version](https://img.shields.io/pypi/v/vault2vault)](https://pypi.org/project/vault2vault/)
[![License](https://img.shields.io/pypi/l/vault2vault)](https://opensource.org/licenses/MIT)
[![Python Supported Versions](https://img.shields.io/pypi/pyversions/vault2vault)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

⚠️ **This project is beta software and is under active development** ⚠️

- [What is this?](#what-is-this)
- [Installing](#installing)
- [Usage](#usage)
  - [Recovering from a failed migration](#recovering-from-a-failed-migration)
- [Roadmap](#roadmap)
- [Developing](#developer-documentation)

## What is this?

If you use [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
then you may have encountered the problem of needing to roll your vault password. Maybe
you found it written down on a sticky note, maybe a coworker who knows it left the
company, maybe you accidentally typed it into Slack when you thought the focus was on your
terminal. Whatever, these things happen.

The built-in tool Ansible provides,
[`ansible-vault rekey`](https://docs.ansible.com/ansible/latest/cli/ansible-vault.html#rekey),
suffers from two main drawbacks: first, it only works on vault encrypted files and not on
vault encrypted YAML data; and second, it only works on a single vault encrypted file at a
time. To rekey everything in a large project you'd need to write a script that recursively
goes through every file and rekeys every encrypted file and YAML variable all at once.

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

> Note: vault2vault requires an Ansible installation to function. If you are installing to
> a standalone virtual environment (like with PipX) then you must install it with the
> `ansible` extra to ensure a version of Ansible is available to the application.\*\*

## Usage

> Note: the full command reference is available by running `vault2vault --help`

Vault2Vault works with files in any arbitrary directory structures, so there is no need to
have your Ansible project(s) structured in a specific way for the tool to work. The
simplest usage of Vault2Vault is by passing the path to your Ansible project directory to
the command:

```bash
vault2vault ./my-ansible-project/
```

The tool will prompt for the current vault password and the new vault password and then
process every file under the provided path. You can also specify multiple paths and
they'll all be processed together:

```bash
vault2vault \
  ./my-ansible-project/playbooks/ \
  ./my-ansible-project/host_vars/ \
  ./my-ansible-project/group_vars/
```

To skip the interactive password prompts you can put the password in a file and have the
tool read it in at runtime. The `--old-pass-file` and `--new-pass-file` parameters work
the same way as the `--vault-password-file` option from the `ansible` command:

```bash
vault2vault ./my-ansible-project/ \
  --old-pass-file=./oldpass.txt \
  --new-pass-file=./newpass.txt
```

If you use multiple vault passwords in your project and want to roll them you'll need to
run `vault2vault` once for each password you want to change. By default, `vault2vault`
will fail with an error if it encounters vaulted data that it cannot decrypt with the
provided current vault password. To change this behavior and instead just ignore any
vaulted data that can't be decrypted (like, for example, if you have data encrypted with
multiple vault passwords) you can pass the `--ignore-undecryptable` flag to turn the
errors into warnings.

> Please report any bugs or issues you encounter on
> [Github](https://github.com/enpaul/vault2vault/issues).

### Recovering from a failed migration

This tool is still pretty early in it's development, and to be honest it hooks into
Ansible's functionality in some fragile ways. I've tested as best I can to ensure it
covers as many edge cases as possible, but there is still the chance that you might get
partway through a password migration and then have the tool fail out, leaving half of your
data successfully rekeyed and the other half not.

In the spirit of the
[Unix philosophy](https://hackaday.com/2018/09/10/doing-one-thing-well-the-unix-philosophy/)
this tool does not include any built-in way to recover from this state. However, it can be
done very effectively using a version control tool.

If you are using Git to track your project files then you can use the command
`git reset --hard` to restore all files to the state of the currently checked out commit.
This does have the side effect of erasing any other un-committed work in the repository,
so it's recommended to always have a clean working tree when using Vault2Vault.

If you are not using a version control system to track your project files then you can
create a temporary Git repository to use in the event of a migration failure:

```bash
cd my-project/

# Initialize the new repository
git init

# Add and commit all your existing files to the git tree
git add .
git commit -m "initial commit"

# Run vault migrations
vault2vault ...

# If no recovery is necessary, delete the git repository data
rm -rf .git
```

## Roadmap

This project is considered feature complete as of the
[0.1.1](https://github.com/enpaul/vault2vault/releases/tag/0.1.1) release. As a result the
roadmap focuses on stability and user experience ahead of a 1.0 release.

- [ ] Reimplement core vaulted data processing function to enable multithreading
- [ ] Implement multithreading for performance in large environments
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Redesign logging messages to improve clarity and consistency

## Developer Documentation

All project contributors and participants are expected to adhere to the
[Contributor Covenant Code of Conduct, v2](CODE_OF_CONDUCT.md)
([external link](https://www.contributor-covenant.org/version/2/0/code_of_conduct/)).

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
