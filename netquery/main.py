from typing import Annotated

from typer import Context, Option, Typer

from netquery.cmds.query import app as query_app
from netquery.cmds.show import app as show_app
from netquery.utils import AliasGroup, read_json

app = Typer(no_args_is_help=True, cls=AliasGroup)


# Options
@app.callback()
def main_callback(
    ctx: Context,
    machines: Annotated[
        str,
        Option(
            "--machines-file",
            "-m",
            help="Specifies the filename of a JSON file where to get the machines data from.",
        ),
    ] = "machines.json",
    # TODO:
    # verbose: Annotated[
    #     bool, Option("--verbose", "-v", help="Enables verbose output.")
    # ] = False,
    # config: str = Option("None", "--config", help="Uses a custom program's config"),
):
    ctx.obj = {"machines": read_json(machines)}


# Register subcommands

app.add_typer(
    show_app,
    name="show | sw",
    help="Shows information about the configured machines and groups.",
)
app.add_typer(
    query_app, name="query | qry", help="Performs queries to the configured machines."
)
