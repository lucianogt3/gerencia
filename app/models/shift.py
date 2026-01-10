from datetime import datetime
from ..extensions import db

class Shift(db.Model):
    __tablename__ = "shifts"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(10), unique=True, nullable=False)
    descricao = db.Column(db.String(50), nullable=False)

    # exemplos:
    # D  -> Diurno
    # N  -> Noturno
    # M  -> Manhã
    # T  -> Tarde
    # MT -> Manhã/Tarde

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
