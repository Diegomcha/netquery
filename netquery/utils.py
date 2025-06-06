import re
from json import load

from click import FileError
from typer import open_file
from typer.core import TyperGroup


def read_json(filename: str):
    try:
        with open_file(filename) as file:
            return load(file)
    except FileNotFoundError as e:
        raise FileError(filename, e.strerror)


# This class allows aliases for commands by using |
class AliasGroup(TyperGroup):

    _CMD_SPLIT_P = re.compile(r" ?[,|] ?")

    def get_command(self, ctx, cmd_name):
        cmd_name = self._group_cmd_name(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _group_cmd_name(self, default_name):
        for cmd in self.commands.values():
            name = cmd.name
            if name and default_name in self._CMD_SPLIT_P.split(name):
                return name
        return default_name
