from functools import wraps
from flask import abort
from flask_login import current_user

def require_active(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if getattr(current_user, "status", None) != "active":
            abort(403)
        return f(*args, **kwargs)
    return wrapper

def require_roles(*roles: str):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if getattr(current_user, "status", None) != "active":
                abort(403)
            if getattr(current_user, "role", None) not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
