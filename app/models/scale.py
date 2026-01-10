from __future__ import annotations
from datetime import datetime
from ..extensions import db

class Scale(db.Model):
    __tablename__ = "scales"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(20), nullable=False)  # Medica/Enfermagem
    servico = db.Column(db.String(80), nullable=False)    # Cardiologia/Neuro etc.
    setor = db.Column(db.String(80), nullable=True)

    ano = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)  # 1-12

    status = db.Column(db.String(20), default="draft", nullable=False, index=True)  # draft/published/archived

    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)

    published_at = db.Column(db.DateTime, nullable=True)
    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
