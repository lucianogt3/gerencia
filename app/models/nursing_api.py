from __future__ import annotations

import calendar
from datetime import datetime, date

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    Sector, User,
    NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell, NursingDailyOverride
)

bp = Blueprint("nursing_api", __name__, url_prefix="/api/nursing")


# ==========================
# Constantes / Nomenclaturas
# ==========================

# status do dia na escala diária (override)
DAY_STATUS = {"OK", "FALTA", "ATESTADO", "TROCA", "REMANEJADO", "EXTRA", "PENDENTE"}

# shifts válidos no seu modelo mensal (NÃO coloque F/FE/AT aqui; isso é status/motivo, não turno)
VALID_SHIFTS = {"D", "N", "M", "T", "MT"}

# padrões de trabalho para auto-preenchimento mensal
# (você pode renomear como quiser, mas esses são bem claros)
WORK_PATTERNS = {
    "12X36_D_IMPAR",
    "12X36_D_PAR",
    "12X36_N_IMPAR",
    "12X36_N_PAR",
    "MT_M",   # seg-sex manhã
    "MT_T",   # seg-sex tarde
}


# ==========================
# Helpers
# ==========================

def _require_manager() -> bool:
    return getattr(current_user, "role", "") in ("manager", "admin")


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _is_weekday(year: int, month: int, day: int) -> bool:
    # 0=segunda ... 6=domingo
    return date(year, month, day).weekday() <= 4


def _pattern_should_work(pattern: str, year: int, month: int, day: int) -> tuple[bool, str | None]:
    """
    Retorna (trabalha_hoje, shift_hoje)
    Se não trabalha, shift vem None.
    """
    pattern = (pattern or "").strip().upper()

    # 12x36: trabalha alternado pelo número do dia (ímpar/par)
    if pattern == "12X36_D_IMPAR":
        return (day % 2 == 1, "D")
    if pattern == "12X36_D_PAR":
        return (day % 2 == 0, "D")
    if pattern == "12X36_N_IMPAR":
        return (day % 2 == 1, "N")
    if pattern == "12X36_N_PAR":
        return (day % 2 == 0, "N")

    # MT: seg-sex
    if pattern == "MT_M":
        return (_is_weekday(year, month, day), "M")
    if pattern == "MT_T":
        return (_is_weekday(year, month, day), "T")

    # se vier vazio/desconhecido, não preenche nada automaticamente
    return (False, None)


def _apply_pattern_to_monthly_cells(
    sched: NursingMonthlySchedule,
    role: str,
    position: int,
    user_id: int,
    pattern: str,
) -> None:
    """
    Gera/atualiza células do mês para a combinação (role, position) preenchendo planned_user_id
    nos dias em que trabalha, e removendo (setando None) nos dias em que não trabalha.

    Mantém seu modelo atual: NursingMonthlyCell(day, shift, role, position -> planned_user_id)
    """
    year, month = sched.year, sched.month
    dim = _days_in_month(year, month)

    # busca todas as células do mês desta "linha"
    cells = NursingMonthlyCell.query.filter_by(
        schedule_id=sched.id,
        role=role,
        position=position,
    ).all()

    # index por dia para facilitar
    # OBS: como shift pode variar por dia, index por (day, shift)
    idx = {(c.day, c.shift): c for c in cells}

    for day in range(1, dim + 1):
        works, sh = _pattern_should_work(pattern, year, month, day)

        if works and sh:
            # garante célula do dia+shift preenchida com o user_id
            c = idx.get((day, sh))
            if not c:
                c = NursingMonthlyCell(
                    schedule_id=sched.id,
                    day=day,
                    shift=sh,
                    role=role,
                    position=position,
                    planned_user_id=user_id,
                )
                db.session.add(c)
            else:
                c.planned_user_id = user_id

            # se existirem células no mesmo day com outros shifts por causa de edição antiga, limpe:
            for other_shift in list(VALID_SHIFTS):
                if other_shift != sh:
                    oc = idx.get((day, other_shift))
                    if oc and oc.planned_user_id == user_id:
                        oc.planned_user_id = None

        else:
            # não trabalha: se tiver célula com esse user_id, limpa
            for sh2 in VALID_SHIFTS:
                c2 = idx.get((day, sh2))
                if c2 and c2.planned_user_id == user_id:
                    c2.planned_user_id = None


