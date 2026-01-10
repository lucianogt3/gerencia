from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class ScaleUploadForm(FlaskForm):
    categoria = SelectField("Categoria", choices=[("Enfermagem","Enfermagem"),("Medica","Médica")], validators=[DataRequired()])
    servico = StringField("Serviço (ex: Cardiologia)", validators=[DataRequired(), Length(max=80)])
    setor = StringField("Setor (opcional)", validators=[Optional(), Length(max=80)])

    ano = IntegerField("Ano", validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    mes = SelectField("Mês", choices=[(str(i), str(i)) for i in range(1,13)], validators=[DataRequired()])

    arquivo = FileField("Arquivo (PDF recomendado)", validators=[DataRequired()])
    submit = SubmitField("Salvar")
