from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# remove "continue" no nível do corpo da função (4 espaços)
txt2, n = re.subn(r"(?m)^\s{4}continue\s*\n", "", txt)

p.write_text(txt2, encoding="utf-8")
print(f"OK: removidos {n} continue(s) inválidos (indent 4 espaços).")
