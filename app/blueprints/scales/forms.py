from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime

# ✅ IMPORTAÇÃO ABSOLUTA (CORRETA)
# Não use "from ...models", use "from app.models"
# (Neste arquivo simples nem estamos importando models, mas fica a dica)

class ScaleUploadForm(FlaskForm):
    categoria = SelectField("Categoria", choices=[
        ("Enfermagem", "Enfermagem"),
        ("Medica", "Médica"),
        ("Multidisciplinar", "Multidisciplinar"),
        ("Apoio", "Apoio")
    ], validators=[DataRequired()])
    
    servico = StringField("Serviço / Unidade", validators=[DataRequired()], render_kw={"placeholder": "Ex: UTI Adulto..."})
    setor = StringField("Setor (Opcional)", render_kw={"placeholder": "Ex: Ala B"})
    
    mes = SelectField("Mês", choices=[(str(i), str(i)) for i in range(1, 13)], validators=[DataRequired()], default=str(datetime.now().month))
    ano = IntegerField("Ano", validators=[DataRequired()], default=datetime.now().year)
    
    arquivo = FileField("Arquivo", validators=[
        FileRequired(),
        FileAllowed(['pdf', 'png', 'jpg', 'jpeg', 'xlsx'], 'Apenas PDF, Excel ou Imagens!')
    ])
    
    submit = SubmitField("Publicar")