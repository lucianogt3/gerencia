from functools import wraps
from flask import abort, redirect, url_for, flash, request
from flask_login import current_user
from datetime import datetime

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

def require_indicator_filling(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if getattr(current_user, "role", None) in ["manager", "admin"]:
            return f(*args, **kwargs)

        if getattr(current_user, "status", None) == "active" and current_user.role == "nurse":
            from app.models.indicator import DailyIndicator
            hoje = datetime.utcnow().date()
            ja_preencheu = DailyIndicator.query.filter_by(user_id=current_user.id, date=hoje).first()

            if not ja_preencheu and request.endpoint != 'indicators.index':
                flash("Ação Obrigatória: Lançar indicadores do plantão para liberar o sistema.", "warning")
                return redirect(url_for('indicators.index'))
        return f(*args, **kwargs)
    return wrapper
