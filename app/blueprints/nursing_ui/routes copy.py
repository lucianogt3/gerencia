from __future__ import annotations

import calendar
from typing import Any, Dict, List
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Sector, 
    User, 
    NursingMonthlySchedule, 
    NursingMonthlyMember, 
    NursingMonthlyCell, 
    NursingDailyOverride
)

# Tenta importar o CSRF
try:
    from app.extensions import csrf
except ImportError:
    csrf = None

def exempt_csrf(f):
    if csrf and hasattr(csrf, 'exempt'):
        return csrf.exempt(f)
    return f

bp = Blueprint("nursing_ui", __name__, url_prefix="/nursing")

# --- Helpers ---
MONTHS_PT = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

def month_name(m: int) -> str:
    return MONTHS_PT.get(int(m), "") if str(m).isdigit() else ""

@bp.app_context_processor
def inject_globals():
    return {"month_name": month_name, "current_year": date.today().year, "timedelta": timedelta}

def _require_manager():
    if getattr(current_user, "role", "") not in ("manager", "admin"): abort(403)

def _build_days(ano: int, mes: int) -> List[Dict[str, Any]]:
    last_day = calendar.monthrange(ano, mes)[1]
    out = []
    for d in range(1, last_day + 1):
        wd = date(ano, mes, d).weekday()
        out.append({"day": d, "is_weekend": wd >= 5})
    return out

def _month_nav(ano: int, mes: int):
    dt = date(ano, mes, 1)
    prev = dt - timedelta(days=1)
    next_m = (dt + timedelta(days=32)).replace(day=1)
    return prev.year, prev.month, next_m.year, next_m.month

# --- LÓGICA DE PREENCHIMENTO ---
def _auto_fill_user_month(schedule_id, user_id, year, month, pattern='odd'):
    user = User.query.get(user_id)
    if not user: return

    # Pega o turno do cadastro ou 'D' se vazio
    shift_code = user.turno.upper() if user.turno else 'D'
    
    _, num_days = calendar.monthrange(year, month)
    
    for day in range(1, num_days + 1):
        should_work = False
        
        # Padrão calendário: Ímpar (1,3,5) ou Par (2,4,6)
        if pattern == 'odd':
            should_work = (day % 2 != 0)
        elif pattern == 'even':
            should_work = (day % 2 == 0)
            
        if should_work:
            # Verifica duplicidade
            exists = NursingMonthlyCell.query.filter_by(schedule_id=schedule_id, planned_user_id=user_id, day=day).first()
            if not exists:
                db.session.add(NursingMonthlyCell(
                    schedule_id=schedule_id, 
                    planned_user_id=user_id, 
                    day=day, 
                    shift=shift_code
                ))

# ==========================================
# ROTAS DE PÁGINAS
# ==========================================

@bp.get("/scales")
@login_required
def year_view():
    _require_manager()
    ano = int(request.args.get("ano") or date.today().year)
    months_list = []
    for m in range(1, 13):
        count = NursingMonthlySchedule.query.filter_by(year=ano, month=m).count()
        months_list.append({"num": m, "name": month_name(m), "active_scales_count": count})
    return render_template("nursing/years_view.html", title=f"Escalas {ano}", ano=ano, months_list=months_list)

@bp.get("/scales/<int:ano>/<int:mes>")
@login_required
def month_details(ano: int, mes: int):
    return redirect(url_for('nursing_ui.year_view', ano=ano))

@bp.post("/scales/create")
@login_required
def create_scale_action():
    _require_manager()
    ano = int(request.form.get("ano") or 0)
    mes = int(request.form.get("mes") or 0)
    sector_id = int(request.form.get("sector_id") or 0)
    if not ano or not sector_id: return redirect(url_for("nursing_ui.year_view"))
    
    exists = NursingMonthlySchedule.query.filter_by(sector_id=sector_id, year=ano, month=mes).first()
    if not exists:
        sched = NursingMonthlySchedule(sector_id=sector_id, year=ano, month=mes, status="draft", created_by_id=current_user.id)
        db.session.add(sched)
        db.session.commit()
    return redirect(url_for("nursing_ui.editor_view", ano=ano, mes=mes, sector_id=sector_id))

