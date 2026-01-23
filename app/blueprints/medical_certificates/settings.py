from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sector import Sector
from app.models.user import User
from datetime import datetime

bp = Blueprint('settings', __name__, url_prefix='/settings')

# =========================
# GERENCIAMENTO DE SETORES
# =========================
@bp.route('/sectors')
@login_required
def sectors():
    if current_user.role not in ['manager', 'admin']:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('dashboard.index'))
    
    sectors_list = Sector.query.filter_by(active=True).order_by(Sector.name).all()
    return render_template('settings/sectors.html', sectors=sectors_list)

@bp.route('/sectors/create', methods=['POST'])
@login_required
def create_sector():
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 403
    
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nome do setor é obrigatório', 'error')
        return redirect(url_for('settings.sectors'))
    
    # Verifica se já existe
    existing = Sector.query.filter_by(name=name).first()
    if existing:
        flash('Já existe um setor com este nome', 'error')
        return redirect(url_for('settings.sectors'))
    
    new_sector = Sector(
        name=name,
        description=request.form.get('description', ''),
        active=True,
        created_by_id=current_user.id
    )
    
    db.session.add(new_sector)
    db.session.commit()
    
    flash('Setor criado com sucesso', 'success')
    return redirect(url_for('settings.sectors'))

@bp.route('/sectors/<int:sector_id>/edit', methods=['POST'])
@login_required
def edit_sector(sector_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 403
    
    sector = Sector.query.get_or_404(sector_id)
    
    sector.name = request.form.get('name', sector.name)
    sector.description = request.form.get('description', sector.description)
    sector.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Setor atualizado com sucesso', 'success')
    return redirect(url_for('settings.sectors'))

@bp.route('/sectors/<int:sector_id>/toggle', methods=['POST'])
@login_required
def toggle_sector(sector_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 403
    
    sector = Sector.query.get_or_404(sector_id)
    sector.active = not sector.active
    sector.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    status = 'ativado' if sector.active else 'desativado'
    flash(f'Setor {status} com sucesso', 'success')
    return redirect(url_for('settings.sectors'))

# =========================
# GERENCIAMENTO DE COLABORADORES POR SETOR
# =========================
@bp.route('/sectors/<int:sector_id>/users')
@login_required
def sector_users(sector_id):
    if current_user.role not in ['manager', 'admin']:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('dashboard.index'))
    
    sector = Sector.query.get_or_404(sector_id)
    users = User.query.filter_by(sector_id=sector_id, status='active').order_by(User.nome).all()
    all_users = User.query.filter_by(status='active').order_by(User.nome).all()
    
    return render_template('settings/sector_users.html', 
                          sector=sector, 
                          users=users, 
                          all_users=all_users)

@bp.route('/sectors/<int:sector_id>/add-user', methods=['POST'])
@login_required
def add_user_to_sector(sector_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 403
    
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Usuário não especificado'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
    
    user.sector_id = sector_id
    user.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'{user.nome} adicionado ao setor'})

@bp.route('/sectors/<int:sector_id>/remove-user/<int:user_id>', methods=['POST'])
@login_required
def remove_user_from_sector(sector_id, user_id):
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
    
    if user.sector_id == sector_id:
        user.sector_id = None
        user.updated_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({'success': True, 'message': f'{user.nome} removido do setor'})