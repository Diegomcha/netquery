import re
from json import JSONDecodeError, load
from socket import getnameinfo
from typing import Any, Callable

from click import UsageError
from netmiko.ssh_dispatcher import CLASS_MAPPER
from rich.console import Console
from typer import Context, open_file

type Machines = dict[str, dict[str, dict[str, Any]]]


SUPPORTED_DEVICE_TYPES = CLASS_MAPPER.keys()
REGEX_DISABLE = re.compile(".*")

console = Console()


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


def validate_groups(ctx: Context, groups: list[str]) -> list[str]:
    """Validates the specified groups agains the machines file's groups.

    Args:
        ctx (Context): Context of the command.
        groups (list[str]): List of groups specified in the command.

    Raises:
        UsageError: Whenever a user-specified group does not exist in the machines file's groups.
    """
    if groups[0] == "all":
        return list(ctx.params["machines"].keys())

    if not all(group in ctx.params["machines"] for group in groups):
        raise UsageError(
            f"Some specified group is not present in the machines file.\nAvailable groups: {list(ctx.params["machines"].keys())}"
        )
    return groups


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
