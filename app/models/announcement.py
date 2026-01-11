from app.extensions import db
from datetime import datetime

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False) # No HTML está 'content', mudei para body
    tipo = db.Column(db.String(20), nullable=False, default="info")
    setor = db.Column(db.String(50))
    is_pinned = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True) # ADICIONE ISSO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # ADICIONE ISSO
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Relacionamento para o HTML conseguir usar a.user.nome
    user = db.relationship('User', backref='my_announcements')