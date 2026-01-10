from flask import Blueprint, render_template
from flask_login import login_required
from ...utils.security import require_active, require_roles

sick_notes_bp = Blueprint("sick_notes", __name__, url_prefix="/sick-notes")

@sick_notes_bp.route("/public")
def public_form():
    # Placeholder: aqui entra /public/atestado com matrícula puxando dados
    return render_template("sick_notes/public.html")

@sick_notes_bp.route("/")
@login_required
@require_active
@require_roles("manager","admin")
def manage():
    return render_template("sick_notes/manage.html")
