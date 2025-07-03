import json
import re
from typing import Annotated
from uuid import uuid4

from cachetools import TTLCache
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathvalidate import sanitize_filename

from netquery.core import query_machines
from netquery.utils_new import (
    SUPPORTED_DEVICE_TYPES,
    MultipleMachines,
    NamedStream,
    gen_default_filename,
    parse_machines_multiple,
    parse_regex,
    validate_device_type,
    validate_groups,
)

app = FastAPI()
cache = TTLCache(25, 300)

app.mount(
    "/static", StaticFiles(directory="src/netquery/ui/web/client/static"), name="static"
)
templates = Jinja2Templates(directory="src/netquery/ui/web/client/templates")


def web_query(
    machines: MultipleMachines,
    username: str,
    password: str,
    device_type: str,
    groups: list[str],
    cmds: list[str],
    prompt_patterns: list[str],
    textfsm_template: str,
    output_regex: re.Pattern,
):
    for i, row in enumerate(
        query_machines(
            machines,
            username,
            password,
            device_type,
            groups,
            cmds,
            prompt_patterns,
            textfsm_template,
            output_regex,
        )
    ):
        yield f"id:{i}\ndata:{json.dumps(row)}\n\n"

    yield f"event:finished\ndata:{gen_default_filename(cmds)}\n\n"


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={"device_types": sorted(SUPPORTED_DEVICE_TYPES)},
    )


@app.get("/stream/{id}")
async def stream(id: str):
    try:
        return StreamingResponse(cache.pop(id), media_type="text/event-stream")
    except KeyError:
        return HTTPException(404, "Not found")


@app.get("/results/{id}")
def results(request: Request, id: str):
    # if id not in cache.keys():
    #     return RedirectResponse("/")

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={},
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

    id = str(uuid4())
    cache[id] = web_query(**parsed)
    # cache[id] = event_gen()

    return RedirectResponse(f"/results/{id}", 302)
