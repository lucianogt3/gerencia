from __future__ import annotations
import click
from flask import Flask
from .extensions import db
from .models.user import User

def register_seed_command(app: Flask):
    @app.cli.command("seed")
    def seed():
        """Cria usuários de teste (gerência + colaborador)."""
        created = 0

        def upsert_user(matricula, nome, email, role, status):
            nonlocal created
            u = User.query.filter_by(matricula=matricula).first()
            if not u:
                u = User(matricula=matricula, nome=nome, email=email, role=role, status=status)
                u.set_password("admin123")
                db.session.add(u)
                created += 1
            else:
                u.nome = nome
                u.email = email
                u.role = role
                u.status = status
            return u

        upsert_user("9001", "Gerência", "gerencia@local", "manager", "active")
        upsert_user("1001", "Colaborador", "colab@local", "staff", "active")

        db.session.commit()
        click.echo(f"Seed concluído. Usuários criados/atualizados: {created}")
