import json
import re
import tempfile
from typing import IO, Annotated, Iterable, Optional, cast

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates

from netquery.core import query_machines
from netquery.utils_new import (
    SUPPORTED_DEVICE_TYPES,
    NamedStream,
    parse_machines_multiple,
    parse_regex,
    validate_device_type,
    validate_groups,
)

app = FastAPI()

templates = Jinja2Templates(directory="src/netquery/templates")


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={"device_types": sorted(SUPPORTED_DEVICE_TYPES)},
    )


# TODO: tabulator
@app.post("/execute")
def execute(
    machines_files: Annotated[list[UploadFile], File()],
    groups: Annotated[str, Form()],
    device_type: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    commands: Annotated[str, Form()],
    expected_prompts: Annotated[str, Form()],
    output_regex: Annotated[str, Form()],
    # textfsm_template: Annotated[UploadFile | None, File()],
):
    parsed = {
        "username": username,
        "password": password,
        "cmds": commands.split(","),
        "prompt_patterns": expected_prompts.split(","),
        "textfsm_template": "",  # TODO:
    }

    try:
        parsed["machines"] = parse_machines_multiple(
            [NamedStream(file.file, file.filename) for file in machines_files]
        )
    except Exception as e:
        raise HTTPException(400, f"Invalid machines file.\n{e}")

    try:
        parsed["groups"] = validate_groups(parsed["machines"], groups.split(","))
    except KeyError as e:
        raise HTTPException(400, repr(e))

    try:
        parsed["device_type"] = validate_device_type(device_type)
    except ValueError as e:
        raise HTTPException(400, repr(e))

    try:
        parsed["output_regex"] = parse_regex(output_regex)
    except re.error as e:
        raise HTTPException(400, f"Invalid output regex {repr(e)}")

    # print(parsed["machines"])

    # return parsed

    arr = []
    for row in query_machines(**parsed):
        print(row)
        arr.append(row)

    return arr
