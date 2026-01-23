from __future__ import annotations

import calendar  # Adicionado para corrigir erro no _autofill_cells
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    User,
    Sector,
    NursingMonthlySchedule,
    NursingMonthlyMember,
    NursingMonthlyCell,
)

bp = Blueprint("nursing_api", __name__, url_prefix="/api/nursing")


# =========================
# Helpers
# =========================
ACTIVE_STATUSES = {"active", "ativo", "approved"}


def _require_manager() -> bool:
    return getattr(current_user, "role", "") in ("manager", "admin")


def _get_schedule_or_404(schedule_id: int):
    sched = NursingMonthlySchedule.query.get(int(schedule_id))
    if not sched:
        return None, (jsonify({"error": "Escala não encontrada"}), 404)
    return sched, None


def _is_locked(schedule: NursingMonthlySchedule) -> bool:
    """Verifica se a escala está fechada/publicada."""
    if hasattr(schedule, "is_published") and bool(getattr(schedule, "is_published")):
        return True
    if hasattr(schedule, "status") and (getattr(schedule, "status") == "published"):
        return True
    return False


def _apply_active_filter(query):
    """Filtra usuários ativos sem quebrar quando o campo/status variar."""
    if hasattr(User, "status"):
        try:
            query = query.filter(User.status.in_(list(ACTIVE_STATUSES)))
        except Exception:
            pass
    return query


def _user_sector_field_name() -> str | None:
    cols = {c.name for c in getattr(User, "__table__").columns}
    if "sector_id" in cols:
        return "sector_id"
    if "setor_id" in cols:
        return "setor_id"
    if "setor" in cols:
        return "setor"
    return None


def _schedule_status_field_name() -> str | None:
    cols = {c.name for c in getattr(NursingMonthlySchedule, "__table__").columns}
    if "status" in cols:
        return "status"
    return None


def _cell_find_or_create(schedule_id: int, day: int, member_id: int | None, user_id: int | None):
    """
    Tenta localizar uma célula de escala de forma tolerante.
    """
    q = NursingMonthlyCell.query.filter_by(schedule_id=schedule_id, day=day)
    cols = {c.name for c in getattr(NursingMonthlyCell, "__table__").columns}

    if member_id and "member_id" in cols:
        q = q.filter_by(member_id=member_id)
    elif user_id:
        if "user_id" in cols:
            q = q.filter_by(user_id=user_id)
        elif "planned_user_id" in cols:
            q = q.filter_by(planned_user_id=user_id)

    cell = q.first()
    if cell:
        return cell

    # cria novo
    cell = NursingMonthlyCell(schedule_id=schedule_id, day=day)

    if member_id and "member_id" in cols:
        setattr(cell, "member_id", member_id)
    elif user_id:
        if "user_id" in cols:
            setattr(cell, "user_id", user_id)
        elif "planned_user_id" in cols:
            setattr(cell, "planned_user_id", user_id)

    db.session.add(cell)
    return cell


def _autofill_cells(schedule: NursingMonthlySchedule, user: User):
    """Preenche D ou N em TODOS os dias do mês baseado no turno do usuário."""
    try:
        days_in_month = calendar.monthrange(schedule.year, schedule.month)[1]
    except Exception:
        return # Evita erro se year/month invalidos

    turno = (getattr(user, "turno", "") or "").strip().lower()
    shift = "D" if "di" in turno else ("N" if "no" in turno else "")

    if not shift:
        return

    # Procura coluna correta (user_id vs planned_user_id)
    cols = {c.name for c in getattr(NursingMonthlyCell, "__table__").columns}
    user_fk_field = "user_id" if "user_id" in cols else "planned_user_id"

    for day in range(1, days_in_month + 1):
        # Busca célula existente
        criteria = {
            "schedule_id": schedule.id,
            "day": day,
            user_fk_field: user.id
        }
        cell = NursingMonthlyCell.query.filter_by(**criteria).first()

        if cell:
            if hasattr(cell, "shift"):
                cell.shift = shift
        else:
            new_cell = NursingMonthlyCell(schedule_id=schedule.id, day=day)
            setattr(new_cell, user_fk_field, user.id)
            if hasattr(new_cell, "shift"):
                new_cell.shift = shift
            db.session.add(new_cell)


