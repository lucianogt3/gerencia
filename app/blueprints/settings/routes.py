from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime

from ...extensions import db
from ...models import Sector, User

bp = Blueprint("settings", __name__, url_prefix="/settings")


def _require_manager():
    return getattr(current_user, "role", "") in ("manager", "admin")


@bp.get("/")
@login_required
def index():
    if not _require_manager():
        return render_template("errors/403.html"), 403
    return redirect(url_for("settings.sectors"))


# --------------------
# Setores
# --------------------
@bp.get("/sectors")
@login_required
def sectors():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    q = (request.args.get("q") or "").strip()
    query = Sector.query
    if q:
        query = query.filter(Sector.name.ilike(f"%{q}%"))

    sectors = query.order_by(Sector.active.desc(), Sector.name.asc()).all()
    return render_template("settings/sectors.html", title="Configurações • Setores", sectors=sectors, q=q)


@bp.post("/sectors/create")
@login_required
def sectors_create():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Nome do setor é obrigatório.", "danger")
        return redirect(url_for("settings.sectors"))

    exists = Sector.query.filter_by(name=name).first()
    if exists:
        flash("Setor já existe.", "warning")
        return redirect(url_for("settings.sectors"))

    s = Sector(name=name, active=True)
    db.session.add(s)
    db.session.commit()
    flash("Setor criado com sucesso.", "success")
    return redirect(url_for("settings.sectors"))


