from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from app.extensions import db
from app.models.swap import ShiftSwap
from app.models.user import User
from app.models.nursing_schedule import NursingDailyOverride

bp = Blueprint("swaps", __name__, url_prefix="/swaps")

@bp.route("/", methods=["GET"])
@login_required
def index():
    # Se for Gerente/Admin, vê tudo. Se for colaborador, vê só as suas.
    query = ShiftSwap.query
    if current_user.role not in ['manager', 'admin']:
        query = query.filter(
            (ShiftSwap.requester_id == current_user.id) | 
            (ShiftSwap.substitute_id == current_user.id)
        )
    
    # Ordena por criação (mais recentes primeiro)
    swaps = query.order_by(ShiftSwap.created_at.desc()).all()

    # KPIs para o topo da página
    kpi = {
        'pending': sum(1 for s in swaps if s.status == 'pending'),
        'approved': sum(1 for s in swaps if s.status == 'approved'),
        'refused': sum(1 for s in swaps if s.status == 'refused')
    }

    # Lista de usuários para o select (exclui o próprio usuário logado)
    users = User.query.filter(User.id != current_user.id, User.status == 'active').order_by(User.nome).all()

    return render_template("swaps/index.html", swaps=swaps, users=users, kpi=kpi)

@bp.route("/create", methods=["POST"])
@login_required
def create():
    substitute_id = request.form.get("substitute_id")
    orig_date = request.form.get("original_date")
    orig_shift = request.form.get("original_shift")
    target_date = request.form.get("target_date")
    target_shift = request.form.get("target_shift")
    reason = request.form.get("reason")
    req_type = request.form.get("request_type")

    if not substitute_id or not orig_date:
        flash("Dados incompletos.", "error")
        return redirect(url_for('swaps.index'))

    swap = ShiftSwap(
        requester_id=current_user.id,
        substitute_id=substitute_id,
        original_date=datetime.strptime(orig_date, "%Y-%m-%d").date(),
        original_shift=orig_shift,
        target_date=datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else None,
        target_shift=target_shift,
        reason=reason,
        request_type=req_type,
        status="pending"
    )
    db.session.add(swap)
    db.session.commit()
    flash("Solicitação enviada com sucesso!", "success")
    return redirect(url_for('swaps.index'))

@bp.route("/action/<int:id>", methods=["POST"])
@login_required
def action(id):
    # Apenas gerentes podem aprovar/recusar
    if current_user.role not in ['manager', 'admin']: 
        return redirect(url_for('swaps.index'))

    swap = ShiftSwap.query.get_or_404(id)
    act = request.form.get("action")
    reason = request.form.get("refusal_reason")

    if act == "refuse":
        swap.status = "refused"
        swap.refusal_reason = reason
        flash("Troca recusada.", "warning")
    
    elif act == "approve":
        swap.status = "approved"
        
        # --- ATUALIZAÇÃO AUTOMÁTICA DA ESCALA DIÁRIA ---
        
        # 1. Dia Original: Solicitante SAI, Substituto ENTRA
        # Remove overrides anteriores para evitar duplicidade
        NursingDailyOverride.query.filter_by(date=swap.original_date, user_id=swap.requester_id).delete()
        NursingDailyOverride.query.filter_by(date=swap.original_date, user_id=swap.substitute_id).delete()

        # Solicitante sai (TR_OUT)
        db.session.add(NursingDailyOverride(
            date=swap.original_date, user_id=swap.requester_id, 
            code="TR_OUT", description=f"Substituído por: {swap.substitute.nome}"
        ))
        # Substituto entra (TR_IN)
        db.session.add(NursingDailyOverride(
            date=swap.original_date, user_id=swap.substitute_id, 
            code="TR_IN", description=f"Cobre: {swap.requester.nome}",
            shift=swap.original_shift # Assume o turno do original
        ))

        # 2. Dia da Devolução (Se existir): O Inverso acontece
        if swap.target_date:
            NursingDailyOverride.query.filter_by(date=swap.target_date, user_id=swap.substitute_id).delete()
            NursingDailyOverride.query.filter_by(date=swap.target_date, user_id=swap.requester_id).delete()

            # Substituto sai (pagando a troca)
            db.session.add(NursingDailyOverride(
                date=swap.target_date, user_id=swap.substitute_id,
                code="TR_OUT", description=f"Devolve p/: {swap.requester.nome}"
            ))
            # Solicitante entra (recebendo a troca)
            db.session.add(NursingDailyOverride(
                date=swap.target_date, user_id=swap.requester_id,
                code="TR_IN", description=f"Recebe de: {swap.substitute.nome}",
                shift=swap.target_shift
            ))
        
        flash("Troca aprovada e escala atualizada!", "success")

    db.session.commit()
    return redirect(url_for('swaps.index'))

@bp.route("/print/<int:id>")
@login_required
def print_term(id):
    swap = ShiftSwap.query.get_or_404(id)
    # Só imprime se aprovado
    if swap.status != 'approved': 
        return "Troca não aprovada.", 403
    return render_template("swaps/print_term.html", swap=swap, today=date.today())