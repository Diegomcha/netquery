import json
from typing import Annotated

from pandas import read_csv
from typer import FileBinaryRead, FileText, FileTextWrite, Option, Typer

# Creating the typer instance
app = Typer(pretty_exceptions_show_locals=False)


# Defining the command with a python decorator
@app.command()
def main(
    input: Annotated[
        FileText,
        Option(
            help="Input CSV file outputted by the main utility.",
            prompt="Input (.csv)",
        ),
    ],
    output: Annotated[FileTextWrite, Option()],
):
    res = read_csv("~/app/output_cisco_wlc.csv")

    dict = {}

    def parser(r):
        dict.setdefault(r["Device Type"], {})[r["Hostname"]] = {
            "host": r["IP"],
            "device_type": r["Device Type"],
        }
        return r

    res.apply(parser, "columns")

    json.dump(dict, output, sort_keys=True, indent=2)
