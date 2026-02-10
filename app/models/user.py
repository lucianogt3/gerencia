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

    ALLOWED_ROLES = ("staff", "technician", "nurse", "condutor", "manager", "admin")
    ALLOWED_STATUS = ("pending", "active", "blocked")

    id = db.Column(db.Integer, primary_key=True)

    # ✅ Controle de primeiro acesso / segurança (SQLite-friendly)
    first_login = db.Column(
        db.Boolean, nullable=False, default=True, server_default="1"
    )
    force_password_change = db.Column(
        db.Boolean, nullable=False, default=True, server_default="1"
    )

    last_login_at = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    profile_completed_at = db.Column(db.DateTime, nullable=True)

    # Dados de Login
    matricula = db.Column(db.String(40), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Dados Pessoais
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=True)
    nascimento = db.Column(db.Date, nullable=False)

    # Dados Funcionais
    setor = db.Column(db.String(80), nullable=True)  # cache do nome do setor
    turno = db.Column(db.String(10), nullable=True)  # D ou N

    # Relacionamento com Setor
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=True, index=True)
    sector = db.relationship("Sector", backref="users")

    # Permissões e Status
    role = db.Column(db.String(20), default="staff", nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
        # se trocar senha, deixa de forçar troca
        self.force_password_change = False

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_profile_complete(self) -> bool:
        # regra mínima (ajuste como você quiser)
        if not self.email:
            return False
        if not (self.sector_id or self.setor):
            return False
        if not self.turno:
            return False
        return True

    @property
    def role_label(self) -> str:
        return {
            "staff": "Administrativo",
            "technician": "Técnico",
            "nurse": "Enfermeiro",
            "condutor": "Condutor",
            "manager": "Gerência",
            "admin": "Admin",
        }.get(self.role, self.role)

    def __repr__(self):
        return f"<User {self.matricula} - {self.nome}>"


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def _sync_user_sector(mapper, connection, target: "User"):
    sess = object_session(target)
    if sess is None:
        return

    st = getattr(target, "setor", None)
    sid = getattr(target, "sector_id", None)

    if sid:
        sec = sess.get(Sector, int(sid))
        if sec:
            target.setor = sec.name
        return

    if st:
        sec = sess.query(Sector).filter(Sector.name == st).first()
        if sec:
            target.sector_id = sec.id