# ---------------------------------------------------------------------
# EDITOR DE ESCALA (AGRUPAMENTO POR TURNO E PARIDADE)
# ---------------------------------------------------------------------
@bp.get("/scales/<int:ano>/<int:mes>/<int:sector_id>")
@login_required
def editor_view(ano: int, mes: int, sector_id: int):
    _require_manager()
    sched = NursingMonthlySchedule.query.filter_by(sector_id=sector_id, year=ano, month=mes).first()
    
    if not sched:
        sched = NursingMonthlySchedule(sector_id=sector_id, year=ano, month=mes, status="draft", created_by_id=getattr(current_user, "id", None))
        db.session.add(sched)
        db.session.commit()
    
    sector = Sector.query.get(sector_id)
    days = _build_days(ano, mes)
    
    members = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, active=True).all()
    member_ids = [m.user_id for m in members]
    
    cells = NursingMonthlyCell.query.filter_by(schedule_id=sched.id).all()
    cell_map = {}
    for c in cells:
        uid = getattr(c, "planned_user_id", getattr(c, "user_id", None))
        if uid:
            if uid not in cell_map: cell_map[uid] = {}
            cell_map[uid][c.day] = c.shift

    users = User.query.filter(User.id.in_(member_ids)).all()
    
    # Grupos exatos do Excel
    groups_data = {
        "PLANTÃO DIURNO PAR": [],
        "PLANTÃO DIURNO ÍMPAR": [],
        "PLANTÃO NOTURNO PAR": [],
        "PLANTÃO NOTURNO ÍMPAR": [],
        "AFASTADAS / OUTROS": []
    }

    for u in users:
        u_cells = cell_map.get(u.id, {})
        # Normaliza turno (Se vazio, assume D)
        t = (u.turno or "D").upper()
        
        # Verifica se trabalha em dias pares ou ímpares
        # Consideramos "Trabalhar" se tiver plantão D ou N no dia
        even_days = [d for d, s in u_cells.items() if s in ['D','N'] and d % 2 == 0]
        odd_days = [d for d, s in u_cells.items() if s in ['D','N'] and d % 2 != 0]
        
        count_even = len(even_days)
        count_odd = len(odd_days)
        
        # Lógica de Classificação
        category = "AFASTADAS / OUTROS"
        
        is_diurno = (t in ['D', 'M', 'T'])
        is_noturno = (t == 'N')
        
        if count_even > count_odd:
            # Predominantemente PAR
            if is_diurno: category = "PLANTÃO DIURNO PAR"
            elif is_noturno: category = "PLANTÃO NOTURNO PAR"
        elif count_odd > count_even:
            # Predominantemente ÍMPAR
            if is_diurno: category = "PLANTÃO DIURNO ÍMPAR"
            elif is_noturno: category = "PLANTÃO NOTURNO ÍMPAR"
        else:
            # Empate ou vazio -> Usa o cadastro se não tiver escala
            # Se tiver escala mista igual, joga em Par por padrão
            if count_even > 0:
                if is_diurno: category = "PLANTÃO DIURNO PAR"
                elif is_noturno: category = "PLANTÃO NOTURNO PAR"
            else:
                # Sem escala definida ainda -> Tenta adivinhar pelo cadastro? 
                # Melhor jogar em Outros para forçar importação correta, 
                # ou jogar em um padrão. Vamos jogar em Outros.
                category = "AFASTADAS / OUTROS"

        # Horário Display
        horario = "07:00 - 19:00" if is_diurno else "19:00 - 07:00"
        
        # Ordenação interna: Enfermeiro (1), Técnico (2), Condutor (3)
        role_map = {'nurse': 1, 'technician': 2, 'condutor': 3}
        role_sort = role_map.get(u.role, 4)

        groups_data[category].append({
            "name": u.nome,
            "user_id": u.id,
            "matricula": u.matricula,
            "role_label": getattr(u, "role_label", u.role),
            "cells": u_cells,
            "horario": horario,
            "role_sort": role_sort
        })

    # Converte para lista ordenada
    rows = []
    # Ordem fixa de exibição dos grupos
    group_order = [
        "PLANTÃO DIURNO PAR", 
        "PLANTÃO DIURNO ÍMPAR", 
        "PLANTÃO NOTURNO PAR", 
        "PLANTÃO NOTURNO ÍMPAR", 
        "AFASTADAS / OUTROS"
    ]
    
    for title in group_order:
        members = groups_data.get(title, [])
        if members:
            # Ordena por Cargo e depois por Nome
            members.sort(key=lambda x: (x['role_sort'], x['name']))
            rows.append({"title": title, "members": members})

    prev_ano, prev_mes, next_ano, next_mes = _month_nav(ano, mes)

    return render_template(
        "nursing/scale_editor.html", 
        title=f"Escala • {month_name(mes)} {ano}",
        ano=ano, mes=mes, days=days,
        prev_ano=prev_ano, prev_mes=prev_mes, next_ano=next_ano, next_mes=next_mes,
        active_sector=sector, active_sector_id=sector_id,
        schedule_id=sched.id, status=sched.status,
        rows=rows
    )

