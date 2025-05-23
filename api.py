import socket
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify

from app import login_required, read_user_from_session, csrf
from tasks import hello, run_ssh_command

bp = Blueprint('api', __name__, url_prefix='/api')

# simple DNS resolver
@bp.route("/resolve", methods=['POST'])
@login_required
@csrf.exempt
def resolve():
    payload = request.get_json()
    try:
        hostname = payload.get("hostname")
        ip = socket.gethostbyname(hostname)
        return jsonify({"ip": ip})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# submit Celery task
@bp.route('/task', methods=['POST'])
@login_required
@csrf.exempt
def create_task():
    user = read_user_from_session(session)
    payload = request.get_json()
    task_type = payload.get("type", None)
    task_data = payload.get("data", None)

    if task_type is None or task_data is None:
        return jsonify({"error": "Missing task type or data"}), 400

    match task_type:
        case "hello":
            result = hello.delay(task_data)
        case "sh_int_desc":
            result = run_ssh_command.delay(
                host = task_data.get("ip_address"),
                username = user.username,
                password = user.password,
                command = "show interface description"
            )

    return jsonify({"task_id": result.id}), 202

# get Celery task status
@bp.route("/task/<string:task_id>", methods=["GET"])
@login_required
@csrf.exempt
def get_task(task_id):
    result = AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": result.status,
        "success": result.successful(),
        "ready": result.ready(),
        "result": result.result if result.ready() and result.successful() else None,
    }

    return jsonify(response)