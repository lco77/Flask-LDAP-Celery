from flask import current_app, g, Blueprint, request, url_for, session, jsonify, json, make_response, render_template, redirect
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from dataclasses import dataclass, field, asdict
from app import login_required, read_user_from_session
import socket

bp = Blueprint('ui', __name__, url_prefix='/ui')

# DeviceForm
class DeviceForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired()])
    submit = SubmitField('Search')

@dataclass
class Device:
    hostname: str
    ip_address: str
    task_id: str = None

@bp.route('/device', methods=['GET','POST'])
@login_required
def device():
    device = None
    error = None
    form = DeviceForm()
    
    if form.validate_on_submit():
        hostname = form.hostname.data
        try:
            ip_address = socket.gethostbyname(hostname)
            device = Device(
                hostname = hostname,
                ip_address = ip_address
            )    
        except socket.gaierror:
            error = f"Could not resolve {hostname}"

    return render_template("ui/device.html", form=form, error=error, device=device, theme=session["theme"])