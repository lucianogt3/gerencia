from datetime import datetime
from app.extensions import db

class SickNote(db.Model):
    __tablename__ = "sick_notes"

    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(32), nullable=False)
    nome = db.Column(db.String(120))
    setor = db.Column(db.String(80))
    turno = db.Column(db.String(20))

    data_atestado = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, nullable=False)

    # upload
    filename = db.Column(db.String(255))
    original_name = db.Column(db.String(255))

    # ✅ CID opcional (se você adicionou a coluna)
    cid = db.Column(db.String(20), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved/rejected
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<SickNote {self.id} {self.matricula} {self.status}>"
