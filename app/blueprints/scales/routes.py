print("--- CARREGANDO O ARQUIVO NOVO DE ESCALAS ---") # <--- ADICIONE ISSO NA LINHA 1
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os

# ✅ CORREÇÃO CRÍTICA: USANDO CAMINHOS ABSOLUTOS
# Isso diz ao Python exatamente onde buscar os arquivos, sem confusão.
from app.utils.security import require_active, require_roles
from app.utils.uploads import save_upload
from app.utils.dates import month_name
from app.extensions import db
from app.models.scale import Scale

# Define o Blueprint
bp = Blueprint("scales", __name__, url_prefix="/scales")

@bp.route("/")
@login_required
@require_active
def index():
    ano = request.args.get("ano", type=int) or datetime.utcnow().year
    mes = request.args.get("mes", type=int) or datetime.utcnow().month
    categoria = request.args.get("categoria", default="")
    servico = request.args.get("servico", default="")

    try:
        q = Scale.query.filter_by(ano=ano, mes=mes)
        if categoria:
            q = q.filter_by(categoria=categoria)
        if servico:
            q = q.filter(Scale.servico.ilike(f"%{servico}%"))
        scales = q.order_by(Scale.created_at.desc()).all()
    except Exception:
        scales = [] 

    return render_template("scales/index.html", scales=scales, ano=ano, mes=mes, month_name=month_name, categoria=categoria, servico=servico)

@bp.route("/upload", methods=["GET","POST"])
@login_required
@require_active
@require_roles("manager","admin")
def upload():
    # Importação absoluta do formulário também
    from app.blueprints.scales.forms import ScaleUploadForm
    
    form = ScaleUploadForm()
    if form.validate_on_submit():
        stored, original = save_upload(form.arquivo.data, subdir="scales", allowed_exts={".pdf",".png",".jpg",".jpeg",".webp",".xlsx"})
        s = Scale(
            categoria=form.categoria.data,
            servico=form.servico.data.strip(),
            setor=(form.setor.data or "").strip() or None,
            ano=form.ano.data,
            mes=int(form.mes.data),
            status="published",
            filename=stored,
            original_name=original,
            published_at=datetime.utcnow(),
            published_by_id=current_user.id,
        )
        db.session.add(s)
        db.session.commit()
        flash("Escala publicada.", "success")
        return redirect(url_for("scales.index", ano=s.ano, mes=s.mes, categoria=s.categoria, servico=s.servico))
    return render_template("scales/upload.html", form=form)

@bp.route("/<int:scale_id>")
@login_required
@require_active
def view(scale_id: int):
    s = Scale.query.get_or_404(scale_id)
    return render_template("scales/view.html", s=s, month_name=month_name)

@bp.route("/file/<filename>")
@login_required
@require_active
def file(filename: str):
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "scales")
    return send_from_directory(folder, filename, as_attachment=False)