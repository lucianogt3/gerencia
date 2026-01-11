from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from ...extensions import db
from ...models import Sector, User

bp = Blueprint("settings", __name__, url_prefix="/settings")


def _require_manager():
    return getattr(current_user, "role", "") in ("manager", "admin")


@bp.get("/")
@login_required
def index():
    if not _require_manager():
        return render_template("errors/403.html"), 403
    return redirect(url_for("settings.sectors"))


# --------------------
# Setores
# --------------------
@bp.get("/sectors")
@login_required
def sectors():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    q = (request.args.get("q") or "").strip()
    query = Sector.query
    if q:
        query = query.filter(Sector.name.ilike(f"%{q}%"))

    sectors = query.order_by(Sector.active.desc(), Sector.name.asc()).all()
    return render_template("settings/sectors.html", title="Configurações • Setores", sectors=sectors, q=q)


@bp.post("/sectors/create")
@login_required
def sectors_create():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Nome do setor é obrigatório.", "danger")
        return redirect(url_for("settings.sectors"))

    exists = Sector.query.filter_by(name=name).first()
    if exists:
        flash("Setor já existe.", "warning")
        return redirect(url_for("settings.sectors"))

    s = Sector(name=name, active=True)
    db.session.add(s)
    db.session.commit()
    flash("Setor criado com sucesso.", "success")
    return redirect(url_for("settings.sectors"))


@bp.post("/sectors/<int:sector_id>/toggle")
@login_required
def sectors_toggle(sector_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    s = Sector.query.get_or_404(sector_id)
    s.active = not bool(s.active)
    db.session.commit()
    flash("Setor atualizado.", "success")
    return redirect(url_for("settings.sectors"))


# --------------------
# Colaboradores
# --------------------
@bp.get("/users")
@login_required
def users():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    q = (request.args.get("q") or "").strip()
    role = (request.args.get("role") or "").strip()
    status = (request.args.get("status") or "").strip()

    query = User.query
    if q:
        query = query.filter(
            (User.nome.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%")) |
            (User.matricula.ilike(f"%{q}%"))
        )
    if role:
        query = query.filter_by(role=role)
    if status:
        query = query.filter_by(status=status)

    users = query.order_by(User.status.asc(), User.nome.asc()).all()
    sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()

    return render_template(
        "settings/users.html",
        title="Configurações • Colaboradores",
        users=users,
        sectors=sectors,
        q=q,
        role=role,
        status=status,
    )


@bp.post("/users/<int:user_id>/toggle")
@login_required
def users_toggle(user_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    u = User.query.get_or_404(user_id)
    u.status = "inactive" if (u.status == "active") else "active"
    db.session.commit()
    flash("Usuário atualizado.", "success")
    return redirect(url_for("settings.users"))


@bp.post("/users/<int:user_id>/update")
@login_required
def users_update(user_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    u = User.query.get_or_404(user_id)

    setor = (request.form.get("setor") or "").strip() or None
    turno = (request.form.get("turno") or "").strip() or None
    role = (request.form.get("role") or "").strip() or None

    if hasattr(u, "setor"):
        u.setor = setor
    if hasattr(u, "turno"):
        u.turno = turno
    if role in ("staff", "nurse", "manager", "admin"):
        u.role = role

    db.session.commit()
    flash("Dados do colaborador atualizados.", "success")
    return redirect(url_for("settings.users"))


