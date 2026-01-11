from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from ...utils.security import require_active
from ...models.announcement import Announcement
from ...models.user import User

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@login_required
def root():
    # Se usuário ainda não foi liberado, mostra página de pendência
    if current_user.status != "active":
        return render_template("auth/pending.html")
    return dashboard()

@main_bp.route("/dashboard")
@login_required
@require_active
def dashboard():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()

    today = date.today()
    month = today.month
    aniversariantes = User.query.filter(User.nascimento.isnot(None)).all()
    aniversariantes_mes = [u for u in aniversariantes if u.nascimento and u.nascimento.month == month]

    pending_count = 0
    pending_preview = []
    if current_user.role in ["manager", "admin"]:
        pending_preview = (User.query
            .filter_by(status="pending")
            .order_by(User.created_at.desc())
            .limit(3).all()
        )
        pending_count = (User.query.filter_by(status="pending").count())

    return render_template(
        "main/dashboard.html",
        announcements=announcements,
        aniversariantes=aniversariantes_mes,
        pending_count=pending_count,
        pending_preview=pending_preview,
        kpis=None
    )
