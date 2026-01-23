from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FileField
from wtforms.validators import DataRequired

class DocumentUploadForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('POP', 'POP'), ('Protocolo', 'Protocolo'), ('Manual', 'Manual')], validators=[DataRequired()])
    arquivo = FileField('Arquivo PDF', validators=[DataRequired()])