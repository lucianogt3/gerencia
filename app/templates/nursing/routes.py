from __future__ import annotations

import calendar
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user

from app.extensions import db, csrf

# Models
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import (
    NursingMonthlySchedule,
    NursingMonthlyMember,
    NursingMonthlyCell,
    NursingDailyOverride,
)

bp = Blueprint("nursing_ui", __name__, url_prefix="/nursing")

# =========================
# CSRF safe decorator
# =========================
def exempt_csrf(f):
    if csrf and hasattr(csrf, "exempt"):
        return csrf.exempt(f)
    return f

# =========================
# Helpers
# =========================
MONTHS_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def month_name(m: int) -> str:
    return MONTHS_PT.get(int(m), "") if str(m).isdigit() else ""

@bp.app_context_processor
def inject_globals():
    return {
        "month_name": month_name,
        "current_year": date.today().year,
        "timedelta": timedelta,
    }

def _require_manager():
    if getattr(current_user, "role", "") not in ("manager", "admin"):
        abort(403)

def _build_days(ano: int, mes: int) -> List[Dict[str, Any]]:
    """Constrói lista de dias do mês com flag de final de semana"""
    last_day = calendar.monthrange(ano, mes)[1]
    return [
        {"day": d, "is_weekend": date(ano, mes, d).weekday() >= 5}
        for d in range(1, last_day + 1)
    ]

def _month_nav(ano: int, mes: int) -> Tuple[int, int, int, int]:
    """Calcula navegação entre meses"""
    dt = date(ano, mes, 1)
    prev = dt - timedelta(days=1)
    next_m = (dt + timedelta(days=32)).replace(day=1)
    return prev.year, prev.month, next_m.year, next_m.month

# =========================
# NORMALIZAÇÃO E RANKING
# =========================
def normalize_shift(raw_turno: Optional[str]) -> str:
    """Normaliza turno para 'D' (diurno) ou 'N' (noturno)"""
    if not raw_turno:
        return "D"
    
    t = raw_turno.strip().upper()
    
    # Verifica por padrões de noturno primeiro
    if (t.startswith("19") or t.startswith("NOI") or 
        "NOTURNO" in t or "NOITE" in t or t == "N"):
        return "N"
    
    # Padrões diurnos
    if (t.startswith("07") or t.startswith("MANHÃ") or 
        "DIURNO" in t or "MANHA" in t or "TARDE" in t or t == "D"):
        return "D"
    
    return "D"  # default

def _norm_txt(s: str) -> str:
    """Normaliza texto: remove acentos e converte para minúsculas"""
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def get_user_role_rank(user: User) -> int:
    """
    Retorna ranking hierárquico do usuário:
    1 - Enfermeiro(a)
    2 - Técnico(a) de Enfermagem
    3 - Condutor
    4 - Outros cargos
    """
    # Coleta informações de cargo de múltiplos campos
    cargo_fields = []
    
    # Verifica campos possíveis
    if hasattr(user, 'role') and user.role:
        cargo_fields.append(user.role)
    
    if hasattr(user, 'role_label') and user.role_label:
        cargo_fields.append(user.role_label)
    
    if hasattr(user, 'cargo') and user.cargo:
        cargo_fields.append(user.cargo)
    
    if hasattr(user, 'position') and user.position:
        cargo_fields.append(user.position)
    
    # Junta todos os campos em uma string normalizada
    cargo_text = " ".join(filter(None, cargo_fields))
    norm_cargo = _norm_txt(cargo_text)
    
    # Determina hierarquia
    if any(kw in norm_cargo for kw in ["enfermeiro", "enfermeira", "enf"]):
        return 1
    elif any(kw in norm_cargo for kw in ["tecnico", "técnico", "tecnica", "técnica", "tec"]):
        return 2
    elif "condutor" in norm_cargo:
        return 3
    else:
        return 4

