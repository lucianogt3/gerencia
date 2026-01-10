from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Optional, Email

class LoginForm(FlaskForm):
    matricula_or_email = StringField("Matrícula ou E-mail", validators=[DataRequired(), Length(min=3, max=180)])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=4, max=128)])
    submit = SubmitField("Entrar")

class RegisterForm(FlaskForm):
    matricula = StringField("Matrícula/ID", validators=[DataRequired(), Length(min=2, max=32)])
    nome = StringField("Nome", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("E-mail (opcional)", validators=[Optional(), Email(), Length(max=180)])
    setor = StringField("Setor (opcional)", validators=[Optional(), Length(max=80)])
    turno = SelectField("Turno (opcional)", choices=[("", "—"), ("Diurno", "Diurno"), ("Noturno", "Noturno")])
    nascimento = DateField("Nascimento (opcional)", validators=[Optional()])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Solicitar acesso")
