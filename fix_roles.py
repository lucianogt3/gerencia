import sqlite3
from pathlib import Path

db = Path("instance") / "app.db"
con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("update nursing_monthly_members set role='nurse' where role='enfermeiro'")
cur.execute("update nursing_monthly_members set role='technician' where role='tecnico'")
con.commit()

print("OK: roles corrigidos.")