# =========================
# AUTO-FILL MENSAL
# =========================
def _auto_fill_user_month(schedule_id: int, user_id: int, year: int, month: int, pattern: str = "auto") -> None:
    """Preenche automaticamente dias de trabalho para um usuário"""
    user = User.query.get(user_id)
    if not user:
        return
    
    shift_code = normalize_shift(getattr(user, "turno", None))
    _, num_days = calendar.monthrange(year, month)
    
    if pattern == "auto":
        pattern = "even" if int(user_id) % 2 == 0 else "odd"
    
    # Limpa células existentes primeiro
    NursingMonthlyCell.query.filter_by(
        schedule_id=schedule_id,
        planned_user_id=user_id
    ).delete()
    
    # Preenche novos dias baseado no padrão
    for day in range(1, num_days + 1):
        should_work = False
        if pattern == "odd":
            should_work = (day % 2 != 0)
        elif pattern == "even":
            should_work = (day % 2 == 0)
        elif pattern == "all":
            should_work = True
        
        if should_work:
            cell = NursingMonthlyCell(
                schedule_id=schedule_id,
                planned_user_id=user_id,
                day=day,
                shift=shift_code,
                created_by_id=current_user.id
            )
            db.session.add(cell)
    
    db.session.commit()

# ==========================================
# PAINEL GERENCIAL (INDICATORS)
# ==========================================
@bp.get("/indicators")
@login_required
def manager_dashboard():
    _require_manager()
    
    try:
        ano = int(request.args.get("ano", date.today().year))
        mes = int(request.args.get("mes", date.today().month))
    except (ValueError, TypeError):
        ano, mes = date.today().year, date.today().month
    
    start_date = date(ano, mes, 1)
    last_day = calendar.monthrange(ano, mes)[1]
    end_date = date(ano, mes, last_day)
    
    # Busca todas as ocorrências do mês
    all_data = db.session.query(
        NursingDailyOverride, User, Sector
    ).outerjoin(
        User, NursingDailyOverride.user_id == User.id
    ).outerjoin(
        Sector, User.sector_id == Sector.id
    ).filter(
        NursingDailyOverride.date.between(start_date, end_date)
    ).order_by(
        NursingDailyOverride.date.desc()
    ).all()
    
    # Processa as ocorrências
    unified_list = []
    c_coop = c_absent = c_swaps = c_present = 0
    
    for override, user, sector in all_data:
        row_type = "OUTROS"
        
        if override.is_coop:
            row_type = "COOP"
            c_coop += 1
        elif override.code == "OK":
            row_type = "PRESENTE"
            c_present += 1
        elif override.code in ("FT", "AT", "F"):
            row_type = "FALTA"
            c_absent += 1
        elif override.code == "EX":
            if override.related_date:
                row_type = "BANCO"
                c_swaps += 1
            else:
                row_type = "EXTRA"
        
        unified_list.append({
            "override": override,
            "user": user,
            "sector": sector,
            "type": row_type
        })
    
    prev_ano, prev_mes, next_ano, next_mes = _month_nav(ano, mes)
    
    return render_template(
        "nursing/manager_dashboard.html",
        occurrences=unified_list,
        count_present=c_present,
        count_coop=c_coop,
        count_absent=c_absent,
        count_swaps=c_swaps,
        ano=ano,
        mes=mes,
        month_label=month_name(mes),
        prev_ano=prev_ano,
        prev_mes=prev_mes,
        next_ano=next_ano,
        next_mes=next_mes
    )

# ==========================================
# ROTAS DE ESCALA MENSAL
# ==========================================
@bp.get("/scales")
@login_required
def year_view():
    _require_manager()
    
    try:
        ano = int(request.args.get("ano", date.today().year))
    except (ValueError, TypeError):
        ano = date.today().year
    
    months_list = []
    for m in range(1, 13):
        active_scales = NursingMonthlySchedule.query.filter_by(
            year=ano, month=m
        ).count()
        
        months_list.append({
            "num": m,
            "name": month_name(m),
            "active_scales_count": active_scales
        })
    
    return render_template("nursing/years_view.html", ano=ano, months_list=months_list)

