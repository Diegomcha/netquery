# TODO: los dispositivos que no sean accessibles?
# TODO:

# Creating the typer instance
from typing import Annotated

from pandas import DataFrame, read_csv, read_html, read_json
from typer import FileText, Typer, run

from netquery.utils import console

# def main(
#     file,
#     # template
# ):
res = read_csv("~/app/output_cisco_wlc.csv")

a = res.to_dict("")

# console.print(res)
# TODO: read_json, read_html
# TODO: read_json, read_html


# if __name__ == "__main__":
#     run(main)