@bp.post("/sectors/<int:sector_id>/toggle")
@login_required
def sectors_toggle(sector_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    s = Sector.query.get_or_404(sector_id)
    s.active = not bool(s.active)
    db.session.commit()
    flash("Setor atualizado.", "success")
    return redirect(url_for("settings.sectors"))


# --------------------
# Colaboradores
# --------------------
@bp.get("/users")
@login_required
def users():
    if not _require_manager():
        return render_template("errors/403.html"), 403

    q = (request.args.get("q") or "").strip()
    role = (request.args.get("role") or "").strip()
    status = (request.args.get("status") or "").strip()

    query = User.query
    if q:
        query = query.filter(
            (User.nome.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%")) |
            (User.matricula.ilike(f"%{q}%"))
        )
    if role:
        query = query.filter_by(role=role)
    if status:
        query = query.filter_by(status=status)

    users = query.order_by(User.status.asc(), User.nome.asc()).all()
    sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()

    return render_template(
        "settings/users.html",
        title="Configurações • Colaboradores",
        users=users,
        sectors=sectors,
        q=q,
        role=role,
        status=status,
    )


@bp.post("/users/<int:user_id>/toggle")
@login_required
def users_toggle(user_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    u = User.query.get_or_404(user_id)
    u.status = "blocked" if (u.status == "active") else "active"
    db.session.commit()
    flash("Usuário atualizado.", "success")
    return redirect(url_for("settings.users"))


@bp.post("/users/<int:user_id>/update")
@login_required
def users_update(user_id: int):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    u = User.query.get_or_404(user_id)

    # agora vem do select como ID (string)
    sector_id_raw = (request.form.get("sector_id") or "").strip()
    turno = (request.form.get("turno") or "").strip() or None
    role = (request.form.get("role") or "").strip() or None

    # ---- SETOR (FK + texto) ----
    if sector_id_raw:
        try:
            sector_id = int(sector_id_raw)
        except ValueError:
            sector_id = None

        if sector_id:
            s = Sector.query.get(sector_id)
            if s:
                # grava FK
                if hasattr(u, "sector_id"):
                    u.sector_id = s.id
                # grava texto (para UI e compatibilidade)
                if hasattr(u, "setor"):
                    u.setor = s.name
            else:
                flash("Setor inválido.", "danger")
                return redirect(url_for("settings.users"))
    else:
        # se escolher "— Setor —" limpa
        if hasattr(u, "sector_id"):
            u.sector_id = None
        if hasattr(u, "setor"):
            u.setor = None

    # ---- TURNO ----
    if hasattr(u, "turno"):
        u.turno = turno

    # ---- ROLE ----
    # inclua technician também (você usa isso no template!)
    if role in ("staff", "technician", "nurse", "manager", "admin"):
        u.role = role

    db.session.commit()
    flash("Dados do colaborador atualizados.", "success")
    return redirect(url_for("settings.users"))


@bp.post("/users/<int:user_id>/reset-password")
@login_required
def users_reset_password(user_id):
    if not _require_manager():
        return render_template("errors/403.html"), 403

    # Busca o usuário
    user = User.query.get_or_404(user_id)
    
    # Define a senha padrão
    nova_senha = "123456"
    user.set_password(nova_senha)
    
    # Salva no banco
    db.session.commit()
    
    flash(f"Senha de {user.nome} resetada com sucesso para: {nova_senha}", "success")
    
    # Retorna para a página de onde veio (ou para a lista de usuários)
    return redirect(request.referrer or url_for('settings.users'))


# --------------------
# Perfil do Usuário (Todos podem acessar)
# --------------------
@bp.get("/profile")
@login_required
def profile():
    """Exibe a página de perfil do usuário"""
    return render_template("settings/profile.html", user=current_user, title="Meu Perfil")


@bp.post("/profile/update")
@login_required
def update_profile():
    """Atualiza os dados do perfil do usuário atual"""
    try:
        # Campos obrigatórios
        required_fields = ['nome', 'email', 'matricula', 'turno', 'data_nascimento']
        for field in required_fields:
            if field not in request.form or not request.form[field].strip():
                flash(f'O campo {field} é obrigatório', 'danger')
                return redirect(url_for('settings.profile'))
        
        # Validar e atualizar matrícula (apenas números)
        matricula = request.form['matricula'].strip()
        if not matricula.isdigit():
            flash('A matrícula deve conter apenas números', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Atualizar campos básicos
        current_user.nome = request.form['nome'].strip()
        current_user.email = request.form['email'].strip()
        current_user.matricula = matricula
        current_user.turno = request.form['turno']
        
        # Validar e atualizar data de nascimento
        try:
            data_nascimento = datetime.strptime(
                request.form['data_nascimento'], '%Y-%m-%d'
            ).date()
            current_user.data_nascimento = data_nascimento
        except ValueError:
            flash('Data de nascimento inválida. Use o formato AAAA-MM-DD.', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Campos opcionais
        optional_fields = ['telefone', 'rg', 'cpf', 'coren']
        for field in optional_fields:
            if field in request.form:
                setattr(current_user, field, request.form[field].strip() or None)
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')
    
    return redirect(url_for('settings.profile'))


@bp.post("/profile/avatar")
@login_required
def update_avatar():
    """Atualiza a foto de perfil (implementação básica)"""
    try:
        # Verificar se foi enviado um arquivo
        if 'foto' not in request.files:
            flash('Nenhuma foto selecionada', 'danger')
            return redirect(url_for('settings.profile'))
        
        foto = request.files['foto']
        
        # Verificar se o arquivo tem nome
        if foto.filename == '':
            flash('Nenhuma foto selecionada', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Verificar se é uma imagem
        if not foto.content_type.startswith('image/'):
            flash('Por favor, selecione apenas imagens (JPG, PNG, GIF)', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Verificar tamanho do arquivo (máximo 5MB)
        foto.seek(0, 2)  # Vai para o final do arquivo
        tamanho = foto.tell()
        foto.seek(0)  # Volta para o início
        
        if tamanho > 5 * 1024 * 1024:  # 5MB
            flash('A imagem não pode ter mais que 5MB', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Aqui você implementaria o salvamento da imagem
        # Por enquanto, apenas simula o sucesso
        # Em produção, salve em um diretório seguro e armazene o caminho no banco
        
        # current_user.foto_url = f'/uploads/avatars/{current_user.id}.jpg'
        
        # db.session.commit()
        
        flash('Foto atualizada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar foto: {str(e)}', 'danger')
    
    return redirect(url_for('settings.profile'))


@bp.post("/profile/remove-avatar")
@login_required
def remove_avatar():
    """Remove a foto de perfil"""
    try:
        # Remover a foto do perfil
        current_user.foto_url = None
        db.session.commit()
        flash('Foto removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover foto: {str(e)}', 'danger')
    
    return redirect(url_for('settings.profile'))


@bp.post("/profile/change-password")
@login_required
def change_password():
    """Altera a senha do usuário"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validar campos
        if not all([current_password, new_password, confirm_password]):
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Verificar senha atual
        if not current_user.check_password(current_password):
            flash('Senha atual incorreta', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Verificar se as novas senhas coincidem
        if new_password != confirm_password:
            flash('As novas senhas não coincidem', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Verificar força da senha (mínimo 6 caracteres)
        if len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres', 'danger')
            return redirect(url_for('settings.profile'))
        
        # Atualizar senha
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Senha alterada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar senha: {str(e)}', 'danger')
    
    return redirect(url_for('settings.profile'))