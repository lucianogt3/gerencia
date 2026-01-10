from __future__ import annotations
from datetime import datetime
from ...extensions import db
from ...models.document import DocumentRead

def register_open(document_id: int, user_id: int) -> None:
    rec = DocumentRead.query.filter_by(document_id=document_id, user_id=user_id).first()
    now = datetime.utcnow()
    if not rec:
        rec = DocumentRead(document_id=document_id, user_id=user_id, first_opened_at=now, last_opened_at=now, open_count=1)
        db.session.add(rec)
    else:
        rec.last_opened_at = now
        rec.open_count = (rec.open_count or 0) + 1
    db.session.commit()