# ==========================
# Setores
# ==========================

@bp.get("/sectors")
@login_required
def list_sectors():
    sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()
    return jsonify([{"id": s.id, "name": s.name} for s in sectors])


@bp.post("/sectors")
@login_required
def create_sector():
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nome do setor é obrigatório"}), 400

    exists = Sector.query.filter_by(name=name).first()
    if exists:
        return jsonify({"error": "Setor já existe"}), 409

    s = Sector(name=name, active=True)
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id, "name": s.name})


# ==========================
# Escala Mensal
# ==========================

@bp.post("/monthly")
@login_required
def create_or_get_monthly():
    """Gerência cria (ou busca) escala mensal por setor/ano/mês."""
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    data = request.get_json(force=True) or {}
    sector_id = int(data.get("sector_id") or 0)
    year = int(data.get("year") or 0)
    month = int(data.get("month") or 0)

    if not sector_id or year < 2000 or month < 1 or month > 12:
        return jsonify({"error": "sector_id/ano/mês inválidos"}), 400

    sched = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id, year=year, month=month
    ).first()

    if not sched:
        sched = NursingMonthlySchedule(
            sector_id=sector_id,
            year=year,
            month=month,
            status="draft",
            created_by_id=getattr(current_user, "id", None),
        )
        db.session.add(sched)
        db.session.commit()

    return jsonify({
        "id": sched.id,
        "sector_id": sched.sector_id,
        "year": sched.year,
        "month": sched.month,
        "status": sched.status,
    })


@bp.get("/monthly/<int:schedule_id>")
@login_required
def get_monthly(schedule_id: int):
    """
    Retorna estrutura para montar a grade:
    - dias do mês
    - membros (linhas)
    - células planejadas
    """
    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    sector = Sector.query.get(sched.sector_id)

    if getattr(current_user, "role", "") not in ("manager", "admin") and sched.status != "published":
        return jsonify({"error": "Escala não publicada"}), 403

    days_in_month = _days_in_month(sched.year, sched.month)

    members = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, active=True).all()
    cells = NursingMonthlyCell.query.filter_by(schedule_id=sched.id).all()

    member_rows = []
    for m in sorted(members, key=lambda x: (x.role, x.position)):
        u = User.query.get(m.user_id)
        member_rows.append({
            "id": m.id,
            "user_id": m.user_id,
            "name": u.nome if u else f"User {m.user_id}",
            "role": m.role,
            "position": m.position,
            # NOVO: padrão para UI saber e desenhar "F" nos dias que não tem célula
            "work_pattern": getattr(m, "work_pattern", None),
            "matricula": getattr(u, "matricula", None) if u else None,
        })

    # mantém seu formato atual de cells (para não quebrar o front que já usa isso)
    cell_map: dict[str, int | None] = {}
    for c in cells:
        key = f"{c.day}:{c.shift}:{c.role}:{c.position}"
        cell_map[key] = c.planned_user_id

    return jsonify({
        "schedule": {
            "id": sched.id,
            "sector": {"id": sector.id, "name": sector.name} if sector else None,
            "year": sched.year,
            "month": sched.month,
            "status": sched.status,
            "days_in_month": days_in_month,
        },
        "members": member_rows,
        "cells": cell_map,
    })


