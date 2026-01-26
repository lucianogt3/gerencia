import re
from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# vamos inserir matricula e aliases no member_rows.append({...})
pattern = r'("name":\s*getattr\(u,\s*"nome",\s*None\)\s*if\s*u\s*else\s*f"User\s*\{m\.user_id\}",\s*)'

if not re.search(pattern, txt):
    print("Não achei o campo name do member_rows.append. Vou tentar localizar por 'member_rows.append({' manualmente.")
    raise SystemExit(1)

replacement = r'''\1
            "nome": getattr(u, "nome", None) if u else f"User {m.user_id}",
            "user_name": getattr(u, "nome", None) if u else f"User {m.user_id}",
            "label": getattr(u, "nome", None) if u else f"User {m.user_id}",
            "matricula": getattr(u, "matricula", None) if u else None,
'''

txt2 = re.sub(pattern, replacement, txt, count=1)

p.write_text(txt2, encoding="utf-8")
print("OK: get_monthly agora envia aliases (nome/user_name/label/matricula).")
