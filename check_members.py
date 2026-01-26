import sqlite3
from pathlib import Path

SCHEDULE_ID = 1

db = Path("instance") / "app.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("MEMBERS DA ESCALA (schedule_id=1):")
rows = cur.execute(
    "select schedule_id, user_id, role, position, active from nursing_monthly_members where schedule_id = ? order by role, position",
    (SCHEDULE_ID,)
).fetchall()

print("TOTAL:", len(rows))
for r in rows:
    print(r)
