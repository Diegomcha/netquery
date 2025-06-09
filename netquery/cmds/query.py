from enum import Enum
from random import random
from typing import Annotated

from click import UsageError
from netmiko import ConnectHandler
from pandas import DataFrame
from tabulate import tabulate
from typer import Argument, Context, Option, Typer, echo, style

from netquery.utils import AliasGroup

app = Typer(no_args_is_help=True, cls=AliasGroup)


class Mode(str, Enum):
    INCLUDE = "include"
    I = "i"
    EXCLUDE = "exclude"
    E = "e"
    BEGIN = "begin"
    B = "b"
    SECTION = "section"
    GREP = "grep"


@app.callback()
def callback(
    ctx: Context,
    groups: Annotated[
        str | None,
        Option(
            "--groups",
            "-g",
            parser=lambda str: str.split(","),
            metavar="GROUP1,GROUP2,...",
            help="Allows specifying which groups of machines should be queried. By default all groups.",
        ),
    ] = None,
):
    if groups and not all(group in ctx.obj["machines"] for group in groups):
        raise UsageError(
            f"Some specified group is not present in the machines file.\nAvailable groups: {list(ctx.obj["machines"].keys())}"
        )

    ctx.obj["groups"] = groups


@app.command(
    "filtered | ftr",
    help="Executes, filters and aggregates the output of a command run on several machines.",
)
def running(
    ctx: Context,
    cmd: Annotated[
        str, Argument(help="Specifies which command to use for executing the query.")
    ],
    term: Annotated[
        str, Argument(help="Specifies which term or regexp to search for.")
    ],
    mode: Annotated[
        Mode, Option(help="Specifies which mode of searching is employed.")
    ] = Mode.INCLUDE,
):
    command(ctx, f"{cmd} | {mode} {term}")


@app.command(
    "command | cmd",
    help="Executes aggregates the output of a command run on several machines.",
)
def command(
    ctx: Context,
    cmd: Annotated[
        str, Argument(help="Specifies which command to use for executing the query.")
    ],
):
    results = []
    for group in ctx.obj["groups"] or ctx.obj["machines"].keys():
        for machine in ctx.obj["machines"][group]:
            try:
                with ConnectHandler(**machine) as con:
                    result = con.send_command(cmd, use_textfsm=False)
                    result = str(random())
            except Exception as e:
                raise UsageError(
                    f"Error running command in machine '{f"{machine['label']} ({machine['host']})" if 'label' in machine else machine['host']}':\n{e}"
                )

            results.append(
                [
                    group,
                    machine["label"] if "label" in machine else "",
                    machine["host"],
                    machine["device_type"],
                    result,
                ]
            )

    df = DataFrame(
        results, columns=["Group", "Label", "IP", "Type", "Result"]
    ).sort_values(["Result", "Group"])[["Result", "Group", "Label", "IP", "Type"]]

    df_clean = df.copy()
    df_clean.loc[df_clean["Result"].duplicated(), "Result"] = ""
    df_clean["Group"] = df.groupby("Result")["Group"].transform(
        lambda x: x.mask(x.duplicated(), "")
    )

    echo(
        style(
            f"Result of {style("command", italic=True, fg="reset")}",
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
