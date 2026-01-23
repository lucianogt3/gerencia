from __future__ import annotations
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from sqlalchemy.orm import object_session

from app.extensions import db
from app.models.sector import Sector

class User(db.Model, UserMixin):
    __tablename__ = "users"

    # ✅ LISTA DE ROLES ATUALIZADA COM 'condutor'
    ALLOWED_ROLES = ("staff", "technician", "nurse", "condutor", "manager", "admin")
    
    ALLOWED_STATUS = ("pending", "active", "blocked")

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados de Login
    matricula = db.Column(db.String(10), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Dados Pessoais
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=True)
    nascimento = db.Column(db.Date, nullable=False)

    # Dados Funcionais
    setor = db.Column(db.String(80), nullable=True) # Nome do setor (cache)
    turno = db.Column(db.String(10), nullable=True) # D ou N
    
    # Relacionamento com Setor
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=True, index=True)
    sector = db.relationship("Sector", backref="users")

    # Permissões e Status
    role = db.Column(db.String(20), default="staff", nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self) -> str:
        """Rótulo amigável para aparecer na tela."""
        return {
            "staff": "Administrativo",
            "technician": "Técnico",
            "nurse": "Enfermeiro",
            "condutor": "Condutor",  # ✅ ADICIONADO AQUI
            "manager": "Gerência",
            "admin": "Admin",
        }.get(self.role, self.role)

    def __repr__(self):
        return f"<User {self.matricula} - {self.nome}>"

# --- EVENTOS PARA SINCRONIZAR NOME DO SETOR COM ID ---
@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def _sync_user_sector(mapper, connection, target: "User"):
    sess = object_session(target)
    if sess is None:
        return

    st = getattr(target, "setor", None)
    sid = getattr(target, "sector_id", None)

    # 1) Se tiver ID, atualiza o nome
    if sid:
        sec = sess.get(Sector, int(sid))
        if sec:
            target.setor = sec.name
        return

    # 2) Se tiver nome, tenta achar o ID
    if st:
        sec = sess.query(Sector).filter(Sector.name == st).first()
        if sec:
            target.sector_id = sec.id