from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# acha a função import_sector (decorator @bp.post ... import_sector)
m = re.search(r'(?ms)^@bp\.post\("/monthly/<int:schedule_id>/import_sector"\)\s*@login_required\s*def\s+import_sector\s*\(\s*schedule_id\s*:\s*int\s*\)\s*:\s*\n(.*?)(?=^\s*@bp\.|\Z)', txt)
if not m:
    print("ERRO: não achei a função import_sector no routes.py")
    raise SystemExit(1)

old_block = m.group(0)

new_block = r'''@bp.post("/monthly/<int:schedule_id>/import_sector")
@login_required
def import_sector(schedule_id: int):
    _require_manager()

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    sector = Sector.query.get(sched.sector_id)

    data = request.get_json(silent=True) or {}
    auto_fill = bool(data.get("auto_fill", True))

    # pega usuários ativos do setor (ajuste se seu model usa outro campo)
    users = User.query.filter_by(sector_id=sector.id, active=True).order_by(User.nome.asc()).all()

    added = 0
    skipped = 0

    def next_position(role: str) -> int:
        last = (NursingMonthlyMember.query
                .filter_by(schedule_id=sched.id, role=role, active=True)
                .order_by(NursingMonthlyMember.position.desc())
                .first())
        return (last.position + 1) if last else 1

    for u in users:
        u_role = (getattr(u, "role", "") or "").lower()

        # admins/manager não entram como membro de escala
        if u_role in ("admin", "manager"):
            skipped += 1
            continue

        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"

        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id, active=True).first()
        if exists:
            skipped += 1
            continue

        db.session.add(NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=u.id,
            role=role,
            position=next_position(role),
            active=True,
        ))
        added += 1

    db.session.commit()

    # se você tiver auto-fill no backend, chama aqui
    if auto_fill:
        try:
            _auto_fill_month(schedule_id=sched.id)
        except Exception:
            pass

    return jsonify({
        "ok": True,
        "schedule_id": sched.id,
        "sector_id": sched.sector_id,
        "imported": added,
        "skipped": skipped,
        "auto_fill": auto_fill,
    })
'''

txt2 = txt.replace(old_block, new_block)
p.write_text(txt2, encoding="utf-8")
print("OK: import_sector reescrito e indentação corrigida.")
