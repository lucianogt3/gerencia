from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, TextAreaField
from wtforms.validators import NumberRange, Optional

SHIFT_CHOICES = [
    ("D", "Diurno (D)"),
    ("N", "Noturno (N)"),
]

def _int_field(label: str) -> IntegerField:
    return IntegerField(label, validators=[Optional(), NumberRange(min=0)], default=0)

class IndicatorForm(FlaskForm):
    # Turno do lançamento (D/N)
    shift = SelectField("Turno", choices=SHIFT_CHOICES, default="D")

    # Itens do formulário (conforme lista validada)
    lpp_total = _int_field("LPP total")
    lpp_admitidos = _int_field("LPP admitidos")
    lpp_novos = _int_field("LPP novos")

    svd_total = _int_field("SVD total")
    sne_gtt_total = _int_field("SNE/GTT total")
    perda_sne_gtt = _int_field("Perda SNE/GTT")

    cvc_cdl_total = _int_field("CVC/CDL total")
    perda_cvc_cdl = _int_field("Perda CVC/CDL")

    avp_total = _int_field("AVP total")

    flebite_infeccao_cvc_cdl = _int_field("Flebite/Infecção CVC/CDL")

    quedas = _int_field("Quedas")
    erros_med = _int_field("Erros medicação")
    faltou_kit_medicacao = _int_field("Falta kit/medicação")

    pulseira_ok = _int_field("Pulseira OK")
    identificacao_incorreta = _int_field("Identificação incorreta")

    encaminhado_uti = _int_field("Encaminhado UTI")
    paradas = _int_field("Paradas")
    obitos = _int_field("Óbitos")

    observacoes = TextAreaField("Observações", validators=[Optional()])
