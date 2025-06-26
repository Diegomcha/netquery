import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated, Any

from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    SSHDetect,
)
from pandas import DataFrame
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from tabulate import tabulate
from typer import Option, Typer, open_file, prompt

from netquery.utils import (
    MultipleMachines,
    console,
    get_hostname,
    parse_multiple_machines,
    parse_output,
    parse_regex,
    parse_textfsm_template,
    safe_splitter,
    validate_device_type,
    validate_groups,
    version_callback,
)

# Creating the typer instance
app = Typer(pretty_exceptions_show_locals=False)


# Defining the command with a python decorator
@app.command()
def query(
    machines: Annotated[
        MultipleMachines,
        Option(
            parser=parse_multiple_machines,
            metavar="FILENAME1,FILENAME2,...",
            help="Comma-separated paths to the files containing machine definitions (.json or .txt).",
            prompt="Machines files (Comma-separated, .txt or .json)",
        ),
    ],
    username: Annotated[
        str,
        Option(
            help="Username for SSH authentication.",
            prompt="Username",
            hide_input=True,
        ),
    ],
    password: Annotated[
        str,
        Option(
            help="Password for SSH authentication.",
            prompt="Password",
            hide_input=True,
        ),
    ],
    device_type: Annotated[
        str,
        Option(
            metavar="DEVICE_TYPE",
            callback=validate_device_type,
            help="Default device type for machines without an explicit 'device_type'. The list of supported types can be found here: https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md. Avoid 'autodetect' for large sets due to performance.",
            prompt="Default device type",
        ),
    ] = "autodetect",
    groups: Annotated[
        Any,
        Option(
            parser=safe_splitter(","),
            callback=validate_groups,
            metavar="GROUP1,GROUP2,...",
            help="Comma-separated list of machine groups to include. If omitted, all groups are used.",
            prompt="Groups (comma-separated)",
        ),
    ] = "all",
    cmds: Annotated[
        Any,
        Option(
            parser=safe_splitter(","),
            metavar="CMD1,CMD2,...",
            help="Comma-separated list of commands to run on each device. Leave empty to only check SSH accessibility.",
            show_default="none",
            prompt="Commands (comma-separated)",
        ),
    ] = "",
    prompt_patterns: Annotated[
        Any,
        Option(
            parser=safe_splitter(","),
            metavar="PATTERN1,PATTERN2,...",
            help="Comma-separated list of expected prompt patterns, one per command. These patterns help match the device's prompt during execution. If left blank, the default prompt for the detected device type will be used.",
            show_default="device's default",
            prompt="Prompt patterns (comma-separated)",
        ),
    ] = "",
    textfsm_template: Annotated[
        Any,
        Option(
            parser=parse_textfsm_template,
            metavar="FILENAME",
            help="Path to a TextFSM template for parsing command output. Only used if 'cmds' is set.",
            show_default="disabled",
            prompt="TextFSM template",
        ),
    ] = "",
    output_regex: Annotated[
        Any,
        Option(
            parser=parse_regex,
            metavar="REGEX",
            help="Regex pattern to filter command output locally. Applied after TextFSM parsing, if used.",
            show_default="disabled",
            prompt="Output regex filter",
        ),
    ] = "",
    output: Annotated[
        Any,
        Option(
            parser=parse_output,
            metavar="[FILENAME.html|FILENAME.json|FILENAME.csv|FILENAME.txt|False]",
            show_default="dynamic",
            help="Output filename for saving results. Use 'False' to disable saving. Format inferred from extension.",
        ),
    ] = None,
    version: Annotated[
        bool | None,
        Option(
            "--version",
            callback=version_callback,
            help="Displays the version of the utility and quits.",
        ),
    ] = None,
):
    """
    Connect to a set of network devices over SSH and run commands.
    """
    # Query machines
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as prog:
        for filename in prog.track(machines.keys(), description="Querying..."):
            for group in prog.track(groups, description=f"· {filename}"):
                # Skip any group not present in current file
                if group not in machines[filename]:
                    continue

                for label, machine in prog.track(
                    machines[filename][group].items(), description=f"  · {group}"
                ):
                    # Open an in-memory log for the session_log
                    with BytesIO() as log:
                        device = {
                            **{
                                "username": username,
                                "password": password,
                                "device_type": device_type,
                                "session_log": log,
                            },
                            **machine,
                        }
                        hostname = get_hostname(device["host"])

                        try:
                            if device["device_type"] == "autodetect":
                                device["device_type"] = SSHDetect(**device).autodetect()

                            # If detection failed
                            if not device["device_type"]:
                                result = "❓ Unknown"
                                prog.console.log(
                                    f"❓ Unknown device type '{label} ({hostname})'!",
                                    style="bold red",
                                )

                            else:
                                with ConnectHandler(**device) as con:
                                    # If no commands, test it is accessible
                                    if len(cmds) == 1 and len(cmds[0]) == 0:
                                        result = "✅ Accessible"
                                    else:
                                        # For single commands
                                        if len(cmds) == 1:
                                            result = con.send_command(
                                                # Command & expected prompt
                                                cmds[0],
                                                expect_string=(
                                                    prompt_patterns[0]
                                                    if len(prompt_patterns[0]) > 0
                                                    else None
                                                ),
                                                # TextFSM options
                                                use_textfsm=textfsm_template != None,
                                                textfsm_template=textfsm_template,
                                                raise_parsing_error=True,
                                            )
                                        # For multiple/interactive commands
                                        else:
                                            result = con.send_multiline(
                                                # Commands & expected prompts
                                                (
                                                    [
                                                        [cmd, pattern]
                                                        for cmd, pattern in zip(
                                                            cmds, prompt_patterns
                                                        )
                                                    ]
                                                    if len(prompt_patterns) == len(cmds)
                                                    else cmds
                                                ),
                                                # TextFSM options
                                                use_textfsm=textfsm_template != None,
                                                textfsm_template=textfsm_template,
                                                raise_parsing_error=True,
                                            )

                                        # Parse JSON result if parsing template was provided
                                        if isinstance(result, (list, dict)):
                                            result = json.dumps(result)

                                        # Filter output
                                        if output_regex:
                                            match = output_regex.search(result)
                                            if match:
                                                result = match.group()
                                            else:
                                                # Do not apply filter if nothing matches
                                                prog.console.log(
                                                    f"🔍 '{output_regex}' found no matches for '{label} ({hostname})'!",
                                                    style="bold yellow",
                                                )

                                    prog.console.log(
                                        f"✅ Task complete for device '{label} ({hostname})'",
                                        style="bold green",
                                    )

                        except NetmikoAuthenticationException:
                            result = "⛔ Unauthorized"
                            prog.console.log(
                                f"⛔ Authentication failure at '{label} ({hostname})'!",
                                style="bold red",
                            )
                        except NetmikoTimeoutException:
                            result = "⌛ Timeout"
                            prog.console.log(
                                f"⌛ Failed to connect to '{label} ({hostname})'!",
                                style="bold red",
                            )
                        except Exception:
                            result = "🔥 Exception"
                            prog.console.log(
                                f"🔥 Unknown error from '{label} ({hostname})'!",
                                style="bold red",
                            )
                            prog.console.print_exception()

                        results.append(
                            [
                                filename,
                                group,
                                label,
                                hostname,
                                device["host"],
                                device["device_type"],
                                result,
                                log.getvalue().decode(),
                            ]
                        )

    # Sort table of results & move columns around
    df = DataFrame(
        results,
        columns=[
            "File",
            "Group",
            "Label",
            "Hostname",
            "IP",
            "Device Type",
            "Result",
            "Log",
        ],
    ).sort_values(
        ["Result", "File", "Group", "Label", "Hostname", "IP", "Device Type"]
    )[
        ["Result", "File", "Group", "Label", "Hostname", "IP", "Device Type", "Log"]
    ]

    # Clean table for display (Cumbersome...)
    df_clean = df.copy()
    df_clean.loc[df_clean["Result"].duplicated(), "Result"] = "''"
    df_clean["File"] = df.groupby("Result")["File"].transform(
        lambda x: x.mask(x.duplicated(), "''")
    )
    df_clean["Group"] = df.groupby(["Result", "File"])["Group"].transform(
        lambda x: x.mask(x.duplicated(), "''")
    )

    df_clean = df_clean.drop("Log", axis="columns")
    if len(machines.keys()) == 1:
        df_clean = df_clean.drop("File", axis="columns")
    if len(groups) == 1:
        df_clean = df_clean.drop("Group", axis="columns")

    # Display the table
    console.print(
        f"Result of '{"+".join(cmds) if len(cmds[0]) > 0 else "accessing the devices"}'",
        style="bold cyan",
    )
    console.print(
        tabulate(
            df_clean.values.tolist(),
            df_clean.columns.to_list(),
            "rounded_grid",
            showindex=True,
        )
    )

    # Handle writting output
    if output != False:
        if output == None:
            output = prompt(
                "Output (.html .csv .json .txt False)",
                default=f"{"+".join(cmds).replace(" ", "_") if len(cmds[0]) > 0 else "accessible"}__{datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")}.csv",
                value_proc=parse_output,
            )

        with open_file(output, "w") as output_file:
            match output.suffix:
                case ".html":
                    df.to_html(output_file)
                case ".csv":
                    df.to_csv(output_file)
                case ".json":
                    df.to_json(output_file, orient="records", lines=True)
                case ".txt":
                    df.to_string(output_file)
                case _:
                    console.print(
                        "Unknown extension, outputted in TXT format.", style="yellow"
                    )
                    df.to_string(output_file)

        console.print(
            f"Output written to '{output}'",
            style="cyan",
        )
