import sqlite3
from pathlib import Path

SCHEDULE_ID = 1

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

# 1) Ajusta role do MEMBER conforme role do USER
# nurse/enfermeiro -> nurse
# staff/technician/tecnico -> technician
# admin/manager -> remove da escala (não faz sentido entrar como colaborador)
members = cur.execute("""
select m.user_id, u.role
from nursing_monthly_members m
join users u on u.id = m.user_id
where m.schedule_id=?
""", (SCHEDULE_ID,)).fetchall()

removed = 0
updated = 0

for user_id, urole in members:
    urole = (urole or "").lower()

    if urole in ("admin", "manager"):
        cur.execute("delete from nursing_monthly_members where schedule_id=? and user_id=?", (SCHEDULE_ID, user_id))
        removed += 1
        continue

    new_role = "nurse" if urole in ("nurse", "enfermeiro") else "technician"
    cur.execute("""
        update nursing_monthly_members
        set role=?
        where schedule_id=? and user_id=?
    """, (new_role, SCHEDULE_ID, user_id))
    updated += 1

con.commit()

print("OK")
print("Atualizados:", updated)
print("Removidos(admin/manager):", removed)

# 2) Mostra como ficou
rows = cur.execute("""
select m.schedule_id, m.user_id, u.nome, u.matricula, m.role, m.position, m.active
from nursing_monthly_members m
join users u on u.id = m.user_id
where m.schedule_id=?
order by m.role, m.position
""", (SCHEDULE_ID,)).fetchall()

print("\nMEMBERS FINAL:")
for r in rows:
    print(r)
