from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Optional, Email, ValidationError

from app.models import User


class LoginForm(FlaskForm):
    matricula_or_email = StringField(
        "Matrícula ou E-mail",
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=3, max=180, message="Deve ter entre 3 e 180 caracteres"),
        ],
    )

    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=4, max=128, message="Deve ter entre 4 e 128 caracteres"),
        ],
    )

    submit = SubmitField("Entrar")


class RegisterForm(FlaskForm):
    # ⚠️ MATRÍCULA REMOVIDA DO FORM (GERADA AUTOMATICAMENTE PELO SISTEMA)

    nome = StringField(
        "Nome Completo",
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=2, max=120, message="Deve ter entre 2 e 120 caracteres"),
        ],
    )

    email = StringField(
        "E-mail (opcional)",
        validators=[
            Optional(),
            Email(message="Digite um e-mail válido"),
            Length(max=180, message="Máximo de 180 caracteres"),
        ],
    )

    setor = SelectField(
        "Setor",
        choices=[],  # preenchido dinamicamente na rota
        validators=[Optional()],
    )

    turno = SelectField(
        "Turno",
        choices=[
            ("", "— Selecione —"),
            ("Diurno", "Diurno"),
            ("Noturno", "Noturno"),
        ],
        validators=[Optional()],
    )

    # ✅ NOVO: Cargo / Role
    role = SelectField(
        "Cargo",
        choices=[
            ("", "— Selecione —"),
            ("staff", "Administrativo"),
            ("technician", "Técnico"),
            ("nurse", "Enfermeiro"),
        ],
        validators=[DataRequired(message="Selecione o cargo.")],
    )

    # ✅ Ajuste: Nascimento é obrigatório de verdade
    nascimento = DateField(
        "Data de Nascimento",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Campo obrigatório")],
    )

    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=6, max=128, message="Deve ter entre 6 e 128 caracteres"),
        ],
    )

    submit = SubmitField("Solicitar acesso")

    def validate_email(self, field):
        """Valida se o e-mail já está cadastrado (se informado)"""
        email = field.data.strip().lower() if field.data else None
        if email and User.query.filter_by(email=email).first():
            raise ValidationError("Este e-mail já está cadastrado.")
