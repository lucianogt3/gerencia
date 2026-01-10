from __future__ import annotations
from datetime import datetime
from ..extensions import db

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # POP/Protocolo/Politica/Checklist
    setor = db.Column(db.String(80), nullable=True)
    tags = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), default="draft", nullable=False, index=True)  # draft/review/approved/archived
    current_version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id"), nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class DocumentVersion(db.Model):
    __tablename__ = "document_versions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)

    version_label = db.Column(db.String(20), nullable=False)  # v1, v2...
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class DocumentRead(db.Model):
    __tablename__ = "document_reads"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    first_opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    open_count = db.Column(db.Integer, default=1, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("document_id", "user_id", name="uq_doc_user_read"),
    )