@bp.get("/scales/<int:ano>/<int:mes>")
@login_required
def month_details(ano: int, mes: int):
    _require_manager()
    
    schedules = NursingMonthlySchedule.query.filter_by(
        year=ano, month=mes
    ).all()
    
    existing_scales = []
    created_ids = [s.sector_id for s in schedules]
    
    for sched in schedules:
        sector = Sector.query.get(sched.sector_id)
        member_count = NursingMonthlyMember.query.filter_by(
            schedule_id=sched.id, active=True
        ).count()
        
        existing_scales.append({
            "id": sched.id,
            "sector_name": sector.name if sector else f"Setor {sched.sector_id}",
            "prof_count": member_count,
            "status": sched.status,
            "sector_id": sched.sector_id
        })
    
    available = Sector.query.filter(
        Sector.active == True,
        ~Sector.id.in_(created_ids)
    ).order_by(Sector.name).all()
    
    return render_template(
        "nursing/month_details.html",
        ano=ano,
        mes=mes,
        existing_scales=existing_scales,
        available_sectors=available,
        month_label=month_name(mes)
    )

@bp.post("/scales/create")
@login_required
def create_scale_action():
    _require_manager()
    
    try:
        ano = int(request.form.get("ano", 0))
        mes = int(request.form.get("mes", 0))
        sector_id = int(request.form.get("sector_id", 0))
    except (ValueError, TypeError):
        return redirect(url_for("nursing_ui.year_view"))
    
    if not sector_id:
        return redirect(url_for("nursing_ui.year_view"))
    
    # Verifica se já existe escala para este setor/mês/ano
    existing = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id, year=ano, month=mes
    ).first()
    
    if not existing:
        new_schedule = NursingMonthlySchedule(
            sector_id=sector_id,
            year=ano,
            month=mes,
            status="draft",
            created_by_id=current_user.id
        )
        db.session.add(new_schedule)
        db.session.commit()
    
    return redirect(url_for(
        "nursing_ui.editor_view",
        ano=ano,
        mes=mes,
        sector_id=sector_id
    ))

