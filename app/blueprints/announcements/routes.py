from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ...extensions import db
from ...utils.security import require_roles, require_active
from ...models.announcement import Announcement
from ...models.announcement_read import AnnouncementRead
from ...models.user import User

bp = Blueprint("announcements", __name__, url_prefix="/announcements")

@bp.get("/")
@login_required
@require_active
def index():
    items = Announcement.query.order_by(Announcement.created_at.desc()).limit(50).all()
    return render_template("announcements/index.html", title="Avisos", items=items)

@bp.get("/new")
@login_required
@require_roles("manager","admin")
def new():
    return render_template("announcements/new.html", title="Novo aviso")

@bp.post("/new")
@login_required
@require_roles("manager","admin")
def create():
    tipo = (request.form.get("tipo") or "info").strip()
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    setor = (request.form.get("setor") or "").strip() or None

    if not title:
        flash("Título é obrigatório.", "warning")
        return redirect(url_for("announcements.new"))

    a = Announcement(tipo=tipo, title=title, body=body, setor=setor)
    db.session.add(a)
    db.session.commit()
    flash("Aviso publicado.", "success")
    return redirect(url_for("announcements.index"))

@bp.get("/<int:announcement_id>")
@login_required
@require_active
def detail(announcement_id: int):
    a = Announcement.query.get_or_404(announcement_id)

    # marca como lido (idempotente)
    exists = AnnouncementRead.query.filter_by(announcement_id=a.id, user_id=current_user.id).first()
    if not exists:
        db.session.add(AnnouncementRead(announcement_id=a.id, user_id=current_user.id))
        db.session.commit()

    # gestão vê relatórios de leitura
    read_map = {}
    unread_users = []
    read_users = []
    if current_user.role in ["manager","admin"]:
        reads = AnnouncementRead.query.filter_by(announcement_id=a.id).all()
        read_map = {r.user_id: r.read_at for r in reads}

        users_q = User.query.filter_by(status="active").all()
        for u in users_q:
            if u.id in read_map:
                read_users.append((u, read_map[u.id]))
            else:
                unread_users.append(u)

    return render_template(
        "announcements/detail.html",
        title="Aviso",
        a=a,
        read_users=read_users,
        unread_users=unread_users
    )