# =========================
# Sectors
# =========================
@bp.get("/sectors")
@login_required
def list_sectors():
    q = Sector.query
    if hasattr(Sector, "active"):
        q = q.filter(Sector.active == True)  # noqa: E712
    q = q.order_by(Sector.name.asc())
    sectors = q.all()
    return jsonify([{"id": s.id, "name": s.name} for s in sectors])


@bp.post("/sectors")
@login_required
def create_sector():
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name obrigatório"}), 400

    s = Sector(name=name)
    if hasattr(Sector, "active"):
        setattr(s, "active", True)
    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True, "id": s.id, "name": s.name})


# =========================
# Monthly schedule
# =========================
@bp.get("/monthly")
@login_required
def monthly_list():
    year = int(request.args.get("year") or 0)
    month = int(request.args.get("month") or 0)

    q = NursingMonthlySchedule.query
    if year:
        q = q.filter_by(year=year)
    if month:
        q = q.filter_by(month=month)

    q = q.order_by(NursingMonthlySchedule.id.asc())
    rows = q.all()

    out = []
    for s in rows:
        sec = Sector.query.get(getattr(s, "sector_id", None)) if getattr(s, "sector_id", None) else None
        out.append({
            "id": s.id,
            "year": getattr(s, "year", None),
            "month": getattr(s, "month", None),
            "sector_id": getattr(s, "sector_id", None),
            "sector_name": sec.name if sec else None,
            "status": getattr(s, _schedule_status_field_name() or "status", None) if _schedule_status_field_name() else None,
        })
    return jsonify({"items": out})


@bp.post("/monthly")
@login_required
def monthly_create():
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    data = request.get_json(silent=True) or {}
    year = int(data.get("year") or 0)
    month = int(data.get("month") or 0)
    sector_id = int(data.get("sector_id") or 0)

    if not (year and month and sector_id):
        return jsonify({"error": "year, month, sector_id obrigatórios"}), 400

    existing = NursingMonthlySchedule.query.filter_by(year=year, month=month, sector_id=sector_id).first()
    if existing:
        return jsonify({"ok": True, "id": existing.id, "already": True})

    s = NursingMonthlySchedule(year=year, month=month, sector_id=sector_id)
    status_field = _schedule_status_field_name()
    if status_field:
        setattr(s, status_field, "draft")

    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True, "id": s.id})


@bp.get("/monthly/<int:schedule_id>")
@login_required
def monthly_get(schedule_id: int):
    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err

    sec = Sector.query.get(getattr(sched, "sector_id", None)) if getattr(sched, "sector_id", None) else None
    status_field = _schedule_status_field_name()

    return jsonify({
        "id": sched.id,
        "year": getattr(sched, "year", None),
        "month": getattr(sched, "month", None),
        "sector_id": getattr(sched, "sector_id", None),
        "sector_name": sec.name if sec else None,
        "status": getattr(sched, status_field, None) if status_field else None,
        "is_locked": _is_locked(sched)
    })


# =========================
# Members
# =========================
@bp.route("/monthly/<int:schedule_id>/members", methods=["GET", "POST", "DELETE"])
@login_required
def monthly_members(schedule_id: int):
    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err

    if request.method == "GET":
        members = (NursingMonthlyMember.query
                   .filter_by(schedule_id=sched.id)
                   .order_by(NursingMonthlyMember.position.asc(), NursingMonthlyMember.id.asc())
                   .all())

        items = []
        for m in members:
            u = User.query.get(getattr(m, "user_id", None)) if getattr(m, "user_id", None) else None
            items.append({
                "member_id": m.id,
                "user_id": getattr(m, "user_id", None),
                "name": getattr(u, "nome", None) if u else None,
                "matricula": getattr(u, "matricula", None) if u else None,
                "role": getattr(m, "role", None),
                "active": getattr(m, "active", True),
                "position": getattr(m, "position", None),
                "sector_id": getattr(u, "sector_id", None) if u else None,
            })
        return jsonify({"items": items})

    # POST/DELETE exigem manager
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    if _is_locked(sched):
        return jsonify({"error": "Escala fechada/publicada"}), 409

    data = request.get_json(silent=True) or {}

    if request.method == "POST":
        user_id = int(data.get("user_id") or 0)
        if not user_id:
            return jsonify({"error": "user_id obrigatório"}), 400

        u = User.query.get(user_id)
        if not u:
            return jsonify({"error": "Usuário não encontrado"}), 404

        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=user_id).first()
        if exists:
            return jsonify({"ok": True, "already": True})

        m = NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=user_id,
            role=getattr(u, "role", "staff"),
            position=9999,
            active=True
        )
        db.session.add(m)
        db.session.commit()
        return jsonify({"ok": True, "member_id": m.id})

    # DELETE
    member_id = int(data.get("member_id") or 0)
    if not member_id:
        return jsonify({"error": "member_id obrigatório"}), 400

    m = NursingMonthlyMember.query.filter_by(id=member_id, schedule_id=sched.id).first()
    if not m:
        return jsonify({"error": "Membro não encontrado"}), 404

    db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