# ==========================================
# EDITOR VIEW (CORRIGIDO: SEPARAÇÃO DIURNO/NOTURNO)
# ==========================================
@bp.get("/scales/<int:ano>/<int:mes>/<int:sector_id>")
@login_required
def editor_view(ano: int, mes: int, sector_id: int):
    _require_manager()
    
    # Busca ou cria escala
    schedule = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id, year=ano, month=mes
    ).first()
    
    if not schedule:
        schedule = NursingMonthlySchedule(
            sector_id=sector_id,
            year=ano,
            month=mes,
            status="draft",
            created_by_id=current_user.id
        )
        db.session.add(schedule)
        db.session.commit()
    
    # Informações básicas
    sector = Sector.query.get(sector_id)
    days = _build_days(ano, mes)
    
    # Membros da escala
    members = NursingMonthlyMember.query.filter_by(
        schedule_id=schedule.id, active=True
    ).all()
    
    user_ids = [m.user_id for m in members]
    
    # Células (dias trabalhados)
    cells = NursingMonthlyCell.query.filter_by(
        schedule_id=schedule.id
    ).all()
    
    # Mapeia células por usuário e dia
    cell_map = {}
    for cell in cells:
        user_id = cell.planned_user_id or cell.user_id
        if user_id:
            if user_id not in cell_map:
                cell_map[user_id] = {}
            cell_map[user_id][int(cell.day)] = (cell.shift or "").strip().upper()
    
    # Usuários da escala
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    
    # Categoriza usuários - AGORA SEPARADOS POR DIURNO E NOTURNO
    categories = {
        # GRUPOS DIURNOS - APENAS USUÁRIOS COM TURNO DIURNO
        "DIURNO - PAR": [],
        "DIURNO - ÍMPAR": [],
        
        # GRUPOS NOTURNOS - APENAS USUÁRIOS COM TURNO NOTURNO
        "NOTURNO - PAR": [],
        "NOTURNO - ÍMPAR": [],
        
        # OUTROS GRUPOS (NÃO TEM TURNO DEFINIDO)
        "NIRAS E QUALIDADE": [],
        "COORDENAÇÃO": [],
        "AFASTADOS/OUTROS": []
    }
    
    for user in users:
        # Informações básicas
        user_cells = cell_map.get(user.id, {})
        user_shift = normalize_shift(getattr(user, "turno", None))
        
        # Determina paridade (baseado nos dias trabalhados ou ID)
        worked_days = [day for day, shift in user_cells.items() if shift and shift not in ("", "FO")]
        if worked_days:
            has_even_day = any(day % 2 == 0 for day in worked_days)
            parity = "PAR" if has_even_day else "ÍMPAR"
        else:
            parity = "PAR" if (user.id % 2 == 0) else "ÍMPAR"
        
        # Determina categoria baseado no cargo/turno
        user_role = (getattr(user, "role", "") or "").lower()
        user_role_label = (getattr(user, "role_label", "") or "").lower()
        
        # Primeiro verifica se é coordenador
        if any(kw in user_role or kw in user_role_label 
               for kw in ["coordenador", "coordenadora", "coord"]):
            category = "COORDENAÇÃO"
        
        # Verifica se é NIRAS/Qualidade
        elif any(kw in user_role or kw in user_role_label 
                 for kw in ["niras", "qualidade", "cq", "qualid"]):
            category = "NIRAS E QUALIDADE"
        
        # Verifica se está afastado
        elif getattr(user, "status", "active") != "active":
            category = "AFASTADOS/OUTROS"
        
        # Se for plantonista, classifica por turno
        else:
            if user_shift == "D":  # DIURNO
                category = f"DIURNO - {parity}"
            elif user_shift == "N":  # NOTURNO
                category = f"NOTURNO - {parity}"
            else:
                # Se não tem turno definido, vai para outros
                category = "AFASTADOS/OUTROS"
        
        # Determina horário para exibição
        if user_shift == "D":
            horario = "07:00 às 19:00"
        elif user_shift == "N":
            horario = "19:00 às 07:00"
        else:
            horario = getattr(user, "turno", "Não definido")
        
        # Ranking hierárquico
        role_rank = get_user_role_rank(user)
        
        # Determina cargo para exibição
        cargo_display = getattr(user, "role_label", None) or user.role or ""
        
        # Determina cargo para filtro
        cargo_lower = cargo_display.lower()
        if any(kw in cargo_lower for kw in ["enfermeiro", "enfermeira"]):
            cargo_filter = "Enfermeiro"
        elif any(kw in cargo_lower for kw in ["tecnico", "técnico", "tecnica", "técnica", "tec"]):
            cargo_filter = "Tecnico"
        else:
            cargo_filter = "Outros"
        
        # Determina turno para filtro
        turno_filter = "DIURNO" if user_shift == "D" else "NOTURNO"
        
        # Adiciona usuário à categoria
        categories[category].append({
            "user_id": user.id,
            "name": user.nome or f"Usuário {user.id}",
            "matricula": user.matricula or "",
            "cells": user_cells,
            "cargo_display": cargo_display,        # Para exibição na coluna Cargo
            "cargo_filter": cargo_filter,          # Para filtro de cargo
            "horario": horario,
            "role_rank": role_rank,
            "parity": parity,
            "shift": user_shift,
            "turno_filter": turno_filter,          # Para filtro de turno
            "cargo_raw": user.role or ""
        })
    
    # Ordena usuários dentro de cada categoria
    for category in categories:
        if category.startswith("DIURNO") or category.startswith("NOTURNO"):
            # Para grupos de plantão: ordena por hierarquia e depois nome
            categories[category].sort(key=lambda x: (
                x["role_rank"],      # 1. Enfermeiros primeiro (rank 1)
                x["name"].lower()    # 2. Ordem alfabética
            ))
        else:
            # Para outros grupos: ordena apenas por nome
            categories[category].sort(key=lambda x: x["name"].lower())
    
    # Prepara linhas para o template na ordem especificada
    order = [
        "DIURNO - PAR",
        "DIURNO - ÍMPAR", 
        "NOTURNO - PAR",
        "NOTURNO - ÍMPAR",
        "NIRAS E QUALIDADE",
        "COORDENAÇÃO",
        "AFASTADOS/OUTROS"
    ]
    
    rows = []
    for category in order:
        if categories[category]:
            # Define tipo do grupo para CSS
            if category.startswith("DIURNO"):
                group_type = "day"
            elif category.startswith("NOTURNO"):
                group_type = "night"
            else:
                group_type = "neutral"
            
            rows.append({
                "title": category,
                "group_type": group_type,
                "members": categories[category]
            })
    
    # Navegação entre meses
    prev_ano, prev_mes, next_ano, next_mes = _month_nav(ano, mes)
    
    return render_template(
        "nursing/scale_editor.html",
        ano=ano,
        mes=mes,
        days=days,
        prev_ano=prev_ano,
        prev_mes=prev_mes,
        next_ano=next_ano,
        next_mes=next_mes,
        active_sector=sector,
        schedule_id=schedule.id,
        status=schedule.status,
        rows=rows,
        month_label=month_name(mes)  # Adicionei isso para o template
    )

