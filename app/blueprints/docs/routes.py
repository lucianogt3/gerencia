from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import extract

from app.utils.security import require_active

# Modelos (com fallback para evitar quebra do sistema caso os arquivos não existam)
try:
    from app.models.document import Document
except ImportError:
    Document = None

try:
    from app.models.document_read import DocumentRead
except ImportError:
    DocumentRead = None


docs_bp = Blueprint("docs", __name__, url_prefix="/docs")


@docs_bp.get("/")
@login_required
@require_active
def index():
    # Se os modelos não existirem ainda (NurseTec ou auditoria_hospitalar), não quebra o sistema
    if Document is None:
        stats = {"pop": 0, "protocolo": 0, "manual": 0, "outros": 0}
        return render_template(
            "docs/index.html",
            stats=stats,
            docs=[],
            years=range(2026, 2022, -1),
            search="",
            selected_year=None,
            selected_type=None,
            reads_map={},
        )

    # 1. CAPTURA DE PARÂMETROS DA URL
    search = (request.args.get("search") or "").strip()
    year = request.args.get("year", type=int)
    doc_type = request.args.get("tipo") # ✅ Correção do NameError: Definindo doc_type

    # 2. CONSTRUÇÃO DA QUERY
    query = Document.query
    
    if search:
        query = query.filter(Document.titulo.ilike(f"%{search}%"))
        
    if year:
        query = query.filter(extract("year", Document.created_at) == year)

    if doc_type:
        query = query.filter_by(tipo=doc_type)

    # 3. EXECUÇÃO DA BUSCA
    docs = query.order_by(Document.updated_at.desc()).all()

    # 4. CÁLCULO DE ESTATÍSTICAS (KPIs para o Nurse Manager Portal)
    stats = {
        "pop": Document.query.filter_by(tipo="POP").count(),
        "protocolo": Document.query.filter_by(tipo="Protocolo").count(),
        "manual": Document.query.filter_by(tipo="Manual").count(),
        "outros": Document.query.filter(Document.tipo.notin_(["POP", "Protocolo", "Manual"])).count(),
    }

    years_range = range(2026, 2022, -1)

    # 5. MAPEAMENTO DE LEITURA (Para auditoria hospitalar)
    reads_map = {}
    if DocumentRead is not None:
        reads = DocumentRead.query.filter_by(user_id=current_user.id).all()
        reads_map = {r.document_id: True for r in reads}

    # 6. RENDERIZAÇÃO
    return render_template(
        "docs/index.html",
        title="Documentos",
        docs=docs,
        stats=stats,
        years=years_range,
        search=search,
        selected_year=year,
        selected_type=doc_type,
        reads_map=reads_map,
    )