@bp.post("/monthly/<int:schedule_id>/members")
@login_required
def upsert_member(schedule_id: int):
    """
    Gerência: adiciona colaborador como linha da grade (role + position)
    e (NOVO) aplica padrão de trabalho preenchendo o mês automaticamente.
    """
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    if sched.status != "draft":
        return jsonify({"error": "Escala não está em rascunho"}), 400

    data = request.get_json(force=True) or {}

    user_id = int(data.get("user_id") or 0)
    role = (data.get("role") or "").strip().lower()  # tecnico / enfermeiro
    position = int(data.get("position") or 0)

    # NOVO: padrão de trabalho para auto-preencher
    work_pattern = (data.get("work_pattern") or "").strip().upper() or None
    if work_pattern and work_pattern not in WORK_PATTERNS:
        return jsonify({
            "error": "work_pattern inválido",
            "allowed": sorted(WORK_PATTERNS)
        }), 400

    if not user_id or role not in ("tecnico", "enfermeiro") or position <= 0:
        return jsonify({"error": "Dados inválidos"}), 400

    u = User.query.get(user_id)
    if not u:
        return jsonify({"error": "Usuário não encontrado"}), 404

    m = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=user_id).first()

    if not m:
        m = NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=user_id,
            role=role,
            position=position,
            active=True,
        )
        # se seu model tiver essa coluna, ok; se não tiver, você cria a migração
        if hasattr(m, "work_pattern"):
            m.work_pattern = work_pattern
        db.session.add(m)
    else:
        m.role = role
        m.position = position
        m.active = True
        if hasattr(m, "work_pattern") and work_pattern:
            m.work_pattern = work_pattern

    db.session.flush()  # garante m.id sem commit ainda

    # aplica padrão no mês (auto preenche)
    pattern_to_use = work_pattern
    if hasattr(m, "work_pattern"):
        pattern_to_use = m.work_pattern or work_pattern

    if pattern_to_use:
        _apply_pattern_to_monthly_cells(
            sched=sched,
            role=role,
            position=position,
            user_id=user_id,
            pattern=pattern_to_use,
        )

    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/monthly/<int:schedule_id>/cell")
@login_required
def set_monthly_cell(schedule_id: int):
    """
    Gerência: define célula planejada
    (dia + turno + role + position -> planned_user_id).

    OBS:
      - Aqui é "manual", por clique.
      - Motivos (atestado/falta/licença) devem ir para o DAILY override.
    """
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    if sched.status != "draft":
        return jsonify({"error": "Escala não está em rascunho"}), 400

    data = request.get_json(force=True) or {}
    day = int(data.get("day") or 0)
    shift = (data.get("shift") or "").strip().upper()
    role = (data.get("role") or "").strip().lower()
    position = int(data.get("position") or 0)

    planned_user_id = data.get("planned_user_id")
    planned_user_id = int(planned_user_id) if planned_user_id else None

    dim = _days_in_month(sched.year, sched.month)
    if day < 1 or day > dim:
        return jsonify({"error": "Dia inválido"}), 400
    if shift not in VALID_SHIFTS:
        return jsonify({"error": "Turno inválido"}), 400
    if role not in ("tecnico", "enfermeiro"):
        return jsonify({"error": "Role inválida"}), 400
    if position <= 0:
        return jsonify({"error": "Posição inválida"}), 400

    if planned_user_id:
        u = User.query.get(planned_user_id)
        if not u:
            return jsonify({"error": "planned_user_id não encontrado"}), 404

    cell = NursingMonthlyCell.query.filter_by(
        schedule_id=sched.id,
        day=day,
        shift=shift,
        role=role,
        position=position,
    ).first()

    if not cell:
        cell = NursingMonthlyCell(
            schedule_id=sched.id,
            day=day,
            shift=shift,
            role=role,
            position=position,
            planned_user_id=planned_user_id,
        )
        db.session.add(cell)
    else:
        cell.planned_user_id = planned_user_id

    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/monthly/<int:schedule_id>/publish")