# =========================
# APIs JSON
# =========================
@bp.get("/api/users/search")
@login_required
def api_search_users():
    q = (request.args.get("q") or "").strip()
    if not q or len(q) < 2:
        return jsonify({"items": []})
    
    users = User.query.filter(
        (User.nome.ilike(f"%{q}%")) | (User.matricula.ilike(f"%{q}%")),
        User.status == "active"
    ).limit(20).all()
    
    items = []
    for user in users:
        items.append({
            "id": user.id,
            "name": user.nome or "",
            "matricula": user.matricula or "",
            "role_label": getattr(user, "role_label", user.role) or "",
            "turno": user.turno or ""
        })
    
    return jsonify({"items": items})

@bp.post("/api/monthly/<int:schedule_id>/import_sector")
@exempt_csrf
@login_required
def api_import_sector(schedule_id: int):
    _require_manager()
    
    schedule = NursingMonthlySchedule.query.get_or_404(schedule_id)
    
    data = request.get_json(silent=True) or {}
    auto_fill = data.get("auto_fill", False)
    
    # Busca todos os usuários ativos do setor
    users = User.query.filter_by(
        sector_id=schedule.sector_id,
        status="active"
    ).all()
    
    imported = 0
    for user in users:
        # Verifica se já é membro
        existing = NursingMonthlyMember.query.filter_by(
            schedule_id=schedule.id,
            user_id=user.id
        ).first()
        
        if not existing:
            member = NursingMonthlyMember(
                schedule_id=schedule.id,
                user_id=user.id,
                active=True,
                added_by_id=current_user.id
            )
            db.session.add(member)
            imported += 1
        
        # Preenchimento automático se solicitado
        if auto_fill:
            _auto_fill_user_month(
                schedule.id,
                user.id,
                schedule.year,
                schedule.month,
                pattern="auto"
            )
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "imported": imported,
        "message": f"{imported} usuários importados"
    })

