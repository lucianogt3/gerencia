from __future__ import annotations

from datetime import date
import click
from flask import current_app
from sqlalchemy import text

from .extensions import db
from .models.user import User

DEFAULT_BIRTH = date(1990, 1, 1)

ALLOWED_ROLES = {"staff", "technician", "nurse", "manager", "admin"}


@click.command("seed")
def seed_command():
    """Cria/atualiza usuários seed e garante nascimento (NOT NULL)."""
    created = 0
    updated = 0

    # 1) Corrige qualquer registro antigo que esteja com nascimento NULL (defensivo)
    db.session.execute(
        text("UPDATE users SET nascimento = :d WHERE nascimento IS NULL"),
        {"d": DEFAULT_BIRTH.isoformat()},
    )
    db.session.commit()

    def upsert_user(
        matricula: str,
        nome: str,
        email: str | None,
        role: str,
        status: str,
        nascimento: date | None = None,
        password: str = "admin123",
    ):
        nonlocal created, updated

        # blindagem total (nunca deixa None)
        if nascimento is None:
            nascimento = DEFAULT_BIRTH

        if role not in ALLOWED_ROLES:
            role = "staff"

        u = User.query.filter_by(matricula=matricula).first()

        if not u:
            u = User(
                matricula=matricula,
                nome=nome,
                email=email,
                role=role,
                status=status,
                nascimento=nascimento,
            )
            u.set_password(password)
            db.session.add(u)
            created += 1
        else:
            u.nome = nome
            u.email = email
            u.role = role
            u.status = status

            # se tiver vazio, seta
            if u.nascimento is None:
                u.nascimento = nascimento

            updated += 1

        return u

    # Seeds (um em cima do outro)
    upsert_user("9001", "Gerência", "gerencia@local", "manager", "active", date(1989, 3, 26))
    upsert_user("1001", "Colaborador", "colab@local", "staff", "active", date(1995, 1, 1))
    upsert_user("0005", "Colaborador Staff", "staff@local", "staff", "active", date(1990, 1, 1))

    db.session.commit()
    click.echo(f"Seed concluído. Criados: {created} | Atualizados: {updated}")
