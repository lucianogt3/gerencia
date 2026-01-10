from __future__ import annotations
from datetime import datetime
from ..extensions import db

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(20), default="info", nullable=False)  # info/alert/urgent

    setor = db.Column(db.String(80), nullable=True)  # null => todos
    image_filename = db.Column(db.String(255), nullable=True)
    image_original_name = db.Column(db.String(255), nullable=True)

    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    pinned_until = db.Column(db.DateTime, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
