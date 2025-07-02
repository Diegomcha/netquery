from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from netquery.utils import SUPPORTED_DEVICE_TYPES

app = FastAPI()

templates = Jinja2Templates(directory="src/netquery/templates")


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={"device_types": sorted(SUPPORTED_DEVICE_TYPES)},
    )


@app.post("/execute")
def execute(
    machines_files: Annotated[UploadFile, File()],
    groups: Annotated[str, Form()],
    device_type: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    commands: Annotated[str, Form()],
    expected_prompts: Annotated[str, Form()],
    output_regex: Annotated[str, Form()],
    textfsm_template: Annotated[UploadFile | None, File()],
): ...
