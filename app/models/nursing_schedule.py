from __future__ import annotations
from datetime import datetime, date
from ..extensions import db

# Turnos aceitos
SHIFT_CHOICES = ("D", "N", "M", "T", "MT")

# Status do dia (escala diária)
DAY_STATUS = (
    "OK",                 # veio conforme escala
    "FALTA_NJ",           # falta não justificada
    "FALTA_J",            # falta justificada (se você quiser usar)
    "ATESTADO_PEND",      # colaborador enviou, aguardando gestor
    "ATESTADO_OK",        # gestor aprovou
    "REMANEJADO",         # veio de outro setor
    "EXTRA",              # cobertura extra
    "FOLGA_COMP",         # cobertura por folga compensatória
)

class NursingMonthlySchedule(db.Model):
    """
    Escala mensal de Enfermagem (grade).
    Ex.: UTI 1, Janeiro/2026.
    """
    __tablename__ = "nursing_monthly_schedules"

    id = db.Column(db.Integer, primary_key=True)

    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)  # 1-12

    # draft -> editável; published -> equipe visualiza; archived -> histórico
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    published_at = db.Column(db.DateTime, nullable=True)
    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

class NursingMonthlyMember(db.Model):
    """
    Quem está na escala mensal e em qual 'posição' (para preencher grade).
    Ex.: ENF 1, TEC 1..6.
    """
    __tablename__ = "nursing_monthly_members"

    id = db.Column(db.Integer, primary_key=True)

    schedule_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_schedules.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # enfermeiro / tecnico / fisioterapeuta (se quiser expandir depois)
    role = db.Column(db.String(20), nullable=False, index=True)

    # posição visual na grade (ex: TEC 1..6; ENF 1..2)
    position = db.Column(db.Integer, nullable=False, index=True)

    active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("schedule_id", "role", "position", name="uq_member_slot"),
        db.UniqueConstraint("schedule_id", "user_id", name="uq_member_user"),
    )

class NursingMonthlyCell(db.Model):
    """
    Célula da grade mensal: qual membro está escalado em um dia específico e turno.
    Ex.: dia 10, turno D, TEC 3 = user X.
    """
    __tablename__ = "nursing_monthly_cells"

    id = db.Column(db.Integer, primary_key=True)

    schedule_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_schedules.id"), nullable=False, index=True)
    day = db.Column(db.Integer, nullable=False, index=True)      # 1..31
    shift = db.Column(db.String(3), nullable=False, index=True)  # D/N/M/T/MT

    role = db.Column(db.String(20), nullable=False, index=True)  # tecnico/enfermeiro
    position = db.Column(db.Integer, nullable=False, index=True)

    planned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("schedule_id", "day", "shift", "role", "position", name="uq_monthly_cell"),
    )

class NursingDailyOverride(db.Model):
    """
    O que aconteceu de verdade no dia (override da escala mensal).
    Se existir registro aqui, ele manda na escala diária.
    """
    __tablename__ = "nursing_daily_overrides"

    id = db.Column(db.Integer, primary_key=True)

    schedule_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_schedules.id"), nullable=False, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False, index=True)

    date = db.Column(db.Date, nullable=False, index=True)
    shift = db.Column(db.String(3), nullable=False, index=True)  # D/N/M/T/MT

    role = db.Column(db.String(20), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, index=True)

    planned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    actual_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    status = db.Column(db.String(20), default="OK", nullable=False, index=True)

    # remanejamento
    from_sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=True)

    # extra/folga
    extra_type = db.Column(db.String(10), nullable=True)   # "EXTRA" | "FOLGA"
    comp_day = db.Column(db.Date, nullable=True)           # se folga, dia da folga compensatória

    notes = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("sector_id", "date", "shift", "role", "position", name="uq_daily_override"),
    )
