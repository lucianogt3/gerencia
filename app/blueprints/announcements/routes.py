from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from ...extensions import db
# ✅ IMPORTANTE: Importando tudo de app.models (arquivo unificado)
from ...models import Announcement, AnnouncementRead, User, Sector

bp = Blueprint("announcements", __name__, url_prefix="/announcements")

# Função auxiliar para verificar permissão
def is_manager():
    return getattr(current_user, 'role', '') in ["manager", "admin"]

@bp.get("/")
@login_required
def index():
    tipo = request.args.get("tipo")
    setor = request.args.get("setor")
    
    query = Announcement.query
    
    # Se não for gerente, só vê os ativos
    if not is_manager():
        query = query.filter_by(active=True)

    if tipo:
        query = query.filter_by(tipo=tipo)
    if setor:
        query = query.filter_by(setor=setor)

    # Ordena por fixados primeiro, depois por data
    announcements = query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).all()
    
    # Busca setores para o filtro
    sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()
    
    return render_template("announcements/index.html", 
                           title="Comunicados", 
                           announcements=announcements, 
                           sectors=sectors)

@bp.get("/new")
@login_required
def new():
    if not is_manager():
        flash("Acesso restrito.", "danger")
        return redirect(url_for('announcements.index'))
    return render_template("announcements/new.html", title="Novo Comunicado")

@bp.post("/new")
@login_required
def create():
    if not is_manager():
        return redirect(url_for('announcements.index'))

    tipo = (request.form.get("tipo") or "info").strip()
    title = (request.form.get("title") or "").strip()
    # ✅ Corrigido: usando 'content' em vez de 'body'
    content = (request.form.get("content") or "").strip() 
    setor = (request.form.get("setor") or "").strip() or None
    is_pinned = (request.form.get("is_pinned") == "on")

    if not title:
        flash("Título é obrigatório.", "warning")
        return redirect(url_for("announcements.new"))

    a = Announcement(
        tipo=tipo,
        title=title,
        content=content,
        setor=setor,
        is_pinned=is_pinned,
        created_by_id=current_user.id,
        active=True
    )

    try:
        db.session.add(a)
        db.session.commit()
        flash("Comunicado publicado.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao salvar: {str(e)}", "danger")
        
    return redirect(url_for("announcements.index"))

@bp.get("/<int:id>")
@login_required
def detail(id):
    # Rota de detalhe (opcional, já que o index mostra tudo)
    a = Announcement.query.get_or_404(id)
    
    # Se não for gerente e estiver inativo, bloqueia
    if not a.active and not is_manager():
        flash("Este comunicado não está disponível.", "warning")
        return redirect(url_for('announcements.index'))

    # Marca leitura ao abrir detalhe
    if not a.is_read_by(current_user):
        db.session.add(AnnouncementRead(announcement_id=a.id, user_id=current_user.id))
        db.session.commit()

    return render_template("announcements/detail.html", title=a.title, a=a)

@bp.get("/<int:id>/edit")
@login_required
def edit(id):
    if not is_manager():
        return redirect(url_for('announcements.index'))
    a = Announcement.query.get_or_404(id)
    return render_template("announcements/new.html", title="Editar Comunicado", a=a)

@bp.post("/<int:id>/edit")
@login_required
def update(id):
    if not is_manager():
        return redirect(url_for('announcements.index'))
        
    a = Announcement.query.get_or_404(id)
    a.title = request.form.get("title")
    # ✅ Corrigido: usando 'content'
    a.content = request.form.get("content")
    a.tipo = request.form.get("tipo")
    a.setor = request.form.get("setor")
    a.is_pinned = (request.form.get("is_pinned") == "on")
    
    db.session.commit()
    flash("Comunicado atualizado!", "success")
    return redirect(url_for("announcements.index"))

@bp.post("/<int:id>/delete")
@login_required
def delete(id):
    if not is_manager():
        return redirect(url_for('announcements.index'))
        
    a = Announcement.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash("Comunicado excluído.", "success")
    return redirect(url_for("announcements.index"))

@bp.post("/<int:id>/toggle")
@login_required
def toggle(id):
    if not is_manager():
        return redirect(url_for('announcements.index'))
        
    a = Announcement.query.get_or_404(id)
    a.active = not a.active
    db.session.commit()
    
    status = "ativado" if a.active else "desativado"
    flash(f"Comunicado {status}!", "info")
    return redirect(url_for("announcements.index"))

# ✅ ROTA AJAX: Marcar como lido
@bp.route('/<int:id>/mark_read', methods=['POST'])
@login_required
def mark_read(id):
    announcement = Announcement.query.get_or_404(id)
    
    # Verifica se já leu para não duplicar (usa o método do model)
    if not announcement.is_read_by(current_user):
        new_read = AnnouncementRead(user_id=current_user.id, announcement_id=announcement.id)
        db.session.add(new_read)
        db.session.commit()
        
    # Retorna JSON para o frontend atualizar o contador
    return jsonify({
        'ok': True, 
        'count': announcement.reads.count()
    })