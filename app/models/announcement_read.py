from app.extensions import db
from datetime import datetime

# 1. Tabela de Leituras (Sua versão melhorada com UniqueConstraint)
class AnnouncementRead(db.Model):
    __tablename__ = "announcement_reads"
    id = db.Column(db.Integer, primary_key=True)
    
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user"),
    )

# 2. Tabela de Comunicados
class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
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
    
    # Relacionamento com as leituras
    reads = db.relationship('AnnouncementRead', backref='announcement', lazy='dynamic', cascade="all, delete-orphan")

    def is_read_by(self, user):
        """Verifica se o usuário já leu este comunicado."""
        if not user or not user.is_authenticated:
            return False
        return self.reads.filter_by(user_id=user.id).count() > 0