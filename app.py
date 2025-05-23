import time
import os
import json
import ssl

from flask import Flask, render_template, redirect, url_for, abort, session, request
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from redis import Redis
from ldap3 import Server, Connection, ALL, SUBTREE, Tls
from functools import wraps
from dataclasses import dataclass, field, asdict
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Config
REDIS_URL = os.environ.get("REDIS_URL")
LDAP_HOST = f"ldaps://{os.environ.get("LDAP_HOST")}"
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN")
LDAP_USERNAME = os.environ.get("LDAP_USERNAME")
LDAP_PASSWORD = os.environ.get("LDAP_PASSWORD")
ROLES = json.loads(os.environ.get("LDAP_ROLES"))
SESSION_TIMEOUT_SECONDS = 3600

# Init Flask app
app = Flask(__name__)

# Server side sessions
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis.from_url(REDIS_URL)
Session(app)

if os.environ['FLASK_ENV'] == 'development':
    app.secret_key = 'REPLACE_WITH_SECURE_SECRET'
    app.debug = True
else:
    app.secret_key = os.urandom(24).hex()

# Attach Celery app
celery_app = Celery('celery', broker=REDIS_URL, result_backend=REDIS_URL, task_ignore_result=False)
celery_app.set_default()
app.extensions["celery"] = celery_app

# Refresh session timeout
@app.before_request
def refresh_session():
    if os.environ['FLASK_ENV'] == 'development':
        print(f"refresh_session(): session={session}")
    # set default theme
    if "theme" not in session:
        session["theme"] = "dark"
    # Check session expired
    if 'username' in session:
        now = int(time.time())
        if session.get('expires_at', 0) < now:
            session.clear()
        else:
            # Refresh timeout
            session['expires_at'] = now + SESSION_TIMEOUT_SECONDS

# CSRF token timeout
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return redirect(url_for("login"))

# Enable CSRF protection
csrf = CSRFProtect(app)

# User class
@dataclass
class User:
    username: str
    password: str = None
    dn: str = None
    fullname: str = None
    email: str = None
    authenticated: bool = False
    roles: list = field(default_factory = list)

# Utility function to read user data from session
def read_user_from_session(session)->User:
    return User(
        username = session.get("username"),
        password = session.get("password"),
        fullname = session.get("fullname"),
        email = session.get("email"),
        roles = session.get("roles")
    )

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Login required decorator
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# Roles required decorator
def roles_required(allowed_roles:list[str]):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_roles = session.get("roles", [])
            if not any(role in allowed_roles for role in user_roles):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# LDAP login function
def ldap_login(username: str, password: str) -> User:
    tls_config = Tls(validate=ssl.CERT_NONE)
    server = Server(
        LDAP_HOST,
        get_info = ALL,
        port = 636,
        use_ssl = True,
        tls = tls_config
    )

    # Use service account to search for user's DN
    try:
        conn = Connection(
            server,
            user = LDAP_USERNAME,
            password = LDAP_PASSWORD,
            auto_bind = True
        )
    except Exception as e:
        print(f"[ERROR] Failed to bind with service account: {e}")
        return User(username=username)

    # Search for the user's DN using sAMAccountName
    search_filter = f"(sAMAccountName={username})"
    conn.search(
        search_base = LDAP_BASE_DN,
        search_filter = search_filter,
        search_scope = SUBTREE,
        attributes = ["distinguishedName", "memberOf", "displayName", "mail"]
    )

    if not conn.entries:
        return User(username=username)

    user_dn = conn.entries[0].entry_dn
    member_of = conn.entries[0].memberOf.values if 'memberOf' in conn.entries[0] else []
    fullname = conn.entries[0].displayName.value
    email = conn.entries[0].mail.value

    # Now try binding with the user's actual credentials
    try:
        Connection(server, user=user_dn, password=password, auto_bind=True)
    except Exception:
        return User(username=username)

    # User role mapping
    user_roles = set()
    for role_name,role_groups in ROLES.items():
        for role_group in role_groups:
            for user_group in member_of:
                if user_group.startswith(role_group):
                    user_roles.add(role_name)


    return User(
        authenticated = True,
        username = username,
        password = password,
        dn = user_dn,
        fullname = fullname,
        email = email,
        roles = list(user_roles)
    )

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error = None

    # Avoid LDAP bind if already authenticated
    if "username" in session:
        return redirect(url_for('home'))
    
    # Authenticate
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = ldap_login(username, password)
        if user.authenticated:
            app.session_interface.regenerate(session)
            session["username"] = user.username
            session["password"] = user.password
            session["roles"] = user.roles
            session["fullname"] = user.fullname
            session["email"] = user.email
            session['expires_at'] = int(time.time()) + SESSION_TIMEOUT_SECONDS
            return redirect(url_for('home'))
        else:
            error = "Access denied"

    return render_template("login.html", form=form, error=error, theme=session["theme"])

# Logout route
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    del session["username"]
    del session["password"]
    del session["roles"]
    del session["fullname"]
    del session["email"]
    del session['expires_at']
    #session.clear()
    return redirect(url_for('login'))

# Home route
@app.route('/', methods=['GET'])
@login_required
def home():
    user = read_user_from_session(session)
    return render_template("home.html", user=user, theme=session["theme"])

# About route
@app.route('/about', methods=['GET'])
@login_required
def about():
    user = read_user_from_session(session)
    return render_template("about.html", user=user, theme=session["theme"])

# Dark/Light theme route
@app.route("/theme", methods=["POST"])
@csrf.exempt
def toggle_theme():
    new_theme = request.form.get("theme")
    if new_theme in ["light", "dark"]:
        session["theme"] = new_theme
    return redirect(request.referrer or url_for("home"))

# Load API blueprint
import api
app.register_blueprint(api.bp)

# Load UI blueprint
import ui
app.register_blueprint(ui.bp)

if __name__ == '__main__':
    app.run(debug=True)
