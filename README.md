# Flask-LDAP-Celery

Flask boilerplate aiming at simplicity:

- LDAP authentication with group to role mapping (typically for use with Active Directory)
- Celery integration to offload long running tasks
- Clear UI versus API separation
- Client-side sessions
- Minimalist Bootstrap frontend using JQuery only
- Support for Dark/Light theme

This is a good choice for simple stateless containerized applications.

All configuration is handled via environment variables.
No need for persistent storage or DB backend.

## Project layout

Layout is very simple:

- app.py initializes the Flask application with login/logout workflow + light/dark theme selection
- worker.py initializes the Celery application 
- api.py is meant for your custom API endpoints
- ui.py is meant for your custom UI endpoints
- tasks.py is meant for your custom Celery tasks

## Configuration

Just add environment variables

```shell
# your application name
FLASK_APP="app"

# set to 'development' or 'production'
FLASK_ENV="development"

# define LDAP credentials
# Note: the application defaults to LDAPS without TLS certificate verification
LDAP_HOST="dc.company.com"
LDAP_USERNAME="CN=ldap_user,DC=company,DC=com"
LDAP_PASSWORD="Secret"
LDAP_BASE_DN="DC=company,DC=com"

# use a JSON formatted string to map roles with AD groups
# you can map multiple groups per role
# Note: a user can match multiple roles
LDAP_ROLES='{"admin": ["CN=admin_users"], "read-only": ["CN=read_users"]}'

# REDIS setup (required by Celery)
REDIS_URL="redis://localhost"
```


## Basic Usage

During app development, simply start your app from the app directory

```shell
# start Flask
flask run --reload

# or using watchog to catch any file change
pip install watchdog
watchmedo auto-restart --patterns="*.py;*.html;*.css;*.js" --recursive -- flask run

# star Celery worker
celery -A worker worker --loglevel=INFO
```

## Access control

There are 2 decorators which you can use to restrict access to your routes:

- @login_required()

A valid authenticated user is required

- @roles_required(allowed_roles)

A valid authenticated user with at least one of allowed_roles is required


