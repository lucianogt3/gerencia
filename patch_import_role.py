import re
from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# troca a regra antiga do import_sector que cria 'enfermeiro'/'tecnico'
txt2 = txt

# substitui QUALQUER linha que tenha role = "enfermeiro" ... else "tecnico"
txt2 = re.sub(
    r'role\s*=\s*"enfermeiro"\s*if\s*u_role\s*in\s*\([^\)]*\)\s*else\s*"tecnico"',
    'role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"',
    txt2
)

# se não encontrou, tenta substituir o else/if manual mais simples
if txt2 == txt:
    txt2 = txt2.replace(
        'role = "enfermeiro" if u_role in ("nurse", "enfermeiro") else "tecnico"',
        'role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"'
    )

p.write_text(txt2, encoding="utf-8")
print("OK: import_sector agora usa nurse/technician.")
