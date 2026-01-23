from __future__ import annotations
from datetime import datetime
from app.extensions import db

class ShiftSwap(db.Model):
    __tablename__ = "shift_swaps"

    id = db.Column(db.Integer, primary_key=True)
    
    # QUEM PEDE (Vai sair da escala no dia original)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # QUEM SUBSTITUI (Vai entrar na escala no dia original)
    substitute_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # --- DADOS DO PLANTÃO ORIGINAL (O dia da falta/troca) ---
    original_date = db.Column(db.Date, nullable=False)
    original_shift = db.Column(db.String(5), nullable=False) # D ou N

    # --- DADOS DA DEVOLUÇÃO (O dia do pagamento) ---
    # Pode ser nulo se for doação de plantão ou banco de horas
    target_date = db.Column(db.Date, nullable=True)
    target_shift = db.Column(db.String(5), nullable=True)

    # --- DADOS DO FORMULÁRIO ---
    reason = db.Column(db.String(255)) # Justificativa
    request_type = db.Column(db.String(50), default="empregado") # "empregado" ou "servico"
    
    # --- CONTROLE ---
    # Status: pending, approved, refused
    status = db.Column(db.String(20), default="pending", nullable=False)
    refusal_reason = db.Column(db.String(255)) # Motivo da recusa (obrigatório se recusar)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    requester = db.relationship("User", foreign_keys=[requester_id], backref="swaps_requested")
    substitute = db.relationship("User", foreign_keys=[substitute_id], backref="swaps_substituted")