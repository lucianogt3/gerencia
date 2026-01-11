from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort, current_app
from datetime import datetime, date
from flask_login import login_required, current_user
import calendar
import json

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
    # deixa disponível no Jinja: {{ month_name(mes) }}
    return {"month_name": month_name}

def _require_manager():
    if not hasattr(current_user, 'role') or current_user.role not in ("manager", "admin"):
        abort(403)

def _month_nav(ano: int, mes: int):
    prev_ano, prev_mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    next_ano, next_mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return prev_ano, prev_mes, next_ano, next_mes

def _build_days(ano: int, mes: int):
    last_day = calendar.monthrange(ano, mes)[1]
    out = []
    for d in range(1, last_day + 1):
        wd = date(ano, mes, d).weekday()  # 0 seg ... 6 dom
        out.append({"day": d, "is_weekend": wd >= 5})
    return out

# =========================
# Rotas de Páginas Básicas
# =========================
@bp.route("/")
@login_required
def index():
    """Página inicial da enfermagem"""
    return render_template("nursing/index.html")

@bp.route("/monthly")
@login_required
def monthly():
    """Página da escala mensal (legado/compatibilidade)"""
    # Dados de exemplo para teste
    colaboradores = []
    for i in range(1, 25):
        colaboradores.append({
            'nome': f'Colaborador {i}',
            'cargo': 'Enfermeiro(a)' if i % 2 == 0 else 'Técnico(a)',
            'setor': 'UTI' if i % 3 == 0 else 'Enfermaria' if i % 3 == 1 else 'PS',
            'status': 'Ativo' if i < 23 else 'Férias',
            'escala': ['D', 'N', 'F'] * 10  # Exemplo simples
        })
    
    return render_template("nursing/monthly.html", colaboradores=colaboradores)

@bp.route("/daily")
@login_required
def daily():
    """Página da escala diária"""
    return render_template("nursing/daily.html")

@bp.route("/reports")
@login_required
def reports():
    """Página de relatórios"""
    return render_template("nursing/reports.html")

@bp.route("/team")
@login_required
def team():
    """Página da equipe"""
    return render_template("nursing/team.html")

# =========================
# ALIASES para compatibilidade com templates antigos
# =========================
@bp.route("/daily-page")
@login_required
def daily_page():
    """Alias para /daily (para manter compatibilidade)"""
    return redirect(url_for("nursing_ui.daily"))

@bp.route("/monthly-page")
@login_required
def monthly_page():
    """Alias para /monthly (para manter compatibilidade)"""
    return redirect(url_for("nursing_ui.monthly"))

# =========================
# NÍVEL 1: Ano (cards de meses)
# =========================
@bp.route("/scales")
@login_required
def year_view():
    """Visualização anual das escalas"""
    _require_manager()

    ano = int(request.args.get("ano") or date.today().year)

    months_list = []
    for m in range(1, 13):
        # Contar escalas existentes para este mês
        # Nota: Você precisará importar seus modelos
        count = 0  # Substitua por: NursingMonthlySchedule.query.filter_by(year=ano, month=m).count()
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
@bp.route("/scales/<int:ano>/<int:mes>")
@login_required
def month_details(ano: int, mes: int):
    """Detalhes das escalas do mês"""
    _require_manager()

    # escalas já criadas no mês
    schedules = []  # Substitua por: NursingMonthlySchedule.query.filter_by(year=ano, month=mes).all()
    
    existing_scales = []
    used_sector_ids = set()

    for s in schedules:
        used_sector_ids.add(s.sector_id)
        sector_name = f"Setor {s.sector_id}"  # Substitua por busca no banco
        prof_count = 0  # Substitua por contagem real
        
        existing_scales.append({
            "id": s.id,
            "sector_id": s.sector_id,
            "sector_name": sector_name,
            "prof_count": prof_count,
            "is_published": (s.status == "published"),
        })

    # setores disponíveis (ainda sem escala no mês)
    available_sectors = []  # Substitua por busca no banco

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
@bp.route("/scales/create", methods=['POST'])
@login_required
def create_scale_action():
    """Cria uma nova escala"""
    _require_manager()

    ano = int(request.form.get("ano") or 0)
    mes = int(request.form.get("mes") or 0)
    sector_id = int(request.form.get("sector_id") or 0)

    if not ano or mes < 1 or mes > 12 or not sector_id:
        flash("Dados inválidos para criar escala.", "danger")
        return redirect(url_for("nursing_ui.year_view", ano=ano or date.today().year))

    # Verificar se já existe
    exists = False  # Substitua por verificação no banco
    if exists:
        flash("Esse setor já tem escala nesse mês.", "warning")
        return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))

    # Criar nova escala
    flash("Escala criada! Clique no card para editar.", "success")
    return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))

