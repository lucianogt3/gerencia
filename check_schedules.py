import sqlite3
from pathlib import Path

db = Path("instance") / "app.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("SCHEDULES (últimos 20):")
rows = cur.execute(
    "select id, sector_id, year, month, status from nursing_monthly_schedules order by id desc limit 20"
).fetchall()

for r in rows:
    print(r)