# =========================
# Cell edit
# =========================
@bp.post("/monthly/<int:schedule_id>/cell")
@login_required
def monthly_cell_set(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err
    
    if _is_locked(sched):
        return jsonify({"error": "Escala fechada/publicada"}), 409

    data = request.get_json(silent=True) or {}
    day = int(data.get("day") or 0)
    code = (data.get("code") or "").strip()
    member_id = int(data.get("member_id") or 0) or None
    user_id = int(data.get("user_id") or 0) or None

    if not day:
        return jsonify({"error": "day obrigatório"}), 400

    cols = {c.name for c in getattr(NursingMonthlyCell, "__table__").columns}
    code_field = "code" if "code" in cols else ("value" if "value" in cols else None)

    cell = _cell_find_or_create(sched.id, day, member_id, user_id)
    if code_field:
        setattr(cell, code_field, code)

    db.session.commit()
    return jsonify({"ok": True})


# =========================
# Publish
# =========================
@bp.post("/monthly/<int:schedule_id>/publish")
@login_required
def monthly_publish(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err

    status_field = _schedule_status_field_name()
    if status_field:
        setattr(sched, status_field, "published")
    elif hasattr(sched, "is_published"):
        setattr(sched, "is_published", True)

    db.session.commit()
    return jsonify({"ok": True})


# =========================
# DAILY
# =========================
@bp.get("/daily")
@login_required
def daily_get():
    return jsonify({"ok": True})


@bp.post("/daily/override")
@login_required
def daily_override():
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403
    return jsonify({"ok": True})


# =========================
# Search & Utils
# =========================
@bp.get("/users/search")
@login_required
def users_search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"items": []})

    query = _apply_active_filter(User.query)
    conds = []
    if hasattr(User, "nome"):
        conds.append(User.nome.ilike(f"%{q}%"))
    if hasattr(User, "matricula"):
        conds.append(User.matricula.ilike(f"%{q}%"))

    if conds:
        query = query.filter(or_(*conds))

    if hasattr(User, "nome"):
        query = query.order_by(User.nome.asc())

    users = query.limit(30).all()
    items = []
    for u in users:
        sec_id = getattr(u, "sector_id", None)
        sec_name = None
        if sec_id:
            sec = Sector.query.get(sec_id)
            sec_name = sec.name if sec else None

        items.append({
            "id": u.id,
            "name": getattr(u, "nome", None),
            "matricula": getattr(u, "matricula", None),
            "sector_id": sec_id,
            "sector_name": sec_name,
            "turno": getattr(u, "turno", None),
            "role_label": getattr(u, "role", None),
        })

    return jsonify({"items": items})


