from __future__ import annotations

from datetime import date
from app.extensions import db

class IndicatorDaily(db.Model):
    __tablename__ = "indicator_daily"

    id = db.Column(db.Integer, primary_key=True)

    ref_date = db.Column(db.Date, nullable=False, index=True)
    unit = db.Column(db.String(120), nullable=False, index=True)
    shift = db.Column(db.String(1), nullable=False, index=True)  # 'D' ou 'N'

    # Itens (inteiros, default 0)
    lpp_total = db.Column(db.Integer, default=0)
    lpp_admitidos = db.Column(db.Integer, default=0)
    lpp_novos = db.Column(db.Integer, default=0)

    svd_total = db.Column(db.Integer, default=0)
    sne_gtt_total = db.Column(db.Integer, default=0)
    perda_sne_gtt = db.Column(db.Integer, default=0)

    cvc_cdl_total = db.Column(db.Integer, default=0)
    perda_cvc_cdl = db.Column(db.Integer, default=0)

    avp_total = db.Column(db.Integer, default=0)

    flebite_infeccao_cvc_cdl = db.Column(db.Integer, default=0)

    quedas = db.Column(db.Integer, default=0)
    erros_med = db.Column(db.Integer, default=0)
    faltou_kit_medicacao = db.Column(db.Integer, default=0)

    pulseira_ok = db.Column(db.Integer, default=0)
    identificacao_incorreta = db.Column(db.Integer, default=0)

    encaminhado_uti = db.Column(db.Integer, default=0)
    paradas = db.Column(db.Integer, default=0)
    obitos = db.Column(db.Integer, default=0)

    observacoes = db.Column(db.Text)

    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("ref_date", "unit", "shift", name="uq_indicator_daily_ref_unit_shift"),
    )

    def from_form(self, form) -> None:
        # Inteiros
        for attr in [
            "lpp_total","lpp_admitidos","lpp_novos",
            "svd_total","sne_gtt_total","perda_sne_gtt",
            "cvc_cdl_total","perda_cvc_cdl",
            "avp_total",
            "flebite_infeccao_cvc_cdl",
            "quedas","erros_med","faltou_kit_medicacao",
            "pulseira_ok","identificacao_incorreta",
            "encaminhado_uti","paradas","obitos",
        ]:
            setattr(self, attr, int(getattr(form, attr).data or 0))

        self.observacoes = (form.observacoes.data or "").strip()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ref_date": self.ref_date.isoformat() if isinstance(self.ref_date, date) else None,
            "unit": self.unit,
            "shift": self.shift,
            "lpp_total": self.lpp_total or 0,
            "lpp_admitidos": self.lpp_admitidos or 0,
            "lpp_novos": self.lpp_novos or 0,
            "svd_total": self.svd_total or 0,
            "sne_gtt_total": self.sne_gtt_total or 0,
            "perda_sne_gtt": self.perda_sne_gtt or 0,
            "cvc_cdl_total": self.cvc_cdl_total or 0,
            "perda_cvc_cdl": self.perda_cvc_cdl or 0,
            "avp_total": self.avp_total or 0,
            "flebite_infeccao_cvc_cdl": self.flebite_infeccao_cvc_cdl or 0,
            "quedas": self.quedas or 0,
            "erros_med": self.erros_med or 0,
            "faltou_kit_medicacao": self.faltou_kit_medicacao or 0,
            "pulseira_ok": self.pulseira_ok or 0,
            "identificacao_incorreta": self.identificacao_incorreta or 0,
            "encaminhado_uti": self.encaminhado_uti or 0,
            "paradas": self.paradas or 0,
            "obitos": self.obitos or 0,
            "observacoes": self.observacoes or "",
            "created_by": self.created_by,
        }
