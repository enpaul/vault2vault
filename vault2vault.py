"""CLI tool for recursively rekeying ansible-vault encrypted secrets"""
import argparse
import getpass
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import List
from typing import Optional

import ruamel.yaml

try:
    import ansible.constants
    from ansible.parsing.vault import VaultSecret
    from ansible.parsing.vault import VaultLib
    from ansible.parsing.vault import AnsibleVaultError
except ImportError:
    print(
        "FATAL: No supported version of Ansible could be imported under the current python interpreter",
        file=sys.stderr,
    )
    sys.exit(1)


__title__ = "vault2vault"
__summary__ = "Recursively rekey ansible-vault encrypted files and in-line variables"
__version__ = "0.1.1"
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
    old: VaultLib,
    new: VaultLib,
    content: bytes,
) -> bytes:
    """Rekey vaulted content to use a new vault password

    :param old: ``VaultLib`` object populated with the vault password the content is
                currently encrypted with
    :param new: ``VaultLib`` object populated with the vault password the content will
                be re-encrypted with
    :param content: Content to decrypt using ``old`` and re-encrypt using ``new``
    :returns: The value of ``content`` decrypted using the existing vault password and
              re-encrypted using the new vault password
    """
    return new.encrypt(old.decrypt(content))


# This whole function needs to be rebuilt from the ground up so I don't
# feel bad about disabling this warning
def _process_file(  # pylint: disable=too-many-statements
    path: Path,
    old: VaultLib,
    new: VaultLib,
    interactive: bool,
    backup: bool,
    ignore: bool,
) -> None:
    logger = logging.getLogger(__name__)

    logger.debug(f"Processing file {path}")

    def _process_yaml_data(  # pylint: disable=too-many-locals
        content: bytes, data: Any, ignore: bool, name: str = ""
    ):
        if isinstance(data, dict):
            for key, value in data.items():
                content = _process_yaml_data(
                    content, value, ignore, name=f"{name}.{key}"
                )
        elif isinstance(data, list):
            for index, item in enumerate(data):
                content = _process_yaml_data(
                    content, item, ignore, name=f"{name}.{index}"
                )
        elif isinstance(data, ruamel.yaml.comments.TaggedScalar) and old.is_encrypted(
            data.value
        ):
            logger.info(f"Identified vaulted content in {path} at {name}")
            confirm = (
                _confirm(f"Rekey vault encrypted variable {name} in file {path}?")
                if interactive
                else True
            )

            if not confirm:
                logger.debug(
                    f"User skipped vault encrypted content in {path} at {name} via interactive mode"
                )
                return content

            try:
                new_data = rekey(old, new, data.value.encode())
            except AnsibleVaultError as err:
                msg = f"Failed to decrypt vault encrypted data in {path} at {name} with provided vault secret"
                if ignore:
                    logger.warning(msg)
                    return content
                raise RuntimeError(msg) from err
            content_decoded = content.decode("utf-8")

            # Ok so this next section is probably the worst possible way to do this, but I did
            # it this way to solve a very specific problem that would absolutely prevent people
            # from using this tool: round trip YAML format preservation. Namely, that it's impossible.
            # Ruamel gets the closest to achieving this: it can do round trip format preservation
            # when the starting state is in _some_ known state (this is better than competitors which
            # require the starting state to be in a _specific_ known state). But given how many
            # ways there are to write YAML- and by extension, how many opinions there are on the
            # "correct" way to write YAML- it is not possible to configure ruamel to account for all of
            # them, even if everyones YAML style was compatible with ruamel's roundtrip formatting (note:
            # they aren't). So there's the problem: to be useful, this tool would need to reformat every
            # YAML file it touched, which means nobody would use it.
            #
            # To avoid the YAML formatting problem, we need a way to replace the target content
            # in the raw text of the file without dumping the parsed YAML. We want to preserve
            # indendation, remove any extra newlines that would be left over, add any necessary
            # newlines without clobbering the following lines, and ideally avoid reimplementing
            # a YAML formatter. The answer to this problem- as the answer to so many stupid problems
            # seems to be- is a regex. If this is too janky for you (I know it is for me) go support
            # the estraven project I'm trying to get off the ground: https://github.com/enpaul/estraven
            #
            # Ok, thanks for sticking with me as I was poetic about this. The solution below...
            # is awful, I can admit that. But it does work, so I'll leave it up to
            # your judgement as to whether it's worthwhile or not. Here's how it works:
            #
            # 1. First we take the first line of the original (unmodified) vaulted content. This line
            #    of text has several important qualities: 1) it exists in the raw text of the file, 2)
            #    it is pseudo-guaranteed to be unique, and 3) it is guaranteed to exist (vaulted content
            #    will be at least one line long, but possibly no more)
            search_data = data.value.split("\n")[1]
            try:
                # 2. Next we use a regex to grab the full line of text from the file that includes the above
                #    string. This is important because the full line of text will include the leading
                #    whitespace, which ruamel helpfully strips out from the parsed data.
                # 3. Next we grab the number of leading spaces on the line using the capture group from the
                #    regex
                padding = len(
                    re.search(rf"\n(\s*){search_data}\n", content_decoded).groups()[0]
                )
            except (TypeError, AttributeError):
                # This is to handle an edgecase where the vaulted content is actually a yaml anchor. For
                # example, if a single vaulted secret needs to be stored under multiple variable names.
                # In that case, the vaulted content iself will only appear once in the file, but the data
                # parsed by ruamel will include it twice. If we fail to get a match on the first line, then
                # we check whether the data is a yaml anchor and, if it is, we skip it.
                if data.anchor.value:
                    logger.debug(
                        f"Content replacement for encrypted content in {path} at {name} was not found, so replacement will be skipped because target is a YAML anchor"
                    )
                    return content
                raise

            # 4. Now with the leading whitespace padding, we add this same number of spaces to each line
            #    of *both* the old vaulted data and the new vaulted data. It's important to do both because
            #    we'll need to do a replacement in a moment so we need to know both what we're replacing
            #    and what we're replacing it with.
            padded_old_data = "\n".join(
                [f"{' ' * padding}{item}" for item in data.value.split("\n") if item]
            )
            padded_new_data = "\n".join(
                [
                    f"{' ' * padding}{item}"
                    for item in new_data.decode("utf-8").split("\n")
                    if item
                ]
            )

            # 5. Finally, we actually replace the content. This needs to have a count=1 so that if the same
            #    encrypted block appears twice in the same file we only replace the first occurance of it,
            #    otherwise the later replacement attempts will fail. We also need to re-encode it back to
            #    bytes because all file operations with vault are done in bytes mode
            content = content_decoded.replace(
                padded_old_data, padded_new_data, 1
            ).encode()
        return content

    with path.open("rb") as infile:
        raw = infile.read()

    # The 'is_encrypted' check doesn't rely on the vault secret in the VaultLib matching the
    # secret the data was encrypted with, it just checks that the data is encrypted with some
    # vault secret. We could use either `old` or `new` for this check, it doesn't actually matter.
    if old.is_encrypted(raw):
        logger.info(f"Identified vault encrypted file: {path}")

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
        except AnsibleVaultError:
            msg = f"Failed to decrypt vault encrypted file {path} with provided vault secret"
            if ignore:
                logger.warning(msg)
                return
            raise RuntimeError(msg) from None
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

        updated = _process_yaml_data(raw, data, ignore=ignore)
    else:
        logger.debug(f"Skipping non-vault file {path}")
        return

    logger.debug(f"Writing updated file contents to {path}")

    with path.open("wb") as outfile:
        outfile.write(updated)


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


