from json import JSONDecodeError
from pathlib import Path
from re import Pattern
from typing import Callable, Literal, cast

import click
from click import UsageError
from netmiko.ssh_dispatcher import CLASS_MAPPER
from rich.console import Console
from typer import Context, open_file

from netquery.utils_new import (
    MultipleMachines,
    NamedStream,
    parse_machines_multiple,
    parse_regex,
    validate_device_type,
    validate_groups,
)

SUPPORTED_DEVICE_TYPES = CLASS_MAPPER.keys()

console = Console()


def cli_parse_machines_files(filenames: str) -> MultipleMachines:
    # Already parsed
    if isinstance(filenames, dict):
        return filenames

    # Parse machines
    try:
        return parse_machines_multiple(
            [NamedStream(open_file(filename)) for filename in filenames.split(",")]
        )
    except (JSONDecodeError, OSError) as e:
        raise UsageError(f"Invalid machines file.\n{e}")


def cli_parse_regex(regex: str | Pattern | None) -> Pattern | None:
    # Already parsed
    if regex == None or isinstance(regex, Pattern):
        return regex

    # Parse regex
    try:
        return parse_regex(regex)
    except Exception as e:
        raise UsageError(f"Invalid regex.\n{e}")


def cli_validate_groups(ctx: Context, groups: list[str]) -> list[str]:
    try:
        return validate_groups(ctx.params["machines"], groups)
    except KeyError as e:
        raise UsageError(repr(e))


def cli_validate_device_type(device_type: str) -> str:
    try:
        return validate_device_type(device_type)
    except ValueError as e:
        raise UsageError(repr(e))


def cli_parse_output(
    filename: str | Path | Literal[False] | None,
) -> Path | Literal[False] | None:
    """Parses the output filename into a Path and verifies whether the file is writable.

    Args:
        filename (str | Path | Literal[False] | None): Filename to parse.

    Returns:
        Path | Literal[False] | None: Path, False if disabled or None if undefined.
    """
    # Already parsed
    if not isinstance(filename, str):
        return filename

    # Disable
    if filename == "False":
        return False

    # Perform validation
    return cast(
        Path,
        click.Path(
            file_okay=True,
            dir_okay=False,
            writable=True,
            readable=False,
            allow_dash=True,
            path_type=Path,
        ).convert(filename, None, None),
    )


def cli_parse_textfsm_template(filename: str | Path | None) -> Path | None:
    """Parses the filename into a Path and verifies the file is readable.

    Args:
        filename (str | Path | None): Filename to parse.

    Returns:
        Path | None: Path or None if disabled.
    """
    # Already parsed
    if not isinstance(filename, str):
        return filename

    # Disable
    if len(filename) == 0:
        return None

    # Perform validation
    return cast(
        Path,
        click.Path(
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            allow_dash=True,
            path_type=Path,
        ).convert(filename, None, None),
    )


def safe_splitter(sep: str) -> Callable[[str | list[str]], list[str]]:
    """
    Returns a parser function that safely splits a string by a given separator, or returns the input unchanged if it's already a list.

    Used for Typer, where arguments may be parsed multiple times (e.g., once as a string and again by a custom parser), which can lead to errors if not handled properly.

    Args:
        sep (str): The separator to use when splitting a string input.

    Returns:
        Callable[[str | list[str]], list[str]]: A function that takes either a comma-separated string or a list of strings and returns a list of strings.

    """
    return lambda arr: arr.split(sep) if isinstance(arr, str) else arr
