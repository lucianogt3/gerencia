import sqlite3
from pathlib import Path

MATRICULA = "1001"
NEW_SECTOR_ID = 1

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

u = cur.execute("select id, nome, matricula, sector_id from users where matricula=?", (MATRICULA,)).fetchone()
if not u:
    print("Não achei matrícula", MATRICULA)
    raise SystemExit

sec = cur.execute("select name from sectors where id=?", (NEW_SECTOR_ID,)).fetchone()
sec_name = sec[0] if sec else None

cur.execute("update users set sector_id=? where matricula=?", (NEW_SECTOR_ID, MATRICULA))

# se existir coluna texto 'setor', atualiza também
cols = [c[1] for c in cur.execute("pragma table_info(users)").fetchall()]
if "setor" in cols and sec_name:
    cur.execute("update users set setor=? where matricula=?", (sec_name, MATRICULA))

con.commit()
print("OK:", u, "-> sector_id =", NEW_SECTOR_ID, sec_name)
