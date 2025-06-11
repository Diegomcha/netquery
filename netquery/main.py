from typer import Typer

from netquery.cmds.query import app as query

app = Typer(no_args_is_help=True)


# Register commands

app.add_typer(query)
