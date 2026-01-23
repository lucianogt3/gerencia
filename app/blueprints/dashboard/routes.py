from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import extract
from datetime import date

# Import dos modelos necessários para os KPIs
from app.models.user import User
from app.models.announcement import Announcement

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@bp.route("/")
@login_required
def index():
    # 1. Busca usuários pendentes (apenas para Admin/Manager)
    pending_list = []
    pending_count = 0
    
    if current_user.role in ['manager', 'admin']:
        pending_list = User.query.filter_by(status="pending").all()
        pending_count = len(pending_list)

    # 2. Busca aniversariantes do mês atual
    today = date.today()
    aniversariantes = User.query.filter(
        extract('month', User.nascimento) == today.month,
        User.status == 'active'
    ).order_by(extract('day', User.nascimento)).all()

    # 3. Busca últimos avisos
    # (Traz os 5 mais recentes)
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        pending_list=pending_list,
        pending_count=pending_count,
        aniversariantes=aniversariantes,
        announcements=announcements
    )