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
    tipo = request.args.get("tipo")
    setor = request.args.get("setor")
    
    query = Announcement.query
    if tipo:
        query = query.filter_by(tipo=tipo)
    if setor:
        query = query.filter_by(setor=setor)

    announcements = query.order_by(Announcement.created_at.desc()).all()
    # Lista de setores para o filtro (pode vir do banco se preferir)
    sectors = [{"name": "UTI Adulto"}, {"name": "Hospital"}] 
    
    return render_template("announcements/index.html", 
                           title="Avisos", 
                           announcements=announcements, 
                           sectors=sectors)

@bp.get("/new")
@login_required
@require_roles("manager", "admin")
def new():
    return render_template("announcements/new.html", title="Novo aviso")

@bp.post("/new")
@login_required
@require_roles("manager", "admin")
def create():
    tipo = (request.form.get("tipo") or "info").strip()
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    setor = (request.form.get("setor") or "").strip() or None
    is_pinned = (request.form.get("is_pinned") == "on")

    if not title:
        flash("Título é obrigatório.", "warning")
        return redirect(url_for("announcements.new"))

    a = Announcement(
        tipo=tipo,
        title=title,
        body=body,
        setor=setor,
        is_pinned=is_pinned,
        created_by_id=current_user.id,
    )

    try:
        db.session.add(a)
        db.session.commit()
        flash("Aviso publicado.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao salvar: {str(e)}", "danger")
        
    return redirect(url_for("announcements.index"))

@bp.get("/<int:id>")
@login_required
@require_active
def detail(id):
    a = Announcement.query.get_or_404(id)
    # Lógica de marcação de leitura
    exists = AnnouncementRead.query.filter_by(
        announcement_id=a.id, user_id=current_user.id
    ).first()
    if not exists:
        db.session.add(AnnouncementRead(announcement_id=a.id, user_id=current_user.id))
        db.session.commit()

    unread_users, read_users = [], []
    if current_user.role in ["manager", "admin"]:
        reads = AnnouncementRead.query.filter_by(announcement_id=a.id).all()
        read_map = {r.user_id: r.read_at for r in reads}
        users_q = User.query.filter_by(status="active").all()
        for u in users_q:
            if u.id in read_map:
                read_users.append((u, read_map[u.id]))
            else:
                unread_users.append(u)

    return render_template("announcements/detail.html", title="Aviso", a=a, 
                           read_users=read_users, unread_users=unread_users)

@bp.get("/<int:id>/edit")
@login_required
@require_roles("manager", "admin")
def edit(id):
    a = Announcement.query.get_or_404(id)
    return render_template("announcements/new.html", title="Editar Aviso", a=a)

@bp.post("/<int:id>/edit")
@login_required
@require_roles("manager", "admin")
def update(id):
    a = Announcement.query.get_or_404(id)
    a.title = request.form.get("title")
    a.body = request.form.get("body")
    a.tipo = request.form.get("tipo")
    a.setor = request.form.get("setor")
    db.session.commit()
    flash("Aviso atualizado!", "success")
    return redirect(url_for("announcements.index"))

@bp.post("/<int:id>/delete")
@login_required
@require_roles("manager", "admin")
def delete(id):
    a = Announcement.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash("Aviso excluído!", "success")
    return redirect(url_for("announcements.index"))

@bp.post("/<int:id>/toggle")
@login_required
@require_roles("manager", "admin")
def toggle(id):
    a = Announcement.query.get_or_404(id)
    a.active = not a.active
    db.session.commit()
    status = "ativado" if a.active else "desativado"
    flash(f"Aviso {status}!", "info")
    return redirect(url_for("announcements.index"))