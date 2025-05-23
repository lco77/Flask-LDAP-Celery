# import os
# from dotenv import load_dotenv
from netmiko import ConnectHandler
from celery import Celery, shared_task 

# load_dotenv()

# Config
# REDIS_URL = os.environ.get("REDIS_URL")
# RESULT_EXPIRES = 300

# Init app
# worker = Celery('celery', broker=REDIS_URL, result_backend=REDIS_URL, task_ignore_result=False)
# worker.conf.result_expires = RESULT_EXPIRES

# hello world task
@shared_task
def hello(world):
    return {
        "hello": world,
        "success": True
    }

# run_ssh_command
@shared_task
def run_ssh_command(host:str, username:str, password:str, command:str, device_type:str="cisco_ios", use_textfsm:bool=True, port:int=22, timeout:int=10):
    try:
        device = {
            "device_type": device_type,
            "ip": host,
            "username": username,
            "password": password,
            "port": port,
        }

        connection = ConnectHandler(**device)
        output = connection.send_command(command, use_textfsm=use_textfsm)
        connection.disconnect()

        return {
            "host": host,
            "command": command,
            "parsed": output if isinstance(output, list) else None,
            "raw_output": output if isinstance(output, str) else None,
            "success": True
        }

    except Exception as e:
        return {
            "host": host,
            "command": command,
            "error": str(e),
            "success": False
        }