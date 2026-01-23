from __future__ import annotations
from datetime import datetime
from app.extensions import db

# Nota: Não importamos User ou Sector aqui para evitar Circular Import.

class NursingMonthlySchedule(db.Model):
    __tablename__ = "nursing_monthly_schedule"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), default="draft")
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sector = db.relationship("Sector", backref="nursing_schedules")
    members = db.relationship("NursingMonthlyMember", backref="schedule", lazy="dynamic", cascade="all, delete-orphan")
    cells = db.relationship("NursingMonthlyCell", backref="schedule", lazy="dynamic", cascade="all, delete-orphan")

class NursingMonthlyMember(db.Model):
    __tablename__ = "nursing_monthly_member"
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_schedule.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), nullable=True)
    active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)
    user = db.relationship("User", backref="nursing_memberships")

class NursingMonthlyCell(db.Model):
    __tablename__ = "nursing_monthly_cell"
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_schedule.id"), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    planned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey("nursing_monthly_member.id"), nullable=True)
    shift = db.Column(db.String(10), nullable=True)
    code = db.Column(db.String(10), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NursingDailyOverride(db.Model):
    """
    Tabela para armazenar trocas pontuais, atestados, extras e COOPERATIVA.
    """
    __tablename__ = "nursing_daily_override"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    code = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # --- CAMPO NOVO: TURNO ---
    shift = db.Column(db.String(5), nullable=True) # D ou N

    # --- COOPERATIVA ---
    is_coop = db.Column(db.Boolean, default=False)
    coop_name = db.Column(db.String(150))
    coop_coren = db.Column(db.String(50))
    coop_role = db.Column(db.String(50))
    
    related_date = db.Column(db.Date, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="daily_overrides")