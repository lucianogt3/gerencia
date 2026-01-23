from app.extensions import db
from datetime import datetime

# --- NOVO: Tabela para salvar quem leu ---
class AnnouncementRead(db.Model):
    __tablename__ = 'announcement_reads'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    
    # Voltei para 'content' para funcionar com seu HTML atual ({{ a.content }})
    content = db.Column(db.Text, nullable=False) 
    
    tipo = db.Column(db.String(20), nullable=False, default="info")
    setor = db.Column(db.String(50))
    is_pinned = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relacionamentos
    user = db.relationship('User', backref='my_announcements')
    
    # Relacionamento com as leituras (lazy='dynamic' permite usar .count())
    reads = db.relationship('AnnouncementRead', backref='announcement', lazy='dynamic', cascade="all, delete-orphan")

    # Função auxiliar para o HTML saber se o usuário logado já leu
    def is_read_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.reads.filter_by(user_id=user.id).count() > 0