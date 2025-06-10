from enum import Enum
from typing import Annotated

from click import UsageError
from tabulate import tabulate
from typer import Argument, Context, Option, Typer, echo, style

show_app = Typer(no_args_is_help=True)


class Format(str, Enum):
    PRETTY = "pretty"
    # TODO: Implement more styles
    # PLAIN = "plain"
    # HTML = "html"


@show_app.callback()
def callback(
    ctx: Context,
    format: Annotated[
        Format, Option("--format", "-f", help="Allows changing the output format.")
    ] = Format.PRETTY,
    # TODO: Finish implementing
    # filename: Annotated[str | None, Option("--filename", "-F")] = None,
):
    ctx.obj["format"] = format
    # ctx.obj["filename"] = filename


@show_app.command("groups", help="Shows the configured machine groups.")
def view_groups(
    ctx: Context,
):
    table = [(group, len(machines)) for group, machines in ctx.obj["machines"].items()]

    echo(style("Groups of machines:", bold=True, fg="cyan"))

    echo(
        tabulate(table, ["Group", "Nº machines"], "rounded_grid", showindex=True),
    )


@show_app.command("machines", help="Shows the machines from a group.")
def view_group_machines(
    ctx: Context,
    group: Annotated[
        str, Argument(help="Group label of the group whose machines to list.")
    ],
):
    if group not in ctx.obj["machines"]:
        raise UsageError(f"Group '{group}' is not in the machines list.")

    table = [
        (
            machine["label"] if "label" in machine else "",
            machine["host"],
            machine["device_type"],
        )
        for machine in ctx.obj["machines"][group]
    ]

    echo(
        style(
            f"Machines of {style(group, italic=True, fg="reset")}",
            bold=True,
            fg="cyan",
        )
    )
    echo(
        tabulate(table, ["Label", "IP", "Type"], "rounded_grid", showindex=True),
    )
