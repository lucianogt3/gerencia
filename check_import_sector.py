import sqlite3
from pathlib import Path

db = Path("instance")/"app.db"
con = sqlite3.connect(db)
cur = con.cursor()

def table_exists(name):
    r = cur.execute("select name from sqlite_master where type='table' and name=?", (name,)).fetchone()
    return bool(r)

print("DB:", db)

# descobrir nomes reais das tabelas
tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name").fetchall()]
print("TABELAS:", tables)

# tenta resolver nomes de tabela
users_table = "users" if table_exists("users") else None
sectors_table = "sectors" if table_exists("sectors") else None

print("\nSETORES:")
if sectors_table:
    for r in cur.execute("select id, name, active from sectors order by id").fetchall():
        print(r)
else:
    print("Tabela sectors não encontrada.")

print("\nUSUÁRIOS ATIVOS POR SETOR:")
if users_table:
    for r in cur.execute("select sector_id, count(*) from users where status='active' group by sector_id order by sector_id").fetchall():
        print(r)
else:
    print("Tabela users não encontrada.")

print("\nATIVOS DO SETOR 1:")
if users_table:
    rows = cur.execute("""
        select id, nome, matricula, sector_id, role, status
        from users
        where status='active' and sector_id=1
        order by nome
    """).fetchall()
    print("TOTAL:", len(rows))
    for r in rows:
        print(r)
else:
    print("Tabela users não encontrada.")
