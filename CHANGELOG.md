# changelog

See also: [Github Release Page](https://github.com/enpaul/vault2vault/releases).

## Version 0.1.4

View this release on: [Github](https://github.com/enpaul/vault2vault/releases/tag/0.1.4),
[PyPI](https://pypi.org/project/vault2vault/0.1.4/)

- Fix not stripping newlines from vault password files. (#5)

## Version 0.1.3

View this release on: [Github](https://github.com/enpaul/vault2vault/releases/tag/0.1.3),
[PyPI](https://pypi.org/project/vault2vault/0.1.3/)

- Fix incorrect encoding specification when opening password files. Contributed by
  [brycelowe](https://github.com/brycelowe) (#2)

## Version 0.1.2

View this release on: [Github](https://github.com/enpaul/vault2vault/releases/tag/0.1.2),
[PyPI](https://pypi.org/project/vault2vault/0.1.2/)

- Add user documentation
- Add project road map
- Fix incorrect and missing docstrings for internal functions

## Version 0.1.1

View this release on: [Github](https://github.com/enpaul/vault2vault/releases/tag/0.1.1),
[PyPI](https://pypi.org/project/vault2vault/0.1.1/)

- Fix bug causing stack trace when the same vaulted block appears in a YAML file more than
  once
- Fix bug where the `--ignore-undecryptable` option was not respected for vaulted
  variables in YAML files
- Update logging messages and levels to improve verbose output

## Version 0.1.0

View this release on: [Github](https://github.com/enpaul/vault2vault/releases/tag/0.1.0),
[PyPI](https://pypi.org/project/vault2vault/0.1.0/)

- Add support for recursively re-keying vaulted content in files and YAML variables