@bp.post("/monthly/<int:schedule_id>/add_user_auto")
@login_required
def add_user_auto(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err
        
    if _is_locked(sched):
        return jsonify({"error": "Escala fechada"}), 409

    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id") or 0)
    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400

    u = User.query.get(user_id)
    if not u:
        return jsonify({"error": "Usuário não encontrado"}), 404

    exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
    if exists:
        return jsonify({"ok": True, "already": True})

    db.session.add(NursingMonthlyMember(
        schedule_id=sched.id,
        user_id=u.id,
        role=getattr(u, "role", "staff"),
        position=9999,
        active=True
    ))
    db.session.commit()
    
    # Opcional: preencher turno automatico
    # _autofill_cells(sched, u) 
    # db.session.commit()

    return jsonify({"ok": True})


@bp.post("/transfer")
@login_required
def transfer_user_between_sectors():
    """
    Remove de outras escalas do mesmo mês e adiciona na atual.
    Verifica se a escala destino está travada.
    """
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id") or 0)
    
    # Suporta schedule_id OU (year, month, to_sector_id)
    schedule_id = int(data.get("schedule_id") or 0)
    year = int(data.get("year") or 0)
    month = int(data.get("month") or 0)

    if schedule_id:
        sched = NursingMonthlySchedule.query.get(schedule_id)
        if sched:
            year = sched.year
            month = sched.month
    elif year and month and data.get("to_sector_id"):
        # Tenta achar o schedule pelo setor
        sched = NursingMonthlySchedule.query.filter_by(
            year=year, month=month, sector_id=int(data.get("to_sector_id"))
        ).first()
    else:
        sched = None

    if not sched:
        return jsonify({"error": "Escala destino não encontrada"}), 404
        
    if _is_locked(sched):
        return jsonify({"error": "Escala publicada. Não pode transferir."}), 409

    if not user_id:
        return jsonify({"error": "user_id obrigatório"}), 400

    # 1. Remove das outras do mesmo mês
    other_schedules = NursingMonthlySchedule.query.filter_by(year=year, month=month).all()
    removed_from = []
    for osched in other_schedules:
        if osched.id == sched.id:
            continue
            
        # Se a outra estiver fechada, tecnicamente não deveria remover, 
        # mas "transferência" implica sair de lá. 
        # Vamos assumir que gerente pode tirar.

        m = NursingMonthlyMember.query.filter_by(schedule_id=osched.id, user_id=user_id).first()
        if m:
            db.session.delete(m)
            removed_from.append(osched.id)
            
            # Limpa células antigas
            cols = {c.name for c in getattr(NursingMonthlyCell, "__table__").columns}
            if "user_id" in cols:
                NursingMonthlyCell.query.filter_by(schedule_id=osched.id, user_id=user_id).delete()
            elif "planned_user_id" in cols:
                NursingMonthlyCell.query.filter_by(schedule_id=osched.id, planned_user_id=user_id).delete()

    # 2. Adiciona na nova (se não existir)
    exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=user_id).first()
    added_id = None
    
    if exists:
        # Garante que está atualizado
        added_id = exists.id
    else:
        u = User.query.get(user_id)
        if not u:
            return jsonify({"error": "Usuário não encontrado"}), 404

        new_member = NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=u.id,
            role=getattr(u, "role", "staff"),
            position=9999,
            active=True
        )
        # Se tiver campo sector_id no membro
        if hasattr(new_member, "sector_id") and hasattr(sched, "sector_id"):
             setattr(new_member, "sector_id", sched.sector_id)
             
        db.session.add(new_member)
        db.session.flush() # para ter ID
        added_id = new_member.id
        
        # Opcional: autofill
        # _autofill_cells(sched, u)

    db.session.commit()
    return jsonify({
        "ok": True, 
        "removed_from": removed_from, 
        "added_to": sched.id, 
        "member_id": added_id
    })


@bp.post("/monthly/<int:schedule_id>/import_sector")
@login_required
def import_sector(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched, err = _get_schedule_or_404(schedule_id)
    if err:
        return err

    if _is_locked(sched):
        return jsonify({"error": "Escala fechada"}), 409

    sector_id = getattr(sched, "sector_id", None)
    if not sector_id:
        return jsonify({"ok": True, "added": 0})

    q = _apply_active_filter(User.query)
    sector_field = _user_sector_field_name()
    
    if sector_field == "sector_id":
        q = q.filter(User.sector_id == sector_id)
    elif sector_field == "setor_id":
        q = q.filter(User.setor_id == sector_id)
    elif sector_field == "setor":
        sec = Sector.query.get(sector_id)
        if sec:
            q = q.filter(User.setor == sec.name)

    users = q.all()
    added = 0
    for u in users:
        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
        if exists:
            continue

        db.session.add(NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=u.id,
            role=getattr(u, "role", "staff"),
            position=9999,
            active=True
        ))
        added += 1

    db.session.commit()
    return jsonify({"ok": True, "added": added})