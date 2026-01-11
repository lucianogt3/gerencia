from datetime import datetime
from ..extensions import db

class AnnouncementRead(db.Model):
    __tablename__ = "announcement_reads"
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user"),
    )
