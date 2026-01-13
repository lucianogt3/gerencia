from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, NursingMonthlySchedule, NursingMonthlyMember

bp = Blueprint("nursing_api", __name__, url_prefix="/api/nursing")

def _require_manager() -> bool:
    return getattr(current_user, "role", "") in ("manager", "admin")

@bp.post("/monthly/<int:schedule_id>/import_sector")
@login_required
def import_sector(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get(schedule_id)
    if not sched:
        return jsonify({"error": "Escala não encontrada"}), 404

    data = request.get_json(silent=True) or {}
    auto_fill = bool(data.get("auto_fill", True))

    sector_id = sched.sector_id

    q = User.query

    # ajuste conforme seu model:
    if hasattr(User, "status"):
        q = q.filter(User.status == "active")

    if hasattr(User, "sector_id"):
        q = q.filter(User.sector_id == sector_id)

    q = q.order_by(User.nome.asc())
    users = q.all()

    added = 0
    for u in users:
        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
        if exists:
            continue
        db.session.add(NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=u.id,
            role=getattr(u, "role", "staff"),
            position=9999,
            active=True
        ))
        added += 1

        # TODO: aqui entra sua regra de auto_fill (par/ímpar, diurno/noturno)

    db.session.commit()
    return jsonify({"ok": True, "added": added, "auto_fill": auto_fill})
