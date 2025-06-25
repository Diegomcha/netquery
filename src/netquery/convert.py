import json
from enum import Enum
from typing import Annotated

from pandas import Series, read_csv
from typer import FileText, FileTextWrite, Option, Typer

from netquery.utils import console

# Creating the typer instance
app = Typer(pretty_exceptions_show_locals=False)


# Enum defining the fields of the CSV
class Field(Enum):
    FILE = "File"
    GROUP = "Group"
    LABEL = "Label"
    HOSTNAME = "Hostname"
    IP = "IP"
    DEVICE_TYPE = "Device Type"
    RESULT = "Result"
    LOG = "Log"


# Defining the command with a python decorator
@app.command()
def main(
    input: Annotated[
        FileText,
        Option(
            help="Input CSV file outputted by `netquery`.",
            prompt="Input (.csv)",
        ),
    ],
    output: Annotated[
        FileTextWrite,
        Option(
            help="Output JSON file to be used with `netquery`.",
            prompt="Output (.json)",
        ),
    ],
    groupby: Annotated[
        Field,
        Option(
            help="Field to group devices by in the output JSON.", case_sensitive=False
        ),
    ] = Field.DEVICE_TYPE,
    labelby: Annotated[
        Field,
        Option(help="Field to use as the label for each device.", case_sensitive=False),
    ] = Field.HOSTNAME,
):
    """
    Converts a CSV file outputted by `netquery` into a structured JSON format compatible with the input of `netquery`.
    """
    # Parser function
    dict = {}

    def parser(row: Series) -> Series:
        dict.setdefault(row[groupby.value], {})[row[labelby.value]] = {
            "host": row[Field.IP.value],
            "device_type": row[Field.DEVICE_TYPE.value],
        }
        return row

    try:
        # Read input
        parsed_input = read_csv(input)

        # Parse the input & output to a file
        parsed_input.apply(parser, "columns", result_type="broadcast")
        json.dump(dict, output, indent=4)

        console.print(
            f"'{input.name}' was converted to '{output.name}'",
            style="cyan",
        )
    except Exception:
        console.print(f"An error ocurred during conversion!", style="bold red")
        console.print_exception()
