from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from click import UsageError
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
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
from tabulate import tabulate
from typer import Context, Option, Typer, echo, prompt, style

from netquery.utils import (
    DEFAULT_DEVICE_TYPE,
    Machines,
    parse_machines,
    validate_groups,
)

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
        Option(prompt="Command", help="Command that will be executed."),
    ],
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
                try:
                    # continue
                    with ConnectHandler(
                        **{
                            "username": username,
                            "password": password,
                            "device_type": DEFAULT_DEVICE_TYPE,
                        },
                        **machine,
                    ) as con:
                        results.append(
                            [
                                group,
                                label,
                                machine["host"],
                                con.send_command(
                                    f"{cmd} | {mode.value} {term}"
                                    if mode is not Mode.DISABLE
                                    else cmd
                                ),
                            ]
                        )
                except NetmikoAuthenticationException as e:
                    prog.console.print(
                        f"Authentication failure at '{label} ({machine['host']})'!",
                        style="bold red",
                    )
                except NetmikoTimeoutException as e:
                    prog.console.print(
                        f"Failed to connect to '{label} ({machine['host']})'!",
                        style="bold red",
                    )
                except Exception as e:
                    raise UsageError(
                        f"Error running command in machine '{label} ({machine['host']})':\n{e}"
                    )

    # Sort table of results
    df = DataFrame(results, columns=["Group", "Label", "IP", "Result"]).sort_values(
        ["Result", "Group", "Label", "IP"]
    )[["Result", "Group", "Label", "IP"]]

    # Clean table for display
    df_clean = df.copy()
    df_clean.loc[df_clean["Result"].duplicated(), "Result"] = '"'
    df_clean["Group"] = df.groupby("Result")["Group"].transform(
        lambda x: x.mask(x.duplicated(), '"')
    )
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
        default=f"{cmd.replace(" ", "_")}{f"_{mode.value}_{term.replace(" ", "_")}" if mode.value is not Mode.DISABLE else ""}__{datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")}.csv",
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
