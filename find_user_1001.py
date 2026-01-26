import sqlite3
from pathlib import Path

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

# tenta achar por matricula = '1001'
try:
    rows = cur.execute("select id, nome, matricula, sector_id, status, role from users where matricula = '1001'").fetchall()
    print("USERS com matricula=1001:", rows)
except Exception as e:
    print("Erro tabela users:", e)
