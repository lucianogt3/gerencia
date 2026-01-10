from __future__ import annotations
from datetime import datetime, date
from ..extensions import db

class SickNote(db.Model):
    __tablename__ = "sick_notes"

    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(32), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=True)
    setor = db.Column(db.String(80), nullable=True)
    turno = db.Column(db.String(20), nullable=True)

    data_atestado = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, nullable=False)

    filename = db.Column(db.String(255), nullable=True)
    original_name = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(20), default="pending", nullable=False, index=True)  # pending/validated/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