@bp.post("/api/monthly/<int:schedule_id>/cell")
@exempt_csrf
@login_required
def api_update_cell(schedule_id: int):
    _require_manager()
    
    data = request.get_json(silent=True) or {}
    
    try:
        user_id = int(data.get("user_id", 0))
        day = int(data.get("day", 0))
        shift = (data.get("shift") or "").strip().upper()
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Dados inválidos"}), 400
    
    if not user_id or not day:
        return jsonify({"success": False, "error": "Usuário ou dia inválido"}), 400
    
    # Valida turno
    if shift not in ("D", "N", "FO", ""):
        shift = "D"  # default
    
    # Busca ou cria célula
    cell = NursingMonthlyCell.query.filter_by(
        schedule_id=schedule_id,
        planned_user_id=user_id,
        day=day
    ).first()
    
    if cell:
        cell.shift = shift
    else:
        cell = NursingMonthlyCell(
            schedule_id=schedule_id,
            planned_user_id=user_id,
            day=day,
            shift=shift
        )
        db.session.add(cell)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Célula atualizada"
    })

@bp.post("/api/monthly/<int:schedule_id>/add_member")
@exempt_csrf
@login_required
def api_add_member(schedule_id: int):
    """Adiciona um membro individual à escala"""
    _require_manager()
    
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"success": False, "error": "ID do usuário necessário"}), 400
    
    # Verifica se o usuário existe
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "Usuário não encontrado"}), 404
    
    # Verifica se já é membro da escala
    existing = NursingMonthlyMember.query.filter_by(
        schedule_id=schedule_id,
        user_id=user_id
    ).first()
    
    if existing:
        return jsonify({"success": False, "error": "Usuário já está na escala"}), 400
    
    # Adiciona novo membro
    new_member = NursingMonthlyMember(
        schedule_id=schedule_id,
        user_id=user_id,
        active=True,
        added_by_id=current_user.id
    )
    
    db.session.add(new_member)
    db.session.commit()
    
    # Busca a escala para obter ano e mês
    schedule = NursingMonthlySchedule.query.get(schedule_id)
    
    # Faz auto-preenchimento para o novo membro
    if schedule:
        _auto_fill_user_month(
            schedule_id,
            user_id,
            schedule.year,
            schedule.month,
            pattern="auto"
        )
    
    return jsonify({
        "success": True,
        "message": f"Colaborador {user.nome} adicionado com sucesso"
    })

@bp.post("/api/monthly/<int:schedule_id>/auto_fill")
@exempt_csrf
@login_required
def api_auto_fill_user(schedule_id: int):
    """Faz auto-preenchimento para um usuário específico"""
    _require_manager()
    
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    pattern = data.get("pattern", "auto")
    
    if not user_id:
        return jsonify({"success": False, "error": "ID do usuário necessário"}), 400
    
    # Verifica se o usuário é membro da escala
    member = NursingMonthlyMember.query.filter_by(
        schedule_id=schedule_id,
        user_id=user_id,
        active=True
    ).first()
    
    if not member:
        return jsonify({"success": False, "error": "Usuário não está na escala"}), 404
    
    # Busca a escala
    schedule = NursingMonthlySchedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"success": False, "error": "Escala não encontrada"}), 404
    
    # Faz auto-preenchimento
    _auto_fill_user_month(
        schedule_id,
        user_id,
        schedule.year,
        schedule.month,
        pattern=pattern
    )
    
    return jsonify({
        "success": True,
        "message": "Auto-preenchimento realizado"
    })

@bp.post("/api/monthly/<int:schedule_id>/auto_fill_all")
@exempt_csrf
@login_required
def api_auto_fill_all(schedule_id: int):
    """Faz auto-preenchimento para todos os membros da escala"""
    _require_manager()
    
    # Busca a escala
    schedule = NursingMonthlySchedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"success": False, "error": "Escala não encontrada"}), 404
    
    # Busca todos os membros ativos
    members = NursingMonthlyMember.query.filter_by(
        schedule_id=schedule_id,
        active=True
    ).all()
    
    count = 0
    for member in members:
        _auto_fill_user_month(
            schedule_id,
            member.user_id,
            schedule.year,
            schedule.month,
            pattern="auto"
        )
        count += 1
    
    return jsonify({
        "success": True,
        "message": f"Auto-preenchimento realizado para {count} colaboradores"
    })

