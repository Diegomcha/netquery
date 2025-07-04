import json
import re
from typing import Annotated, Any, AsyncGenerator, Callable, Generator
from uuid import uuid4

from anyio import Event
from cachetools import TTLCache
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette import ServerSentEvent
from sse_starlette.sse import EventSourceResponse

from netquery.core import query_machines
from netquery.utils_new import (
    SUPPORTED_DEVICE_TYPES,
    NamedStream,
    async_gen,
    gen_default_filename,
    parse_machines_multiple,
    parse_regex,
    validate_device_type,
    validate_groups,
)

app = FastAPI()

templates = Jinja2Templates(directory="src/netquery/ui/web/client/templates")
app.mount(
    "/static", StaticFiles(directory="src/netquery/ui/web/client/static"), name="static"
)

cache: TTLCache[str, Callable[[Request], AsyncGenerator[ServerSentEvent, Any]]] = (
    TTLCache(25, 300)
)
stop: dict[str, Event] = {}


def web_query(
    data: dict,
    id: str,
    filename: str,
):
    async def generator(req: Request):
        event = stop[id] = Event()

        async for row in async_gen(query_machines(**data)):
            if await req.is_disconnected() or event.is_set():
                break

            if isinstance(row["result"], Exception):
                row["result"] = str(row["result"])

            yield ServerSentEvent(data=json.dumps(row))

        yield ServerSentEvent(
            data=filename,
            event="finished",
        )

        stop.pop(id, None)

    return generator


@app.get("/")
async def read_root(req: Request):
    return templates.TemplateResponse(
        request=req,
        name="form.html",
        context={"device_types": sorted(SUPPORTED_DEVICE_TYPES)},
    )


@app.get("/results/{id}")
async def results(req: Request, id: str):
    return templates.TemplateResponse(
        request=req,
        name="results.html",
        context={},
    )


@app.post("/execute")
async def execute(
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
    id = str(uuid4())
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

    cache[id] = web_query(parsed, id, gen_default_filename(parsed["cmds"]))

    return RedirectResponse(f"/results/{id}", 302)


@app.get("/stream/{id}")
async def stream(req: Request, id: str):
    try:
        return EventSourceResponse(cache.pop(id)(req))
    except KeyError:
        return HTTPException(404, "Not found")


@app.delete("/stream/{id}")
async def stopStream(id: str):
    event = stop.get(id)
    if event:
        event.set()
    return Response()
