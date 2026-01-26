import re
from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# 1) Dentro do import_sector: após pegar u_role, pular admin/manager
# Vamos inserir logo depois da linha u_role = ...
txt = re.sub(
    r'(u_role\s*=\s*\(getattr\(u,\s*"role",\s*""\)\s*or\s*""\)\.lower\(\)\s*\n)',
    r'\1        if u_role in ("admin", "manager"):\n            skipped += 1\n            continue\n',
    txt
)

# 2) Garantir que o role da member sempre seja nurse/technician (você já patchou, mas garantimos)
txt = txt.replace(
    'role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"',
    'role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"'
)

# 3) No add_user_auto: bloquear admin/manager também (antes de criar member_role)
txt = re.sub(
    r'(member_role\s*=\s*"nurse"\s*if\s*u_role\s*in\s*\("nurse",\s*"enfermeiro"\)\s*else\s*"technician")',
    r'if u_role in ("admin", "manager"):\n        return jsonify({"error": "Não é possível adicionar admin/gerência na escala."}), 400\n\n    \1',
    txt
)

p.write_text(txt, encoding="utf-8")
print("OK: import_sector e add_user_auto protegidos (sem admin/manager).")
