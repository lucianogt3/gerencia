from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# remove o bloco errado dentro do transfer:
#   if u_role in ("admin","manager"):
#       skipped += 1
#       continue
txt2 = re.sub(
    r"\n\s*if\s+u_role\s+in\s+\(\"admin\",\s*\"manager\"\):\s*\n\s*skipped\s*\+=\s*1\s*\n\s*continue\s*\n",
    "\n",
    txt,
    flags=re.M
)

# agora injeta a validação correta logo após u_role = ...
def repl(m):
    base = m.group(0)
    guard = "\n\n    # admins/manager não entram como membro de escala\n    if u_role in (\"admin\", \"manager\"):\n        return jsonify({\"error\": \"Usuário admin/manager não pode ser adicionado à escala\"}), 400"
    return base + guard

txt3 = re.sub(
    r"^\s*u_role\s*=\s*\(getattr\(u,\s*\"role\",\s*\"\"\)\s*or\s*\"\"\)\.lower\(\)\s*$",
    repl,
    txt2,
    flags=re.M
)

p.write_text(txt3, encoding="utf-8")
print("OK: bloco inválido removido e validação inserida no transfer().")
