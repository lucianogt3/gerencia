from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    # Roles oficiais do projeto
    ALLOWED_ROLES = ("staff", "technician", "nurse", "manager", "admin")

    # Status oficiais do projeto
    ALLOWED_STATUS = ("pending", "active", "blocked")

    id = db.Column(db.Integer, primary_key=True)

    # Matrícula gerada automaticamente (001, 002, ...)
    matricula = db.Column(db.String(10), unique=True, nullable=False, index=True)

    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=True)

    setor = db.Column(db.String(80), nullable=True)
    turno = db.Column(db.String(10), nullable=True)

    # ✅ Agora obrigatório no banco (como está no formulário e no template)
    nascimento = db.Column(db.Date, nullable=False)

    role = db.Column(db.String(20), default="staff", nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self) -> str:
        """Rótulo amigável para UI (opcional)."""
        return {
            "staff": "Administrativo",
            "technician": "Técnico",
            "nurse": "Enfermeiro",
            "technician": "Técnico",
            "manager": "Gerência",
            "admin": "Admin",
        }.get(self.role, self.role)

    def __repr__(self):
        return f"<User {self.matricula} - {self.nome}>"
