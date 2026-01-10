from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, abort
from flask_login import login_required, current_user
from ...utils.security import require_active, require_roles
from ...utils.uploads import save_upload
from ...extensions import db
from ...models.document import Document, DocumentVersion, DocumentRead
from .forms import DocumentUploadForm
from .services import register_open
import os

docs_bp = Blueprint("docs", __name__, url_prefix="/docs")

@docs_bp.route("/")
@login_required
@require_active
def index():
    docs = Document.query.order_by(Document.updated_at.desc()).all()
    # agregados simples
    # contagem de leituras por doc
    reads = DocumentRead.query.all()
    reads_map = {}
    for r in reads:
        reads_map.setdefault(r.document_id, {"users": 0, "opens": 0})
        reads_map[r.document_id]["users"] += 1
        reads_map[r.document_id]["opens"] += (r.open_count or 0)

    return render_template("docs/index.html", docs=docs, reads_map=reads_map)

@docs_bp.route("/upload", methods=["GET", "POST"])
@login_required
@require_active
@require_roles("manager", "admin")
def upload():
    form = DocumentUploadForm()
    if form.validate_on_submit():
        stored, original = save_upload(form.arquivo.data, subdir="docs", allowed_exts={".pdf",".png",".jpg",".jpeg",".webp",".docx"})

        doc = Document(
            titulo=form.titulo.data.strip(),
            tipo=form.tipo.data,
            setor=(form.setor.data or "").strip() or None,
            tags=(form.tags.data or "").strip() or None,
            status="approved",  # por enquanto, já aprova (você pode mudar p/ review depois)
            created_by_id=current_user.id,
        )
        db.session.add(doc)
        db.session.flush()

        v = DocumentVersion(
            document_id=doc.id,
            version_label="v1",
            filename=stored,
            original_name=original,
            uploaded_by_id=current_user.id,
        )
        db.session.add(v)
        db.session.flush()

        doc.current_version_id = v.id
        db.session.commit()

        flash("Documento enviado.", "success")
        return redirect(url_for("docs.index"))

    return render_template("docs/upload.html", form=form)

@docs_bp.route("/<int:doc_id>")
@login_required
@require_active
def view(doc_id: int):
    doc = Document.query.get_or_404(doc_id)
    if not doc.current_version_id:
        abort(404)

    # registra abertura/leitura automática
    register_open(doc_id, current_user.id)

    version = DocumentVersion.query.get(doc.current_version_id)
    return render_template("docs/view.html", doc=doc, version=version)

@docs_bp.route("/file/<filename>")
@login_required
@require_active
def file(filename: str):
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "docs")
    return send_from_directory(folder, filename, as_attachment=False)

@docs_bp.route("/report")
@login_required
@require_active
@require_roles("manager", "admin")
def report():
    # relatório simples de leituras/aberturas por doc
    docs = Document.query.order_by(Document.updated_at.desc()).all()
    reads = DocumentRead.query.all()
    reads_by_doc = {}
    for r in reads:
        reads_by_doc.setdefault(r.document_id, [])
        reads_by_doc[r.document_id].append(r)
    return render_template("docs/report.html", docs=docs, reads_by_doc=reads_by_doc)
