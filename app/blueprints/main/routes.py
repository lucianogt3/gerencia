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
    # Avisos simples (últimos 5)
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()

    # Aniversariantes do mês (simples)
    today = date.today()
    month = today.month
    aniversariantes = (
        User.query
        .filter(User.nascimento.isnot(None))
        .all()
    )
    aniversariantes_mes = [u for u in aniversariantes if u.nascimento and u.nascimento.month == month]

    return render_template("main/dashboard.html", announcements=announcements, aniversariantes=aniversariantes_mes)
