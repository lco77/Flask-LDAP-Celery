import os
from dotenv import load_dotenv
from celery import Celery
import tasks
load_dotenv()

# Config
REDIS_URL = os.environ.get("REDIS_URL")
RESULT_EXPIRES = 300

# Init app
worker = Celery('celery', broker=REDIS_URL, result_backend=REDIS_URL, task_ignore_result=False)
worker.conf.result_expires = RESULT_EXPIRES