def _expand_paths(paths: Iterable[Path]) -> List[Path]:
    logger = logging.getLogger(__name__)

    results = []
    for path in paths:
        path = Path(path).resolve()
        if path.is_file():
            logger.debug(f"Including file {path}")
            results.append(path)
        elif path.is_dir():
            logger.debug(f"Identifying files under {path}")
            results += _expand_paths(path.iterdir())
        else:
            logger.debug(f"Discarding path {path}")
    return results


def _load_password(
    fpath: Optional[str], desc: str = "", confirm: bool = True
) -> VaultSecret:
    """Load a password from a file or interactively

    :param fpath: Optional path to the file containing the vault password. If not provided then
                  the password will be prompted for interactively.
    :param desc: Description text to inject into the interactive password prompt. Useful when using
                 this function multiple times to identify different passwords to the user.
    :returns: Populated vault secret object with the loaded password
    """

    logger = logging.getLogger(__name__)

    if fpath:
        try:
            with Path(fpath).resolve().open("rb", encoding="utf-8") as infile:
                return VaultSecret(infile.read())
        except (FileNotFoundError, PermissionError) as err:
            raise RuntimeError(
                f"Specified vault password file '{fpath}' does not exist or is unreadable"
            ) from err

    logger.debug("No vault password file provided, prompting for interactive input")

    password_1 = getpass.getpass(
        prompt=f"Enter {desc} Ansible Vault password: ", stream=sys.stderr
    )

    if confirm:
        password_2 = getpass.getpass(
            prompt=f"Confirm (re-enter) {desc} Ansible Vault password: ",
            stream=sys.stderr,
        )

        if password_1 != password_2:
            raise RuntimeError(f"Provided {desc} passwords do not match")

    return VaultSecret(password_1.encode("utf-8"))


def main():
    """Main program entrypoint and CLI interface"""
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
        logger.warning("No paths provided, nothing to do!")
        sys.exit(0)

    try:
        old_pass = _load_password(args.old_pass_file, desc="existing", confirm=False)
        new_pass = _load_password(args.new_pass_file, desc="new", confirm=True)

        in_vault = VaultLib([(args.vault_id, old_pass)])
        out_vault = VaultLib([(args.vault_id, new_pass)])
    except RuntimeError as err:
        logger.error(str(err))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)

    logger.info(
        f"Identifying all files under {len(args.paths)} input paths: {', '.join(args.paths)}"
    )
    files = _expand_paths(args.paths)
    logger.info(f"Identified {len(files)} files for processing")

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
