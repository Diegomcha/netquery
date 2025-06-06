from typing import Annotated

from typer import Argument, Context, Option, Typer

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
    verbose: Annotated[
        bool, Option("--verbose", "-v", help="Enables verbose output.")
    ] = False,
    # TODO: Config
    # config: str = Option("None", "--config", help="Uses a custom program's config"),
):
    ctx.obj = {"verbose": verbose, "machines": read_json(machines)}


# Register subcommands

app.add_typer(show_app, name="show | sw")
app.add_typer(query_app, name="query | qry")
