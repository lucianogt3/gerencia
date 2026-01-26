import sqlite3
from pathlib import Path

db = Path("instance") / "app.db"
con = sqlite3.connect(db)
cur = con.cursor()

print("DB:", db.resolve())
tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table'").fetchall()]
print("tables:", tables)
