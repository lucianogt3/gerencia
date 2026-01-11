from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models.announcement import Announcement
from app.models.user import User
from app.models.sector import Sector
from sqlalchemy import extract

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@login_required
def root():
    """Rota raiz - redireciona para dashboard ou página de pendência"""
    # Se usuário ainda não foi liberado, mostra página de pendência
    if current_user.status != "active":
        return render_template("auth/pending.html")
    return dashboard()

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Página principal do dashboard"""
    
    # Buscar comunicados ativos (para todos)
    announcements = Announcement.query.filter_by(
        active=True
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()
    
    # Buscar usuários pendentes (apenas para admin/manager)
    pending_list = []
    pending_count = 0
    if current_user.role in ['admin', 'manager']:
        pending_list = User.query.filter_by(status='pending').limit(5).all()
        pending_count = User.query.filter_by(status='pending').count()
    
    # Buscar aniversariantes do mês atual
    hoje = datetime.utcnow()
    aniversariantes = User.query.filter(
        extract('month', User.nascimento) == hoje.month,
        User.status == 'active'
    ).order_by(
        extract('day', User.nascimento)
    ).limit(10).all()
    
    # Contar total de usuários ativos
    active_users_count = User.query.filter_by(status='active').count()
    
    # Buscar setores ativos
    active_sectors = Sector.query.filter_by(active=True).count()
    
    return render_template(
        'main/dashboard.html',
        title='Painel',
        announcements=announcements,
        pending_list=pending_list,
        pending_count=pending_count,
        aniversariantes=aniversariantes,
        active_users_count=active_users_count,
        active_sectors_count=active_sectors
    )

@main_bp.route('/perfil')
@login_required
def profile():
    """Página de perfil do usuário"""
    return render_template('main/profile.html', 
                         title='Meu Perfil')

@main_bp.route('/configuracoes')
@login_required
def settings_page():
    """Página de configurações (apenas admin/manager)"""
    if current_user.role not in ['admin', 'manager']:
        from flask import abort
        abort(403)  # Forbidden
    
    return render_template('main/settings.html', 
                         title='Configurações do Sistema')

@main_bp.route('/ajuda')
@login_required
def help_page():
    """Página de ajuda"""
    return render_template('main/help.html', 
                         title='Ajuda & Suporte')

@main_bp.route('/calendario')
@login_required
def calendar():
    """Calendário de escalas e eventos"""
    return render_template('main/calendar.html', 
                         title='Calendário')