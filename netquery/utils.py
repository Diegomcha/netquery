from json import JSONDecodeError, load
from typing import Any

from click import UsageError
from typer import open_file

DEFAULT_DEVICE_TYPE = "cisco_ios"

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
