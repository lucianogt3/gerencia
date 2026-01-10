from datetime import date, datetime
from ..extensions import db

class ScaleDaily(db.Model):
    __tablename__ = "scales_daily"

    id = db.Column(db.Integer, primary_key=True)

    data = db.Column(db.Date, nullable=False)

    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    status = db.Column(
        db.String(30),
        nullable=False,
        default="presente"
    )
    # presente | falta | atestado | substituido | extra | folga | remanejado

    substituto_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    observacao = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
