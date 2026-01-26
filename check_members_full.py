import sqlite3
from pathlib import Path

SCHEDULE_ID = 1

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

rows = cur.execute("""
select m.schedule_id, m.user_id, u.nome, u.matricula, m.role, m.position, m.active
from nursing_monthly_members m
join users u on u.id = m.user_id
where m.schedule_id=?
order by m.role, m.position
""", (SCHEDULE_ID,)).fetchall()

print("MEMBERS (schedule_id=%s):" % SCHEDULE_ID)
print("TOTAL:", len(rows))
for r in rows:
    print(r)
