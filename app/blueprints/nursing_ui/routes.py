from __future__ import annotations

from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

bp = Blueprint("nursing_ui", __name__, url_prefix="/nursing")


@bp.get("/monthly")
@login_required
def monthly_page():
    if getattr(current_user, "role", "") not in ("manager", "admin"):
        return render_template("errors/403.html"), 403

    return render_template(
        "nursing/monthly.html",
        title="Escala Mensal"
    )


@bp.get("/daily")
@login_required
def daily_page():
    today = date.today().isoformat()
    sector_id = request.args.get("sector_id", "")
    shift = request.args.get("shift", "D")

    return render_template(
        "nursing/daily.html",
        title="Escala Diária",
        today=today,
        sector_id=sector_id,
        shift=shift,
    )



