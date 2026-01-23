from app.extensions import db
from app.models.document import DocumentRead
from datetime import datetime

def register_open(document_id, user_id):
    read = DocumentRead.query.filter_by(document_id=document_id, user_id=user_id).first()
    if not read:
        read = DocumentRead(document_id=document_id, user_id=user_id, open_count=1)
        db.session.add(read)
    else:
        read.open_count += 1
        read.last_read_at = datetime.utcnow()
    
    db.session.commit()