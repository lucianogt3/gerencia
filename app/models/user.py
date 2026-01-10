from __future__ import annotations
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db

SHIFT_CHOICES = ("D", "N", "M", "T", "MT")

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Matrícula/ID do hospital (chave única do sistema)
    matricula = db.Column(db.String(32), unique=True, nullable=False, index=True)

    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=True, index=True)

    # setor por FK (criado pela gerência)
    setor_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=True, index=True)

    # turno padrão do colaborador (não é a escala diária, é cadastro)
    # valores: D, N, M, T, MT
    turno = db.Column(db.String(3), nullable=True, index=True)

    nascimento = db.Column(db.Date, nullable=True)

    password_hash = db.Column(db.String(255), nullable=False)

    # pending -> aguarda liberação, active -> liberado, blocked -> bloqueado
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)

    # role: staff, supervisor, manager, admin
    role = db.Column(db.String(20), default="staff", nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_active_user(self) -> bool:
        return self.status == "active"

    def __repr__(self) -> str:
        return f"<User {self.matricula} {self.nome}>"
