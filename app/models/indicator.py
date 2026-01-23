from app.extensions import db
from datetime import datetime

class DailyIndicator(db.Model):
    __tablename__ = "daily_indicators"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    turno = db.Column(db.String(10), nullable=False) # Diurno / Noturno
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=True)

    # Auditoria e Lógica de Adesão
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)      # Preenchido após o horário
    is_cooperative = db.Column(db.Boolean, default=False) # Lançado pela Gerência

    # --- OS 19 ITENS DINÂMICOS ---
    censo_dia = db.Column(db.Integer, default=0)
    admissoes = db.Column(db.Integer, default=0)
    altas_transferencias = db.Column(db.Integer, default=0)
    obitos = db.Column(db.Integer, default=0)
    quedas_paciente = db.Column(db.Integer, default=0)
    extubacao_acidental = db.Column(db.Integer, default=0)
    novas_lpp = db.Column(db.Integer, default=0)
    erros_medicacao = db.Column(db.Integer, default=0)
    broncoaspiracao = db.Column(db.Integer, default=0)
    parada_cardio = db.Column(db.Integer, default=0)
    reinternacao_24h = db.Column(db.Integer, default=0)
    faltas_tecnicos = db.Column(db.Integer, default=0)
    atestados_equipe = db.Column(db.Integer, default=0)
    horas_extras_geradas = db.Column(db.Float, default=0.0)
    manutencao_equipamento = db.Column(db.Boolean, default=False)
    falta_insumo_critico = db.Column(db.Boolean, default=False)
    exames_pendentes = db.Column(db.Integer, default=0)
    conclusao_prontuarios = db.Column(db.Boolean, default=False)
    conflitos_acompanhantes = db.Column(db.Integer, default=0)

    user = db.relationship("User", backref="indicators")