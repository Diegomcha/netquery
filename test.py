from getpass import getpass, getuser

from netmiko import ConnectHandler

machine = {
    "device_type": "cisco_ios",
    "host": "10.207.5.224",
    "username": getpass("Username: "),
    "password": getpass(),
}

with ConnectHandler(**machine) as con:
    result = con.send_command("show run | i hostname")
    print(result)
