from datetime import datetime
from ..extensions import db

class ScaleMonthly(db.Model):
    __tablename__ = "scales_monthly"

    id = db.Column(db.Integer, primary_key=True)

    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)

    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
