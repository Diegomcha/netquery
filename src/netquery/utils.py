from io import BytesIO
from json import JSONDecodeError, load
from socket import getnameinfo
from typing import Any

from click import UsageError
from typer import Context, open_file

type Machines = dict[str, dict[str, dict[str, Any]]]


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
    except (JSONDecodeError, FileNotFoundError) as e:
        raise UsageError(f"Invalid machines file '{filename}'.\n{e}")


def validate_groups(ctx: Context, groups: list[str]) -> list[str]:
    """Validates the specified groups agains the machines file's groups.

    Args:
        ctx (Context): Context of the command.
        groups (list[str]): List of groups specified in the command.

    Raises:
        UsageError: Whenever a user-specified group does not exist in the machines file's groups.
    """
    if groups and not all(group in ctx.params["machines"] for group in groups):
        raise UsageError(
            f"Some specified group is not present in the machines file.\nAvailable groups: {list(ctx.params["machines"].keys())}"
        )
    return groups or ctx.params["machines"].keys()


def get_hostname(ip: str) -> str:
    """Obtains the hostname of an ip using a DNS reverse lookup.

    Args:
        ip (str): IP whose hostname to obtain.

    Returns:
        str: Hostname if it was available, otherwise the IP.
    """
    hostname, _ = getnameinfo((ip, 0), 0)
    return hostname


class InMemoryLog(BytesIO):
    def write(self, b):
        # Ensure bytes are written
        if isinstance(b, str):
            b = b.encode("utf-8")
        return super().write(b)
