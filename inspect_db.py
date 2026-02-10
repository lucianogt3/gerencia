import sqlite3
from pathlib import Path

db_path = Path("instance") / "app.db"
print("DB:", db_path.resolve())

con = sqlite3.connect(db_path)
tables = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' order by name;"
)]
print("Tabelas:", tables)

if "alembic_version" in tables:
    ver = con.execute("select version_num from alembic_version").fetchone()
    print("alembic_version:", ver[0] if ver else None)
else:
    print("Sem alembic_version (migrations nunca aplicadas nesse arquivo).")

con.close()
