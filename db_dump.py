import sqlite3
from pathlib import Path

db = Path("instance") / "app.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("SCHEDULES:")
try:
    rows = cur.execute("select id, sector_id, year, month, status from nursing_monthly_schedule order by id desc").fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print("Erro lendo nursing_monthly_schedule:", e)

print("\nMEMBERS (últimos 50):")
try:
    rows = cur.execute("select schedule_id, user_id, role, position, active from nursing_monthly_member order by schedule_id desc, role, position limit 50").fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print("Erro lendo nursing_monthly_member:", e)
