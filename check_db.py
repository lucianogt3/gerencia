import sqlite3

db = r"C:\Users\Luciano Lino Pereira\Desktop\nurse_manager_portal\instance\app.db"
con = sqlite3.connect(db)
cur = con.cursor()

try:
    cur.execute("ALTER TABLE sick_notes ADD COLUMN cid VARCHAR(20);")
    con.commit()
    print("OK: coluna cid adicionada em sick_notes")
except sqlite3.OperationalError as e:
    # se já existir, fica ok
    if "duplicate column name" in str(e).lower():
        print("OK: coluna cid já existia em sick_notes")
    else:
        raise
finally:
    con.close()
