from typing import Annotated

from typer import Context, FileText, Option, Typer, echo, open_file, prompt

from netquery.cmds.query import query_app
from netquery.cmds.show import show_app
from netquery.utils import parse_machines

app = Typer(no_args_is_help=True)


# # Options
# @app.callback()
# def main_callback(
#     ctx: Context,
# ):
#     ctx.obj = {}


# Register subcommands

# app.add_typer(
#     show_app,
#     name="show",
#     help="Shows information about the configured machines and groups.",
# )
app.add_typer(query_app)
