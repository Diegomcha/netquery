import json
import re
from socket import getnameinfo
from typing import IO, Any, Optional

from netmiko.ssh_dispatcher import CLASS_MAPPER

# Custom types
type Machines = dict[str, dict[str, dict[str, Any]]]
type MultipleMachines = dict[str, Machines]


SUPPORTED_DEVICE_TYPES = CLASS_MAPPER.keys()


# Helper class to unify web/cli file interfaces
class NamedStream:
    def __init__(self, stream: IO, name: Optional[str] = None):
        self.stream = stream
        self.name = name or stream.name

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def parse_machines_multiple(
    files: list[NamedStream],
) -> MultipleMachines:
    """Parses multiple machines files.

    Args:
        files (list[NamedStream]): List of files.

    Returns:
        MultipleMachines: Dictionary of machines dictionary.
    """
    return {file.name: parse_machines(file) for file in files}


def _decode_str(string: str | bytearray) -> str:
    return string if isinstance(string, str) else string.decode("utf-8")


def parse_machines(file: NamedStream) -> Machines:
    """Parses the machines from a file into a dictionary of group>label>machine_params.

    Args:
        file (NamedStream): File to parse.

    Returns:
        Machines: Dictionary of machines.
    """
    with file.stream:
        # Parsing JSON files
        if file.name.endswith(".json"):
            return json.load(file.stream)
        # Parsing TXT files into a default group
        else:
            return {
                "default": {
                    _decode_str(ip).strip(): {"host": _decode_str(ip).strip()}
                    for ip in file.stream.readlines()
                }
            }


def parse_regex(regex: str) -> re.Pattern | None:
    """Parses a regular expression into a python Pattern.

    Args:
        regex (str): Regular expression string to parse.

    Returns:
        re.Pattern | None: Pattern or None if disabled.
    """

    # Disable
    if len(regex) == 0:
        return None

    # Compile regex
    return re.compile(regex)


def validate_groups(machines: MultipleMachines, groups: list[str]) -> list[str]:
    """Validates the specified groups agains the machines files' groups.

    Args:
        ctx (Context): Context of the command.
        groups (list[str]): List of groups specified in the command.

    Raises:
        KeyError: Whenever a user-specified group does not exist in the machines files' groups.
    """

    # Compute a set of all possible groups
    all_groups = set([group for file in machines.values() for group in file.keys()])

    if groups[0] == "all":
        return list(all_groups)

    if not all(any(group in file for file in machines.values()) for group in groups):
        raise KeyError(
            "Some specified group is not present in any of the machines files."
        )

    return list(groups)


def validate_device_type(device_type: str) -> str:
    """Validates the specified device_type against the platforms supported by `netmiko`.

    Args:
        device_type (str): Device type to validate.

    Raises:
        ValueError: Whenever the specified device type is not supported.

    Returns:
        str: The device type itself.
    """
    if device_type not in SUPPORTED_DEVICE_TYPES:
        raise ValueError(
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