@login_required
def publish_monthly(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    sched.status = "published"
    sched.published_at = datetime.utcnow()
    sched.published_by_id = getattr(current_user, "id", None)

    db.session.commit()
    return jsonify({"ok": True})


# ==========================
# Escala Diária (override)
# ==========================

@bp.get("/daily")
@login_required
def get_daily_view():
    """
    Retorna Escala Diária consolidada:
    - pega plano mensal (cells do dia/turno)
    - aplica override (daily_overrides) se houver
    """
    sector_id = int(request.args.get("sector_id") or 0)
    dt_str = (request.args.get("date") or "").strip()
    shift = (request.args.get("shift") or "").strip().upper()

    if not sector_id or not dt_str or shift not in VALID_SHIFTS:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    dt = date.fromisoformat(dt_str)

    sched = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id, year=dt.year, month=dt.month, status="published"
    ).first()
    if not sched:
        return jsonify({"error": "Escala mensal não publicada para este setor/mês"}), 404

    day = dt.day

    monthly_cells = NursingMonthlyCell.query.filter_by(
        schedule_id=sched.id, day=day, shift=shift
    ).all()

    overrides = NursingDailyOverride.query.filter_by(
        sector_id=sector_id, date=dt, shift=shift
    ).all()
    ov_map = {(o.role, o.position): o for o in overrides}

    rows = []
    for c in sorted(monthly_cells, key=lambda x: (x.role, x.position)):
        planned_u = User.query.get(c.planned_user_id) if c.planned_user_id else None
        ov = ov_map.get((c.role, c.position))

        if ov:
            actual_u = User.query.get(ov.actual_user_id) if ov.actual_user_id else None
            rows.append({
                "role": c.role,
                "position": c.position,
                "planned_user": {"id": planned_u.id, "name": planned_u.nome} if planned_u else None,
                "actual_user": {"id": actual_u.id, "name": actual_u.nome} if actual_u else None,
                "status": ov.status,
                "from_sector_id": ov.from_sector_id,
                "extra_type": ov.extra_type,
                "comp_day": ov.comp_day.isoformat() if ov.comp_day else None,
                "notes": ov.notes,
            })
        else:
            rows.append({
                "role": c.role,
                "position": c.position,
                "planned_user": {"id": planned_u.id, "name": planned_u.nome} if planned_u else None,
                "actual_user": None,
                "status": "OK",
                "from_sector_id": None,
                "extra_type": None,
                "comp_day": None,
                "notes": None,
            })

    return jsonify({
        "schedule_id": sched.id,
        "sector_id": sector_id,
        "date": dt.isoformat(),
        "shift": shift,
        "rows": rows,
    })


@bp.post("/daily/override")
@login_required
def set_daily_override():
    """
    Enfermeiro registra mudanças (dia):
    - falta
    - atestado pendente
    - remanejamento
    - extra/folga
    """
    data = request.get_json(force=True) or {}

    sector_id = int(data.get("sector_id") or 0)
    dt = date.fromisoformat(data.get("date"))
    shift = (data.get("shift") or "").strip().upper()

    role = (data.get("role") or "").strip().lower()
    position = int(data.get("position") or 0)

    status = (data.get("status") or "OK").strip().upper()

    planned_user_id = data.get("planned_user_id")
    planned_user_id = int(planned_user_id) if planned_user_id else None

    actual_user_id = data.get("actual_user_id")
    actual_user_id = int(actual_user_id) if actual_user_id else None

    from_sector_id = data.get("from_sector_id")
    from_sector_id = int(from_sector_id) if from_sector_id else None

    extra_type = (data.get("extra_type") or "").strip().upper() or None
    comp_day = data.get("comp_day")
    comp_day = date.fromisoformat(comp_day) if comp_day else None

    notes = (data.get("notes") or "").strip() or None

    if not sector_id or shift not in VALID_SHIFTS:
        return jsonify({"error": "Setor/turno inválidos"}), 400
    if role not in ("tecnico", "enfermeiro") or position <= 0:
        return jsonify({"error": "Role/posição inválidos"}), 400
    if status not in DAY_STATUS:
        return jsonify({"error": "Status inválido"}), 400

    sched = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id, year=dt.year, month=dt.month, status="published"
    ).first()
    if not sched:
        return jsonify({"error": "Escala mensal não publicada para este setor/mês"}), 404

    ov = NursingDailyOverride.query.filter_by(
        sector_id=sector_id, date=dt, shift=shift, role=role, position=position
    ).first()

    if not ov:
        ov = NursingDailyOverride(
            schedule_id=sched.id,
            sector_id=sector_id,
            date=dt,
            shift=shift,
            role=role,
            position=position,
            created_by_id=getattr(current_user, "id", None),
        )
        db.session.add(ov)

    ov.planned_user_id = planned_user_id
    ov.actual_user_id = actual_user_id
    ov.status = status
    ov.from_sector_id = from_sector_id
    ov.extra_type = extra_type
    ov.comp_day = comp_day
    ov.notes = notes

    db.session.commit()
    return jsonify({"ok": True})
