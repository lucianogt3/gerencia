from __future__ import annotations

from app.extensions import db


class IndicatorDaily(db.Model):
    __tablename__ = "indicator_daily"

    id = db.Column(db.Integer, primary_key=True)

    # Identificação do lançamento
    ref_date = db.Column(db.Date, nullable=False, index=True)
    unit = db.Column(db.String(120), nullable=False, index=True)
    shift = db.Column(db.String(30), nullable=False, index=True)
    created_by = db.Column(db.Integer, nullable=True)

    # Campos (compatíveis com o IndicatorForm atual)
    censo_dia = db.Column(db.Integer, default=0)
    admissoes = db.Column(db.Integer, default=0)
    altas_transferencias = db.Column(db.Integer, default=0)
    obitos = db.Column(db.Integer, default=0)

    quedas_paciente = db.Column(db.Integer, default=0)
    extubacao_acidental = db.Column(db.Integer, default=0)
    novas_lpp = db.Column(db.Integer, default=0)
    erros_medicacao = db.Column(db.Integer, default=0)
    broncoaspiracao = db.Column(db.Integer, default=0)
    parada_cardio = db.Column(db.Integer, default=0)
    reinternacao_24h = db.Column(db.Integer, default=0)

    faltas_tecnicos = db.Column(db.Integer, default=0)
    atestados_equipe = db.Column(db.Integer, default=0)
    horas_extras_geradas = db.Column(db.Float, default=0.0)

    manutencao_equipamento = db.Column(db.Boolean, default=False)
    falta_insumo_critico = db.Column(db.Boolean, default=False)
    exames_pendentes = db.Column(db.Integer, default=0)
    conclusao_prontuarios = db.Column(db.Boolean, default=False)
    conflitos_acompanhantes = db.Column(db.Integer, default=0)

    observacoes = db.Column(db.Text, default="")

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("ref_date", "unit", "shift", name="uq_indicator_daily_ref_unit_shift"),
    )

    @staticmethod
    def _nz_int(v):
        return int(v) if v is not None else 0

    @staticmethod
    def _nz_float(v):
        return float(v) if v is not None else 0.0

    def from_form(self, form):
        # Inteiros
        self.censo_dia = self._nz_int(form.censo_dia.data)
        self.admissoes = self._nz_int(form.admissoes.data)
        self.altas_transferencias = self._nz_int(form.altas_transferencias.data)
        self.obitos = self._nz_int(form.obitos.data)

        self.quedas_paciente = self._nz_int(form.quedas_paciente.data)
        self.extubacao_acidental = self._nz_int(form.extubacao_acidental.data)
        self.novas_lpp = self._nz_int(form.novas_lpp.data)
        self.erros_medicacao = self._nz_int(form.erros_medicacao.data)
        self.broncoaspiracao = self._nz_int(form.broncoaspiracao.data)
        self.parada_cardio = self._nz_int(form.parada_cardio.data)
        self.reinternacao_24h = self._nz_int(form.reinternacao_24h.data)

        self.faltas_tecnicos = self._nz_int(form.faltas_tecnicos.data)
        self.atestados_equipe = self._nz_int(form.atestados_equipe.data)
        self.horas_extras_geradas = self._nz_float(form.horas_extras_geradas.data)

        # Booleans
        self.manutencao_equipamento = bool(form.manutencao_equipamento.data)
        self.falta_insumo_critico = bool(form.falta_insumo_critico.data)
        self.conclusao_prontuarios = bool(form.conclusao_prontuarios.data)

        self.exames_pendentes = self._nz_int(form.exames_pendentes.data)
        self.conflitos_acompanhantes = self._nz_int(form.conflitos_acompanhantes.data)

        self.observacoes = (form.observacoes.data or "").strip()
