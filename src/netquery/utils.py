import re
from importlib.metadata import version
from json import JSONDecodeError, load
from pathlib import Path
from re import Pattern
from socket import getnameinfo
from typing import Any, Callable, Literal, cast

import click
from click import UsageError
from netmiko.ssh_dispatcher import CLASS_MAPPER
from rich.console import Console
from typer import Context, Exit, open_file

type Machines = dict[str, dict[str, dict[str, Any]]]
type MultipleMachines = dict[str, Machines]


SUPPORTED_DEVICE_TYPES = CLASS_MAPPER.keys()

console = Console()


def parse_multiple_machines(filenames: str) -> MultipleMachines:
    """Parses multiple machines files.

    Args:
        filenames (str): Filenames comma-separated.

    Returns:
        dict[str, Machines]: Machines.
    """
    # Already parsed
    if isinstance(filenames, dict):
        return filenames

    # Parse machines
    return {filename: parse_machines(filename) for filename in filenames.split(",")}


def parse_machines(filename: str) -> Machines:
    """Parses the machines from a file into a dictionary of group>label>machine_params.

    Args:
        filename (str): Name of the file to parse.

    Raises:
        UsageError: When an error while parsing occurs.

    Returns:
        Any: Dictionary of machines.
    """

    # Already parsed
    if isinstance(filename, dict):
        return filename

    try:
        with open_file(filename) as file:
            # Parsing JSON files
            if file.name.endswith(".json"):
                return load(file)
            # Parsing TXT files into a default group
            else:
                return {
                    "default": {
                        ip.strip(): {"host": ip.strip()} for ip in file.readlines()
                    }
                }
    except (JSONDecodeError, OSError) as e:
        raise UsageError(f"Invalid machines file.\n{e}")


def parse_regex(regex: str | Pattern | None) -> re.Pattern | None:
    """Parses a regular expression into a python Pattern.

    Args:
        regex (str | Pattern | None): Regular expression string to parse.

    Raises:
        UsageError: If the regular expression is malformed.

    Returns:
        re.Pattern | None: Pattern or None if disabled.
    """
    # Already parsed
    if regex == None or isinstance(regex, Pattern):
        return regex

    # Disable
    if len(regex) == 0:
        return None

    # Compile regex
    try:
        return re.compile(regex)
    except Exception as e:
        raise UsageError(f"Error compiling regex.\n{e}")


def parse_output(
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


def parse_textfsm_template(filename: str | Path | None) -> Path | None:
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


def validate_groups(ctx: Context, groups: list[str]) -> list[str]:
    """Validates the specified groups agains the machines files' groups.

    Args:
        ctx (Context): Context of the command.
        groups (list[str]): List of groups specified in the command.

    Raises:
        UsageError: Whenever a user-specified group does not exist in the machines files' groups.
    """

    # Compute a set of all possible groups
    all_groups = set(
        [group for file in ctx.params["machines"].values() for group in file.keys()]
    )

    if groups[0] == "all":
        return list(all_groups)

    if not all(
        any(group in file for file in ctx.params["machines"].values())
        for group in groups
    ):
        raise UsageError(
            "Some specified group is not present in any of the machines files."
        )

    return list(groups)


def validate_device_type(device_type: str) -> str:
    """Validates the specified device_type against the platforms supported by `netmiko`.

    Args:
        device_type (str): Device type to validate.

    Raises:
        UsageError: Whenever the specified device type is not supported.

    Returns:
        str: The device type itself.
    """
    if device_type not in SUPPORTED_DEVICE_TYPES:
        raise UsageError(
            f"Provided invalid device_type: '{device_type}'\nAvailable device types can be found here: https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md"
        )

    return device_type


def get_hostname(ip: str) -> str:
    """Obtains the hostname of an ip using a DNS reverse lookup.

    Args:
        ip (str): IP whose hostname to obtain.

    Returns:
        str: Hostname if it was available, otherwise the IP.
    """
    hostname, _ = getnameinfo((ip, 0), 0)
    return hostname


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


def version_callback(val: bool):
    """
    Callback that displays the version of the package.
    """
    if val:
        console.print(version("netquery"), highlight=False)
        raise Exit()