# =========================
# ESCALA DIÁRIA
# =========================
usuários
@login_required
def daily():
    # 1. Captura de Filtros e Definição de Data
    date_str = request.args.get("date")
    selected_sector = request.args.get("sector_id")
    selected_shift = request.args.get("shift")
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    except ValueError:
        current_date = date.today()

    # 2. Lógica de Turno Automático (se não selecionado manualmente)
    # Diurno: 07h-18h59 | Noturno: 19h-06h59
    now = datetime.now()
    if not selected_shift:
        if 7 <= now.hour < 19:
            selected_shift = "D"
        else:
            selected_shift = "N"
            # Se for madrugada (00h-06h), refere-se à escala iniciada no dia anterior
            if now.hour < 7 and not date_str:
                current_date = current_date - timedelta(days=1)

    # 3. Busca de Dados para Filtros
    is_manager = getattr(current_user, "role", "") in ("manager", "admin")
    if is_manager:
        sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()
    else:
        sid = getattr(current_user, "sector_id", None)
        sectors = Sector.query.filter_by(id=sid, active=True).all() if sid else []

    # 4. Construção da Lista de Colaboradores (Plano Mensal + Overrides)
    daily_list = []
    if selected_sector:
        sched = NursingMonthlySchedule.query.filter_by(
            sector_id=selected_sector, 
            year=current_date.year, 
            month=current_date.month
        ).first()

        if sched:
            # Busca quem está no plano mensal para este dia/turno
            cells = NursingMonthlyCell.query.filter_by(
                schedule_id=sched.id, day=current_date.day, shift=selected_shift
            ).all()

            for c in cells:
                user = User.query.get(c.planned_user_id or c.user_id)
                if user:
                    # Busca se já existe uma ação registrada (Falta, Presença, Troca)
                    override = NursingDailyOverride.query.filter_by(
                        user_id=user.id, date=current_date
                    ).first()
                    
                    status = "planned"
                    if override:
                        status = "confirmed" if override.code == "OK" else "absent" if override.code == "FT" else "swapped_out"

                    daily_list.append({
                        "user": user,
                        "sector": Sector.query.get(selected_sector),
                        "shift": c.shift,
                        "status": status,
                        "obs": getattr(override, "notes", "") if override else ""
                    })

    # 5. Lista Global de Usuários para os Modais (Extras/Trocas)
    all_users = User.query.filter_by(status='active').order_by(User.nome).all()

    return render_template(
        "nursing/daily.html",
        daily_list=daily_list,
        current_date=current_date,
        today_date=date.today(),
        sectors=sectors,
        selected_sector=selected_sector,
        selected_shift=selected_shift,
        all_users=all_users,
        is_manager=is_manager,
        timedelta=timedelta
    )

@bp.post("/daily/action")
@login_required
def daily_action():
    # Processa as ações dos botões do HTML (Confirmar, Falta, Extra)
    data = request.form
    user_id = data.get("user_id")
    action = data.get("action")
    dt_str = data.get("date")
    ref_date = datetime.strptime(dt_str, '%Y-%m-%d').date()

    # Mapeamento de Códigos
    # OK = Presente | FT = Falta | EX = Extra
    code = "OK" if action == "confirm" else "FT" if action == "absent" else "EX"

    existing = NursingDailyOverride.query.filter_by(user_id=user_id, date=ref_date).first()
    if existing:
        existing.code = code
    else:
        new_ov = NursingDailyOverride(
            user_id=user_id, 
            date=ref_date, 
            code=code, 
            created_by_id=current_user.id
        )
        db.session.add(new_ov)
    
    db.session.commit()
    flash("Ação registrada com sucesso!", "success")
    return redirect(url_for('nursing_ui.daily', date=dt_str, sector_id=data.get("sector_id")))

@bp.get("/daily-page")
@login_required
def daily_page():
    return redirect(url_for("nursing_ui.daily"))