from __future__ import annotations

import calendar
from typing import Any, Dict, List
from datetime import date

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Sector,
    User,
    NursingMonthlySchedule,
    NursingMonthlyMember,
    NursingMonthlyCell,
)

bp = Blueprint("nursing_ui", __name__, url_prefix="/nursing")


# =========================
# Helpers / Permissão
# =========================
MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def month_name(m: int) -> str:
    try:
        m = int(m)
    except Exception:
        return ""
    return MONTHS_PT[m - 1] if 1 <= m <= 12 else ""


@bp.app_context_processor
def inject_globals():
    return {
        "month_name": month_name,
        "current_year": date.today().year
    }

def _require_manager():
    if getattr(current_user, "role", "") not in ("manager", "admin"):
        abort(403)


def _month_nav(ano: int, mes: int):
    prev_ano, prev_mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    next_ano, next_mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return prev_ano, prev_mes, next_ano, next_mes


def _build_days(ano: int, mes: int) -> List[Dict[str, Any]]:
    last_day = calendar.monthrange(ano, mes)[1]
    out: List[Dict[str, Any]] = []
    for d in range(1, last_day + 1):
        wd = date(ano, mes, d).weekday()  # 0 seg ... 6 dom
        out.append({"day": d, "is_weekend": wd >= 5})
    return out


# =========================
# NÍVEL 1: Ano (cards de meses)
# =========================
@bp.get("/scales")
@login_required
def year_view():
    _require_manager()

    ano = int(request.args.get("ano") or date.today().year)

    months_list = []
    for m in range(1, 13):
        count = NursingMonthlySchedule.query.filter_by(year=ano, month=m).count()
        months_list.append({
            "num": m,
            "name": month_name(m),
            "active_scales_count": count
        })

    return render_template(
        "nursing/years_view.html",
        title=f"Escalas {ano}",
        ano=ano,
        months_list=months_list,
    )


# =========================
# NÍVEL 2: Mês (cards de setores com escala)
# =========================
@bp.get("/scales/<int:ano>/<int:mes>")
@login_required
def month_details(ano: int, mes: int):
    _require_manager()

    # escalas já criadas no mês
    schedules = (
        NursingMonthlySchedule.query
        .filter_by(year=ano, month=mes)
        .order_by(NursingMonthlySchedule.sector_id.asc())
        .all()
    )

    existing_scales = []
    used_sector_ids = set()

    for s in schedules:
        used_sector_ids.add(s.sector_id)
        sector = Sector.query.get(s.sector_id)
        prof_count = NursingMonthlyMember.query.filter_by(schedule_id=s.id, active=True).count()

        existing_scales.append({
            "id": s.id,
            "sector_id": s.sector_id,
            "sector_name": sector.name if sector else f"Setor {s.sector_id}",
            "prof_count": prof_count,
            "is_published": (s.status == "published"),
        })

    # setores disponíveis (ainda sem escala no mês)
    all_sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()
    available_sectors = [{"id": sec.id, "name": sec.name} for sec in all_sectors if sec.id not in used_sector_ids]

    return render_template(
        "nursing/month_details.html",
        title=f"{month_name(mes)} {ano}",
        ano=ano,
        mes=mes,
        month_label=month_name(mes),
        existing_scales=existing_scales,
        available_sectors=available_sectors,
    )


# =========================
# Ação: criar a escala (cria o card)
# =========================
@bp.post("/scales/create")
@login_required
def create_scale_action():
    _require_manager()

    ano = int(request.form.get("ano") or 0)
    mes = int(request.form.get("mes") or 0)
    sector_id = int(request.form.get("sector_id") or 0)

    if not ano or mes < 1 or mes > 12 or not sector_id:
        flash("Dados inválidos para criar escala.", "danger")
        return redirect(url_for("nursing_ui.year_view", ano=ano or date.today().year))

    # não duplica
    exists = NursingMonthlySchedule.query.filter_by(sector_id=sector_id, year=ano, month=mes).first()
    if exists:
        flash("Esse setor já tem escala nesse mês.", "warning")
        return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))

    sched = NursingMonthlySchedule(
        sector_id=sector_id,
        year=ano,
        month=mes,
        status="draft",
        created_by_id=getattr(current_user, "id", None),
    )
    db.session.add(sched)
    db.session.commit()

    flash("Escala criada! Clique no card para editar.", "success")
    return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))


# =========================
# NÍVEL 3: Editor (tabela mensal)
# =========================

@bp.get("/scales/<int:ano>/<int:mes>/<int:sector_id>")
@login_required
def editor_view(ano: int, mes: int, sector_id: int):
    _require_manager()

    sched = NursingMonthlySchedule.query.filter_by(sector_id=sector_id, year=ano, month=mes).first()
    if not sched:
        flash("Escala não encontrada. Crie o card primeiro.", "warning")
        return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))

    sector = Sector.query.get(sector_id)

    days = _build_days(ano, mes)
    days_in_month = calendar.monthrange(ano, mes)[1]   # ✅ ADICIONA ISSO

    prev_ano, prev_mes, next_ano, next_mes = _month_nav(ano, mes)

    members = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, active=True).all()

    q = (request.args.get("q") or "").strip().lower()
    professionals = []
    for m in sorted(members, key=lambda x: (x.role, x.position)):
        u = User.query.get(m.user_id)
        if not u:
            continue

        name = (u.nome or "").strip()
        matricula = getattr(u, "matricula", "") or ""
        hay = f"{name} {matricula} {m.role}".lower()
        if q and q not in hay:
            continue

        professionals.append({
            "id": u.id,
            "name": name,
            "role": m.role,
            "position": m.position,
            "matricula": matricula,
            "turno": getattr(u, "turno", None),
        })

    cell_map: Dict[int, Dict[int, str]] = {}
    cells = NursingMonthlyCell.query.filter_by(schedule_id=sched.id).all()
    for c in cells:
        if not c.planned_user_id:
            continue
        cell_map.setdefault(c.planned_user_id, {})[c.day] = c.shift

    return render_template(
        "nursing/scale_editor.html",
        title=f"Escala • {month_name(mes)} {ano}",
        unidade_nome=getattr(current_user, "unidade_nome", None),
        ano=ano,
        mes=mes,
        prev_ano=prev_ano,
        prev_mes=prev_mes,
        next_ano=next_ano,
        next_mes=next_mes,
        active_sector_id=sector_id,
        active_sector=sector,
        sectors=Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all(),
        days=days,
        days_in_month=days_in_month,        # ✅ ADICIONA ISSO
        professionals=professionals,
        cell_map=cell_map,
        q=q,
        schedule_id=sched.id,
        status=sched.status,
    )


@bp.route("/daily")
@login_required
def daily():
    """Página da escala diária"""
    # Lógica para a escala diária, por exemplo, para hoje
    today = date.today()
    # Talvez você queira redirecionar para uma página específica ou renderizar um template
    return render_template("nursing/daily.html", current_date=today)

# Se quiser manter o endpoint daily_page por enquanto, pode adicionar um alias:
@bp.route("/daily-page")
@login_required
def daily_page():
    """Alias para a página diária"""
    return redirect(url_for('nursing_ui.daily'))

