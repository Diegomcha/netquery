import json
from io import BytesIO
from re import Pattern

from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    SSHDetect,
)

from netquery.exceptions import (
    NetqueryNoMatchesException,
    NetqueryTimeoutException,
    NetqueryUnauthorizedException,
    NetqueryUnknownDeviceTypeException,
)
from netquery.utils import MultipleMachines, get_hostname


def query_machines(
    machines: MultipleMachines,
    username: str,
    password: str,
    device_type: str,
    groups: list[str],
    cmds: list[str],
    prompt_patterns: list[str],
    textfsm_template: str,
    output_regex: Pattern,
):
    # Flatten iterations
    work = [
        (filename, group, label, machine)
        for filename in machines
        for group in groups
        if group in machines[filename]
        for label, machine in machines[filename][group].items()
    ]

    for i, (filename, group, label, machine) in enumerate(work, 1):

        # TODO: Remove!
        # for filename in machines.keys():
        #     for group in groups:
        #         # Skip any group not present in current file
        #         if group not in machines[filename]:
        #             continue

        #         for label, machine in machines[filename][group].items():

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

            try:
                if device["device_type"] == "autodetect":
                    device["device_type"] = SSHDetect(**device).autodetect()

                # If detection failed
                if not device["device_type"]:
                    result = NetqueryUnknownDeviceTypeException()

                else:
                    with ConnectHandler(**device) as con:
                        # If no commands, test it is accessible
                        if len(cmds[0]) == 0:
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
                                    # If no matches throw error
                                    result = NetqueryNoMatchesException(result)

            except NetmikoAuthenticationException:
                result = NetqueryUnauthorizedException()
            except NetmikoTimeoutException:
                result = NetqueryTimeoutException()
            except Exception as e:
                result = e

            yield {
                "filename": filename,
                "group": group,
                "label": label,
                "hostname": get_hostname(device["host"]),
                "ip": device["host"],
                "device_type": device["device_type"],
                "result": result,
                "log": log.getvalue().decode(),
                "progress": i / len(work),
            }
