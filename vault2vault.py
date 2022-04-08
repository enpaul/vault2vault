"""CLI tool for recursively rekeying ansible-vault encrypted secrets"""
import argparse
import getpass
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from typing import List
from typing import Sequence
from typing import Tuple
from typing import Union

import ansible.constants
import ansible.parsing.vault
import ruamel.yaml


__title__ = "vault2vault"
__summary__ = "Recursively rekey ansible-vault encrypted files and in-line variables"
__version__ = "0.1.0"
__url__ = "https://github.com/enpaul/vault2vault/"
__license__ = "MIT"
__authors__ = ["Ethan Paul <24588726+enpaul@users.noreply.github.com>"]


YAML_FILE_EXTENSIONS = (".yml", ".yaml")

yaml = ruamel.yaml.YAML(typ="rt")

ruamel.yaml.add_constructor(
    "!vault",
    lambda loader, node: node.value,
    constructor=ruamel.yaml.SafeConstructor,
)


def rekey(
    old: ansible.parsing.vault.VaultLib,
    new: ansible.parsing.vault.VaultLib,
    content: bytes,
) -> bytes:
    return new.encrypt(old.decrypt(content))


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=__title__,
        description=__summary__,
    )

    parser.add_argument(
        "--version", help="Show program version and exit", action="store_true"
    )
    parser.add_argument(
        "--interactive",
        help="Step through files and variables interactively, prompting for confirmation before making each change",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase verbosity; can be repeated",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-b",
        "--backup",
        help="Write a backup of every file to be modified, suffixed with '.bak'",
        action="store_true",
    )
    parser.add_argument(
        "-i",
        "--vault-id",
        help="Limit rekeying to encrypted secrets with the specified Vault ID",
        type=str,
        default=ansible.constants.DEFAULT_VAULT_IDENTITY,
    )
    parser.add_argument(
        "--ignore-undecryptable",
        help="Ignore any file or variable that is not decryptable with the provided vault secret instead of raising an error",
        action="store_true",
    )
    parser.add_argument(
        "--old-pass-file",
        help="Path to a file with the old vault password to decrypt secrets with",
        type=str,
        dest="old_pass_file",
    )
    parser.add_argument(
        "--new-pass-file",
        help="Path to a file with the new vault password to rekey secrets with",
        type=str,
        dest="new_pass_file",
    )
    parser.add_argument(
        "paths", help="Paths to search for Ansible Vault encrypted content", nargs="*"
    )

    return parser.parse_args()


def _confirm(prompt: str, default: bool = True) -> bool:
    while True:
        confirm = input(f"{prompt} [{'YES/no' if default else 'yes/NO'}]: ")
        if not confirm:
            return default
        if confirm.lower() in ["yes", "y"]:
            return True
        if confirm.lower() in ["no", "n"]:
            return False
        print("Please input one of the specified options", file=sys.stderr)


def _process_file(
    path: Path,
    old: ansible.parsing.vault.VaultLib,
    new: ansible.parsing.vault.VaultLib,
    interactive: bool,
    backup: bool,
    ignore: bool,
) -> None:
    logger = logging.getLogger(__name__)

    logger.debug(f"Processing file {path}")

    def _process_yaml_data(content: bytes, data: Any, name: str = ""):
        if isinstance(data, dict):
            for key, value in data.items():
                content = _process_yaml_data(content, value, f"{name}.{key}")
        elif isinstance(data, list):
            for index, item in enumerate(data):
                content = _process_yaml_data(content, item, f"{name}.{index}")
        elif isinstance(data, ruamel.yaml.comments.TaggedScalar):
            if old.is_encrypted(data.value):
                logger.debug(f"Identified vaulted content in {path} at '{name}'")
                confirm = (
                    _confirm(f"Rekey vault encrypted variable {name} in file {path}?")
                    if interactive
                    else True
                )

                if not confirm:
                    logger.debug(
                        f"User skipped vault encrypted content in {path} at '{name}' via interactive mode"
                    )
                    return content

                new_data = rekey(old, new, data.value.encode())
                content_decoded = content.decode("utf-8")

                search_data = data.value.split("\n")[1]
                try:
                    padding = len(
                        re.search(rf"\n(\s*){search_data}\n", content_decoded).groups()[
                            0
                        ]
                    )
                except (TypeError, AttributeError):
                    if data.anchor.value:
                        logger.debug(
                            f"Content replacement for encrypted content in {path} at {name} was not found, so replacement will be skipped because target is a YAML anchor"
                        )
                        return content
                    raise

                padded_old_data = "\n".join(
                    [
                        f"{' ' * padding}{item}"
                        for item in data.value.split("\n")
                        if item
                    ]
                )
                padded_new_data = "\n".join(
                    [
                        f"{' ' * padding}{item}"
                        for item in new_data.decode("utf-8")
                        if item
                    ]
                )

                content = content_decoded.replace(
                    padded_old_data, padded_new_data
                ).encode()
        return content

    with path.open("rb") as infile:
        raw = infile.read()

    # The 'is_encrypted' check doesn't rely on the vault secret in the VaultLib matching the
    # secret the data was encrypted with, it just checks that the data is encrypted with some
    # vault secret. We could use either `old` or `new` for this check, it doesn't actually matter.
    if old.is_encrypted(raw):
        logger.debug(f"Identified vault encrypted file: {path}")

        confirm = (
            _confirm(f"Rekey vault encrypted file {path}?") if interactive else True
        )

        if not confirm:
            logger.debug(
                f"User skipped vault encrypted file {path} via interactive mode"
            )
            return

        if backup:
            path.rename(f"{path}.bak")

        try:
            updated = rekey(old, new, raw)
        except ansible.parsing.vault.AnsibleVaultError:
            msg = f"Failed to decrypt vault encrypted file {path} with provided vault secret"
            if ignore:
                logger.warning(msg)
                return
            raise RuntimeError(msg)
    elif path.suffix.lower() in YAML_FILE_EXTENSIONS:
        logger.debug(f"Identified YAML file: {path}")

        confirm = (
            _confirm(f"Search YAML file {path} for vault encrypted variables?")
            if interactive
            else True
        )

        data = yaml.load(raw)

        if not confirm:
            logger.debug(
                f"User skipped processing YAML file {path} via interactive mode"
            )
            return

        if backup:
            shutil.copy(path, f"{path}.bak")

        updated = _process_yaml_data(raw, data)
    else:
        logger.debug(f"Skipping non-vault file {path}")
        return

    logger.debug(f"Writing updated file contents to {path}")

    with path.open("wb") as outfile:
        outfile.write(updated)


