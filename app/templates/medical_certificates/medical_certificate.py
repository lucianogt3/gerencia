# app/models/medical_certificate.py
from datetime import datetime
from app.extensions import db

class MedicalCertificate(db.Model):
    __tablename__ = 'medical_certificates'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)

    certificate_type = db.Column(db.String(50), nullable=False)  # atestado_medico, licenca, etc
    certificate_file = db.Column(db.String(255))  # caminho do arquivo

    # ✅ NOVO: CID (OPCIONAL)
    cid = db.Column(db.String(20), nullable=True)

    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    manager_notes = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='medical_certificates')
    manager = db.relationship('User', foreign_keys=[manager_id])

    def __repr__(self):
        return f'<MedicalCertificate {self.id} - User {self.user_id}>'
