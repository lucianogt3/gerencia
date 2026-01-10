from datetime import date, datetime
from ..extensions import db

class Absence(db.Model):
    __tablename__ = "absences"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    data = db.Column(db.Date, primary_key=True)

    tipo = db.Column(db.String(20), nullable=False)
    # falta | atestado

    aprovado = db.Column(db.Boolean, default=False)
    aprovado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
