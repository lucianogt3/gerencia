from __future__ import annotations
from datetime import datetime
from ..extensions import db

class ShiftSwap(db.Model):
    __tablename__ = "shift_swaps"

    id = db.Column(db.Integer, primary_key=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    substituto_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    setor = db.Column(db.String(80), nullable=True)
    turno_original = db.Column(db.String(20), nullable=False)
    data_original = db.Column(db.Date, nullable=False)

    turno_troca = db.Column(db.String(20), nullable=False)
    data_troca = db.Column(db.Date, nullable=False)

    texto_termo = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(30), default="awaiting_substitute", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class SwapEvent(db.Model):
    __tablename__ = "swap_events"

    id = db.Column(db.Integer, primary_key=True)
    swap_id = db.Column(db.Integer, db.ForeignKey("shift_swaps.id"), nullable=False, index=True)
    event_type = db.Column(db.String(30), nullable=False)  # created, substitute_approved, manager_approved, no_show, etc
    note = db.Column(db.Text, nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
