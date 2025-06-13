import os
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO, StringIO
from json import dump, dumps
from typing import Annotated, Any

from click import UsageError
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoBaseException,
    NetmikoTimeoutException,
    SSHDetect,
)
from pandas import DataFrame
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.traceback import install
from tabulate import tabulate
from typer import Option, Typer, echo, prompt, style

from netquery.utils import Machines, parse_machines, validate_groups

install(show_locals=False)

app = Typer()


class Mode(str, Enum):
    I = "i"
    INCLUDE = "include"
    E = "e"
    EXCLUDE = "exclude"
    B = "b"
    BEGIN = "begin"
    SECTION = "section"
    GREP = "grep"
    DISABLE = "disable"

    def __str__(self) -> str:
        return self.value


# Command that does the querying
@app.command()
def query(
    machines: Annotated[
        Machines,
        Option(
            prompt="Machines file (.txt or .json)",
            help="File where the machines are specified. It may be *.json or *.txt.",
            parser=parse_machines,
            metavar="FILENAME",
        ),
    ],
    username: Annotated[
        str,
        Option(
            prompt="Username",
            hide_input=True,
            help="Username used to authenticate into the machines.",
        ),
    ],
    password: Annotated[
        str,
        Option(
            prompt="Password",
            hide_input=True,
            help="Password used to authenticate into the machines.",
        ),
    ],
    cmd: Annotated[
        str,
        Option(prompt="Command", help="Command that will be executed. Can be ommited"),
    ] = "",
    mode: Annotated[
        Mode,
        Option(
            prompt="Searching mode",
            prompt_required=True,
            help="Filtering mode that will be applied. 'disable' means filtering is disabled.",
        ),
    ] = Mode.DISABLE,
    term: Annotated[
        str,
        Option(
            prompt="Searching term",
            prompt_required=True,
            help="Term to use to filter the results. When mode is 'disable', this option serves no purpose.",
        ),
    ] = "",
    device_type: Annotated[
        str,
        Option(
            metavar="DEVICE_TYPE",
            help="Default device type to use for the devices with no explicit 'device_type'. Avoid using default 'autodetect' as it is too slow.",
            prompt="Default device type",
        ),
    ] = "autodetect",
    textfsm_template: Annotated[
        str,
        Option(
            metavar="FILENAME",
            help="TextFSM template to use for parsing the output. Only works when 'cmd' is set.",
            prompt="TextFSM template",
        ),
    ] = "",
    groups: Annotated[
        Any,
        Option(
            parser=lambda groups: groups.split(","),
            callback=validate_groups,
            metavar="GROUP1,GROUP2,...",
            help="Allows specifying which groups of machines should be queried.",
            show_default="All groups",
        ),
    ] = None,
    multiple: Annotated[
        bool, Option(help="Whether to allow multiple queries interactively.")
    ] = True,
    output: Annotated[
        str | None,
        Option(
            metavar="[FILENAME.html|FILENAME.json|FILENAME.csv|FILENAME.txt|False]",
            show_default="dynamic",
            help="Filename where the results of the query will be outputted or 'False' to disable.",
        ),
    ] = None,
):
    """
    Query a set of machines using SSH and run a specified command, optionally filtering results by search term and mode.

    - You can specify machines via a .txt or .json file, authenticate with a username and password, and run a command across selected machine groups.

    - Results are displayed in a formatted table and can be saved in various formats (CSV, HTML, JSON, TXT).

    - Supports repeated queries in a single session.
    """

    # Query machines
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
    ) as prog:
        for group in prog.track(groups, description="Querying..."):
            for label, machine in prog.track(
                machines[group].items(), description=f"· {group}"
            ):
                with BytesIO() as log:
                    device = {
                        **{
                            "username": username,
                            "password": password,
                            "device_type": device_type,
                            "session_log": log,
                        },
                        **machine,
                    }
                    try:
                        if device["device_type"] == "autodetect":
                            device["device_type"] = SSHDetect(**device).autodetect()

                        if not device["device_type"]:
                            result = "❓ Unknown"
                            prog.console.print(
                                f"Unknown device type '{label} ({machine['host']})'!",
                                style="bold red",
                            )
                        else:
                            with ConnectHandler(**device) as con:
                                if len(cmd) > 0:
                                    result = con.send_command(
                                        (
                                            f"{cmd} | {mode.value} {term}"
                                            if mode is not Mode.DISABLE
                                            else cmd
                                        ),
                                        use_textfsm=len(textfsm_template) > 0,
                                        textfsm_template=textfsm_template,
                                        raise_parsing_error=True,
                                    )
                                    if isinstance(result, (list, dict)):
                                        result = dumps(result)
                                else:
                                    result = "✅ Accessible"

                    except NetmikoAuthenticationException:
                        result = "⛔ Unauthorized"
                        prog.console.print(
                            f"Authentication failure at '{label} ({machine['host']})'!",
                            style="bold red",
                        )
                    except NetmikoTimeoutException:
                        result = "⌛ Timeout"
                        prog.console.print(
                            f"Failed to connect to '{label} ({machine['host']})'!",
                            style="bold red",
                        )
                    except Exception as e:
                        result = "🔥 Exception"
                        prog.console.print(
                            f"Unknown error from '{label} ({machine['host']})'!\n\n{e}",
                            style="bold red",
                        )

                    results.append(
                        [
                            group,
                            label,
                            device["host"],
                            device["device_type"],
                            result,
                            log.getvalue().decode(),
                        ]
                    )

    # Sort table of results
    df = DataFrame(
        results, columns=["Group", "Label", "IP", "Device Type", "Result", "Log"]
    ).sort_values(["Result", "Group", "Label", "IP", "Device Type"])[
        ["Result", "Group", "Label", "IP", "Device Type", "Log"]
    ]

    # Clean table for display
    df_clean = df.copy()
    df_clean.loc[df_clean["Result"].duplicated(), "Result"] = '"'
    df_clean["Group"] = df.groupby("Result")["Group"].transform(
        lambda x: x.mask(x.duplicated(), '"')
    )
    df_clean = df_clean.drop("Log", axis="columns")
    if len(groups) == 1:
        df_clean = df_clean.drop("Group", axis="columns")

    # Display
    echo(
        style(
            f"Result of {style(cmd, italic=True, fg="reset")}",
            bold=True,
            fg="cyan",
        )
    )
    echo(
        tabulate(
            df_clean.values.tolist(),
            df_clean.columns.to_list(),
            "rounded_grid",
            showindex=True,
        )
    )

    # Handle writting output
    filename: str = output or prompt(
        "Output (.html .csv .json .txt False)",
        default=f"{cmd.replace(" ", "_") if len(cmd)  > 0 else "accessible"}{f"_{mode.value}_{term.replace(" ", "_")}" if mode.value != Mode.DISABLE else ""}__{datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")}.csv",
        type=str,
    )
    if filename != "False":
        if filename.endswith("html"):
            df.to_html(filename)
        elif filename.endswith("csv"):
            df.to_csv(filename)
        elif filename.endswith("json"):
            df.to_json(filename)
        elif filename.endswith("txt"):
            df.to_string(filename)
        else:
            echo(
                style("Unknown extension, outputted in TXT format.", fg="yellow"),
                err=True,
            )
        echo(
            style(
                f"Output written to {style(filename, italic=True, fg="reset")}",
                fg="cyan",
                bold=True,
            )
        )

    # Handle running multiple queries
    if multiple and prompt("Do you want to run another query?", False, type=bool):
        query(
            machines,
            username,
            password,
            prompt("Command", cmd),
            prompt("Mode", mode.value, type=Mode),
            prompt("Term", term),
            groups,
        )
