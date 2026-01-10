from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Optional, Length

class DocumentUploadForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(max=200)])
    tipo = SelectField("Tipo", choices=[
        ("POP", "POP"),
        ("Protocolo", "Protocolo"),
        ("Politica", "Política"),
        ("Checklist", "Checklist"),
    ], validators=[DataRequired()])
    setor = StringField("Setor (opcional)", validators=[Optional(), Length(max=80)])
    tags = StringField("Tags (opcional)", validators=[Optional(), Length(max=200)])
    arquivo = FileField("Arquivo (PDF recomendado)", validators=[DataRequired()])
    submit = SubmitField("Enviar")