def _expand_paths(paths: Sequence[Union[Path, str]]) -> List[Path]:
    logger = logging.getLogger(__name__)

    results = []
    for path in paths:
        path = Path(path).resolve()
        if path.is_file():
            logger.debug(f"Including file {path}")
            results.append(path)
        elif path.is_dir():
            logger.debug(f"Descending into subdirectory {path}")
            results += _expand_paths(path.iterdir())
        else:
            logger.debug(f"Discarding path {path}")
    return results


def _read_vault_pass_file(path: Union[Path, str]) -> str:
    logger = logging.getLogger(__name__)
    try:
        with Path(path).resolve().open() as infile:
            return infile.read()
    except (FileNotFoundError, PermissionError):
        logger.error(
            f"Specified vault password file '{path}' does not exist or is unreadable"
        )
        sys.exit(1)


def _load_passwords(
    old_file: str, new_file: str
) -> Tuple[ansible.parsing.vault.VaultSecret, ansible.parsing.vault.VaultSecret]:
    logger = logging.getLogger(__name__)

    if old_file:
        old_vault_pass = _read_vault_pass_file(old_file)
        logger.info(f"Loaded old vault password from {Path(old_file).resolve()}")
    else:
        logger.debug(
            "No old vault password file provided, prompting for old vault password input"
        )
        old_vault_pass = getpass.getpass(
            prompt="Old Ansible Vault password: ", stream=sys.stderr
        )

    if new_file:
        new_vault_pass = _read_vault_pass_file(new_file)
        logger.info(f"Loaded new vault password from {Path(new_file).resolve()}")
    else:
        logger.debug(
            "No new vault password file provided, prompting for new vault password input"
        )
        new_vault_pass = getpass.getpass(
            prompt="New Ansible Vault password: ", stream=sys.stderr
        )
        confirm = getpass.getpass(
            prompt="Confirm new Ansible Vault password: ", stream=sys.stderr
        )
        if new_vault_pass != confirm:
            logger.error("New vault passwords do not match")
            sys.exit(1)

    return ansible.parsing.vault.VaultSecret(
        old_vault_pass.encode("utf-8")
    ), ansible.parsing.vault.VaultSecret(new_vault_pass.encode("utf-8"))


def main():
    args = _get_args()

    logger = logging.getLogger(__name__)

    logging.basicConfig(
        stream=sys.stderr,
        format="%(levelname)s: %(message)s",
        level=max(logging.WARNING - (args.verbose * 10), 0),
    )

    if args.version:
        print(f"{__title__} {__version__}")
        sys.exit(0)

    if not args.paths:
        logger.warning("No path provided, nothing to do!")
        sys.exit(0)

    old_pass, new_pass = _load_passwords(args.old_pass_file, args.new_pass_file)
    in_vault = ansible.parsing.vault.VaultLib([(args.vault_id, old_pass)])
    out_vault = ansible.parsing.vault.VaultLib([(args.vault_id, new_pass)])

    logger.debug(
        f"Identifying all files under {len(args.paths)} input paths: {', '.join(args.paths)}"
    )
    files = _expand_paths(args.paths)

    for filepath in files:
        _process_file(
            filepath,
            in_vault,
            out_vault,
            args.interactive,
            args.backup,
            args.ignore_undecryptable,
        )


if __name__ == "__main__":
    main()
