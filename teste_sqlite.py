import sqlite3
p = r"C:\Users\Luciano Lino Pereira\Desktop\nurse_manager_portal\instance\app.db"
con = sqlite3.connect(p)
con.execute("select 1")
con.close()
print("OK abriu SQLite")
