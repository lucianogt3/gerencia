from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
import uuid

from app.extensions import db
from app.models.medical_certificate import MedicalCertificate
from app.models.user import User
from app.models.nursing_schedule import NursingDailyOverride

bp = Blueprint('medical_certificates', __name__, url_prefix='/medical-certificates')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# VISÃO DO COLABORADOR
# =========================
@bp.route('/')
@login_required
def index():
    # Se for gerente, vê todos os atestados
    if current_user.role in ['manager', 'admin']:
        certificates = MedicalCertificate.query.order_by(
            MedicalCertificate.created_at.desc()
        ).all()
    else:
        # Se for colaborador, vê apenas os seus
        certificates = MedicalCertificate.query.filter_by(
            user_id=current_user.id
        ).order_by(
            MedicalCertificate.created_at.desc()
        ).all()
    
    return render_template('medical_certificates/index.html', 
                          certificates=certificates,
                          is_manager=current_user.role in ['manager', 'admin'])

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        # Validação dos dados
        start_date_str = request.form.get('start_date')
        total_days = request.form.get('total_days', type=int)
        certificate_type = request.form.get('certificate_type', 'atestado_medico')
        notes = request.form.get('notes', '')
        
        if not start_date_str or not total_days:
            flash('Data inicial e quantidade de dias são obrigatórios', 'error')
            return redirect(url_for('medical_certificates.new'))
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=total_days - 1)
        
        # Upload do arquivo
        certificate_file = None
        if 'certificate_file' in request.files:
            file = request.files['certificate_file']
            if file and file.filename and allowed_file(file.filename):
                # Cria diretório se não existir
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Gera nome único para o arquivo
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                
                certificate_file = f"certificates/{filename}"
            elif file and file.filename:
                flash('Formato de arquivo não permitido', 'error')
                return redirect(url_for('medical_certificates.new'))
        
        # Cria o atestado
        certificate = MedicalCertificate(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            certificate_type=certificate_type,
            certificate_file=certificate_file,
            notes=notes,
            status='pending'
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        flash('Atestado cadastrado com sucesso! Aguarde a aprovação do gerente.', 'success')
        return redirect(url_for('medical_certificates.index'))
    
    return render_template('medical_certificates/new.html')

# =========================
# VISÃO DO GERENTE
# =========================
@bp.route('/<int:certificate_id>/review', methods=['GET', 'POST'])
@login_required
def review(certificate_id):
    if current_user.role not in ['manager', 'admin']:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('medical_certificates.index'))
    
    certificate = MedicalCertificate.query.get_or_404(certificate_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        manager_notes = request.form.get('manager_notes', '')
        
        if action == 'approve':
            certificate.status = 'approved'
            certificate.manager_id = current_user.id
            certificate.manager_notes = manager_notes
            certificate.approved_at = datetime.utcnow()
            
            # Cria sobreposições na escala diária para cada dia do atestado
            create_override_for_certificate(certificate)
            
            flash('Atestado aprovado com sucesso! As escalas foram atualizadas.', 'success')
            
        elif action == 'reject':
            certificate.status = 'rejected'
            certificate.manager_id = current_user.id
            certificate.manager_notes = manager_notes
            certificate.approved_at = datetime.utcnow()
            
            flash('Atestado rejeitado.', 'success')
        
        db.session.commit()
        return redirect(url_for('medical_certificates.index'))
    
    # Calcula os dias de afastamento
    days_range = []
    current_date = certificate.start_date
    while current_date <= certificate.end_date:
        days_range.append(current_date)
        current_date += timedelta(days=1)
    
    return render_template('medical_certificates/review.html',
                          certificate=certificate,
                          days_range=days_range)

def create_override_for_certificate(certificate):
    """Cria sobreposições na escala diária para cada dia do atestado"""
    user = certificate.user
    
    current_date = certificate.start_date
    while current_date <= certificate.end_date:
        # Verifica se já existe uma sobreposição para este dia
        existing = NursingDailyOverride.query.filter_by(
            user_id=user.id,
            date=current_date
        ).first()
        
        if not existing:
            # Cria nova sobreposição
            override = NursingDailyOverride(
                user_id=user.id,
                date=current_date,
                code='AT',  # Atestado
                notes=f"Atestado médico - {certificate.certificate_type}",
                manager_id=current_user.id,
                is_coop=False
            )
            db.session.add(override)
        
        current_date += timedelta(days=1)

# =========================
# API PARA VERIFICAÇÃO DE ATESTADOS
# =========================
@bp.route('/api/check/<int:user_id>/<date_str>')
@login_required
def check_certificate(user_id, date_str):
    """Verifica se um usuário tem atestado em uma data específica"""
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        certificate = MedicalCertificate.query.filter(
            MedicalCertificate.user_id == user_id,
            MedicalCertificate.start_date <= check_date,
            MedicalCertificate.end_date >= check_date,
            MedicalCertificate.status == 'approved'
        ).first()
        
        if certificate:
            return jsonify({
                'has_certificate': True,
                'type': certificate.certificate_type,
                'days': certificate.total_days,
                'notes': certificate.notes
            })
        
        return jsonify({'has_certificate': False})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# =========================
# DOWNLOAD DO ATESTADO
# =========================
@bp.route('/<int:certificate_id>/download')
@login_required
def download(certificate_id):
    certificate = MedicalCertificate.query.get_or_404(certificate_id)
    
    # Verifica permissões
    if certificate.user_id != current_user.id and current_user.role not in ['manager', 'admin']:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('medical_certificates.index'))
    
    if not certificate.certificate_file:
        flash('Arquivo não encontrado', 'error')
        return redirect(url_for('medical_certificates.index'))
    
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates'),
        certificate.certificate_file.split('/')[-1]
    )