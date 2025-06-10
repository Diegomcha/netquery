from enum import Enum
from random import random
from time import sleep
from typing import Annotated

from click import UsageError
from netmiko import ConnectHandler
from pandas import DataFrame
from rich.progress import Progress, track
from tabulate import tabulate
from typer import Argument, Context, FileText, Option, Typer, echo, prompt, style

from netquery.utils import DEFAULT_DEVICE_TYPE, Machines, parse_machines

query_app = Typer()


class Mode(str, Enum):
    I = "i"
    INCLUDE = "include"
    E = "e"
    EXCLUDE = "exclude"
    B = "b"
    BEGIN = "begin"
    SECTION = "section"
    GREP = "grep"


def validate_groups(ctx: Context, groups: list[str]):
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


@query_app.command()
def query(
    machines: Annotated[
        Machines,
        Option(
            prompt="Machines file (.txt or .json)",
            parser=parse_machines,
            metavar="FILENAME",
        ),
    ],
    username: Annotated[str, Option(prompt="Username", hide_input=True)],
    password: Annotated[str, Option(prompt="Password", hide_input=True)],
    cmd: Annotated[str, Option(prompt="Command")],
    mode: Annotated[Mode, Option(prompt="Searching mode")],
    term: Annotated[str, Option(prompt="Searching term")],
    groups: Annotated[
        str | None,
        Option(
            parser=lambda str: str.split(","),
            callback=validate_groups,
            metavar="GROUP1,GROUP2,...",
            help="Allows specifying which groups of machines should be queried.",
            show_default="All groups",
        ),
    ] = None,
    multiple: Annotated[bool, Option()] = True,
):
    echo(machines)
    results = []
    with Progress() as prog:
        for group in prog.track(groups or machines.keys(), description="Querying"):
            for label, machine in prog.track(
                machines[group].items(), description=group
            ):
                try:
                    result = ""
                #     with ConnectHandler(
                #         **{
                #             "username": username,
                #             "password": password,
                #             "device_type": DEFAULT_DEVICE_TYPE,
                #         },
                #         **machine,
                #     ) as con:
                #         result = con.send_command(f"{cmd} | {mode.value} {term}")
                except Exception as e:
                    raise UsageError(
                        f"Error running command in machine '{label}':\n{e}"
                    )

                results.append(
                    [
                        group,
                        label,
                        machine["host"],
                        result,
                    ]
                )

    df = DataFrame(results, columns=["Group", "Label", "IP", "Result"]).sort_values(
        ["Result", "Group", "Label", "IP"]
    )[["Result", "Group", "Label", "IP"]]

    echo(
        style(
            f"Result of {style(cmd, italic=True, fg="reset")}",
            bold=True,
            fg="cyan",
        )
    )
    echo(
        tabulate(
            df.values.tolist(),
            df.columns.to_list(),
            "rounded_grid",
            showindex=True,
        )
    )

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
