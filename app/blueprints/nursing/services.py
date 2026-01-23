from app.extensions import db
from app.models import NursingMonthlySchedule, NursingMonthlyCell, NursingDailyOverride
from datetime import datetime

def sync_monthly_to_daily(sector_id, date_obj):
    schedule = NursingMonthlySchedule.query.filter_by(
        sector_id=sector_id,
        year=date_obj.year,
        month=date_obj.month,
        status="published"
    ).first()

    if not schedule:
        return False, "Escala mensal não publicada."

    planned_cells = NursingMonthlyCell.query.filter_by(
        schedule_id=schedule.id,
        day=date_obj.day
    ).all()

    for cell in planned_cells:
        if not cell.planned_user_id: continue
        
        exists = NursingDailyOverride.query.filter_by(
            user_id=cell.planned_user_id,
            date=date_obj,
            shift=cell.shift
        ).first()

        if not exists:
            db.session.add(NursingDailyOverride(
                user_id=cell.planned_user_id,
                date=date_obj,
                shift=cell.shift,
                sector_id=sector_id,
                status="OK"
            ))
    db.session.commit()
    return True, "Sincronizado."