@bp.route("/monthly", methods=["GET"])
@login_required
def monthly_page():
    return redirect(url_for('nursing_ui.year_view'))

# ==========================================
# APIS JSON
# ==========================================

@bp.get("/api/users/search")
@login_required
def api_search_users():
    q = request.args.get("q", "").strip()
    if not q: return jsonify({"items": []})
    users = User.query.filter((User.nome.ilike(f"%{q}%")) | (User.matricula.ilike(f"%{q}%"))).filter_by(status='active').limit(10).all()
    return jsonify({"items": [{
        "id": u.id, "name": u.nome, "matricula": u.matricula, "role_label": getattr(u, "role_label", u.role), "turno": u.turno
    } for u in users]})

@bp.get("/api/monthly/<int:schedule_id>/preview_import")
@login_required
def api_preview_import(schedule_id):
    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    all_users = User.query.filter_by(sector_id=sched.sector_id, status='active').all()
    current_members = [m.user_id for m in NursingMonthlyMember.query.filter_by(schedule_id=sched.id).all()]
    
    missing = []
    for u in all_users:
        if u.id not in current_members:
            missing.append({
                "id": u.id, "name": u.nome, "role": getattr(u, "role_label", u.role), "turno": u.turno or "?"
            })
    # Ordena por nome
    missing.sort(key=lambda x: x['name'])
    return jsonify({"count": len(missing), "users": missing})

@bp.post("/api/monthly/<int:schedule_id>/import_all")
@exempt_csrf
@login_required
def api_import_all(schedule_id):
    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    data = request.get_json(silent=True) or {}
    
    pattern = data.get("pattern", "odd") 
    user_ids = data.get('user_ids', []) # Lista de IDs selecionados no checkbox
    
    count = 0
    if user_ids:
        for uid in user_ids:
            # Verifica se já está na escala
            exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=uid).first()
            if not exists:
                db.session.add(NursingMonthlyMember(schedule_id=sched.id, user_id=uid, active=True))
                # Aplica preenchimento
                _auto_fill_user_month(sched.id, uid, sched.year, sched.month, pattern=pattern)
                count += 1
        
        db.session.commit()
        
    return jsonify({"success": True, "imported": count})

@bp.post("/api/monthly/<int:schedule_id>/add_user_auto")
@exempt_csrf
@login_required
def api_add_user(schedule_id):
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    pattern = data.get("pattern", "odd")
    
    if not uid: return jsonify({"error": "ID invalido"}), 400
    
    exists = NursingMonthlyMember.query.filter_by(schedule_id=schedule_id, user_id=uid).first()
    if not exists:
        db.session.add(NursingMonthlyMember(schedule_id=schedule_id, user_id=uid, active=True))
        db.session.commit()
    
    sched = NursingMonthlySchedule.query.get(schedule_id)
    _auto_fill_user_month(schedule_id, uid, sched.year, sched.month, pattern=pattern)
    db.session.commit()
    return jsonify({"success": True})

@bp.post("/api/monthly/<int:schedule_id>/remove_member")
@exempt_csrf
@login_required
def api_remove_member(schedule_id):
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    if not uid: return jsonify({"error": "ID invalido"}), 400
    
    NursingMonthlyCell.query.filter_by(schedule_id=schedule_id, planned_user_id=uid).delete()
    NursingMonthlyMember.query.filter_by(schedule_id=schedule_id, user_id=uid).delete()
    db.session.commit()
    return jsonify({"success": True})

@bp.post("/api/monthly/<int:schedule_id>/cell")
@exempt_csrf
@login_required
def api_update_cell(schedule_id):
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    day = data.get("day")
    shift = data.get("shift", "").strip().upper()
    
    cell = NursingMonthlyCell.query.filter_by(schedule_id=schedule_id, planned_user_id=uid, day=day).first()
    if cell:
        cell.shift = shift
    else:
        db.session.add(NursingMonthlyCell(schedule_id=schedule_id, planned_user_id=uid, day=day, shift=shift))
    db.session.commit()
    return jsonify({"success": True})

# ==========================================
# ESCALA DIÁRIA
# ==========================================
@bp.route("/daily", methods=["GET", "POST"])
@login_required
def daily():
    # Código padrão da daily mantido para compatibilidade
    return render_template("nursing/daily.html", daily_list=[], current_date=date.today(), sectors=[])

@bp.get("/daily-page")
@login_required
def daily_page():
    return redirect(url_for("nursing_ui.daily"))