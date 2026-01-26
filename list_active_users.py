import sqlite3
from pathlib import Path

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

rows = cur.execute("""
select id, nome, matricula, sector_id, role, status
from users
where status='active'
order by sector_id, nome
""").fetchall()

for r in rows:
    print(r)