# =========================
# NÍVEL 3: Editor (tabela mensal)
# =========================
@bp.route("/scales/<int:ano>/<int:mes>/<int:sector_id>")
@login_required
def editor_view(ano: int, mes: int, sector_id: int):
    """Editor da escala mensal"""
    _require_manager()

    # Buscar escala existente
    schedule = None  # Substitua por busca no banco
    if not schedule:
        flash("Escala não encontrada. Crie o card primeiro.", "warning")
        return redirect(url_for("nursing_ui.month_details", ano=ano, mes=mes))

    sector_name = f"Setor {sector_id}"  # Substitua por busca no banco
    days = _build_days(ano, mes)
    prev_ano, prev_mes, next_ano, next_mes = _month_nav(ano, mes)

    # Profissionais
    professionals = []
    # Substitua por busca no banco de membros da escala
    
    # Células da escala (user_id/dia -> código)
    cell_map = {}
    # Substitua por busca no banco de células

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
        active_sector={"name": sector_name},
        sectors=[],  # Substitua por busca de setores
        days=days,
        professionals=professionals,
        cell_map=cell_map,
        q=request.args.get("q", ""),
        schedule_id=1,  # Substitua pelo ID real
        status="draft",  # Substitua pelo status real
    )

# =========================
# APIs
# =========================
@bp.route("/api/escala", methods=['GET', 'POST'])
@login_required
def api_escala():
    """API para manipulação da escala"""
    if request.method == 'POST':
        data = request.json
        # Lógica para salvar a escala
        return jsonify({'success': True, 'message': 'Escala salva com sucesso'})
    
    # GET: Retornar dados da escala
    return jsonify({'escala': [], 'mes': datetime.now().strftime('%Y-%m')})

@bp.route("/api/colaboradores")
@login_required
def api_colaboradores():
    """API para listar colaboradores"""
    colaboradores = [
        {'id': i, 'nome': f'Colaborador {i}', 'cargo': 'Enfermeiro', 'setor': 'UTI', 'status': 'Ativo'}
        for i in range(1, 26)
    ]
    return jsonify(colaboradores)

# =========================
# APIs para o editor de escalas
# =========================
@bp.route("/api/scales/<int:schedule_id>/cells", methods=['POST'])
@login_required
def save_cell(schedule_id):
    """Salva uma célula da escala"""
    _require_manager()
    
    data = request.json
    user_id = data.get('user_id')
    day = data.get('day')
    shift = data.get('shift')
    
    if not all([user_id, day, shift]):
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
    
    # Lógica para salvar no banco
    # Exemplo: NursingMonthlyCell.save_cell(schedule_id, user_id, day, shift)
    
    return jsonify({'success': True})

@bp.route("/api/scales/<int:schedule_id>/publish", methods=['POST'])
@login_required
def publish_scale(schedule_id):
    """Publica uma escala"""
    _require_manager()
    
    # Lógica para publicar a escala
    # Exemplo: NursingMonthlySchedule.publish(schedule_id)
    
    return jsonify({'success': True, 'message': 'Escala publicada com sucesso'})

@bp.route("/api/scales/<int:schedule_id>/members", methods=['GET', 'POST'])
@login_required
def manage_members(schedule_id):
    """Gerencia membros da escala"""
    _require_manager()
    
    if request.method == 'GET':
        # Retorna membros da escala
        members = []  # Substitua por busca no banco
        return jsonify({'members': members})
    
    elif request.method == 'POST':
        # Adiciona membro à escala
        data = request.json
        user_id = data.get('user_id')
        role = data.get('role')
        
        if not user_id or not role:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        # Lógica para adicionar membro
        return jsonify({'success': True, 'message': 'Membro adicionado'})

# =========================
# Rotas de Exportação/Importação
# =========================
@bp.route("/export/<int:ano>/<int:mes>")
@login_required
def export_month(ano: int, mes: int):
    """Exporta escalas do mês"""
    _require_manager()
    
    # Lógica de exportação
    # Retorna JSON, CSV ou PDF
    
    return jsonify({'export': 'data'})

@bp.route("/import", methods=['POST'])
@login_required
def import_scales():
    """Importa escalas"""
    _require_manager()
    
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(request.referrer or url_for('nursing_ui.year_view'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(request.referrer or url_for('nursing_ui.year_view'))
    
    # Lógica de importação
    flash('Escalas importadas com sucesso', 'success')
    return redirect(url_for('nursing_ui.year_view'))

# =========================
# Rotas de Configuração
# =========================
@bp.route("/settings/turnos")
@login_required
def turno_settings():
    """Configuração de turnos"""
    _require_manager()
    return render_template("nursing/settings/turnos.html")

@bp.route("/settings/escala-types")
@login_required
def escala_types_settings():
    """Configuração de tipos de escala"""
    _require_manager()
    return render_template("nursing/settings/escala_types.html")

# =========================
# Rotas de Visualização Pública (somente leitura)
# =========================
@bp.route("/view/<int:ano>/<int:mes>")
@login_required
def public_view(ano: int, mes: int):
    """Visualização pública da escala (somente leitura)"""
    # Esta rota não requer manager, apenas login
    return render_template("nursing/public_view.html", 
                          ano=ano, 
                          mes=mes,
                          month_label=month_name(mes))