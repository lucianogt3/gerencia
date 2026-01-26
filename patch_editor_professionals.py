from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# troca o bloco professionals.append({ ... }) inteiro
pattern = r"professionals\.append\(\{\s*.*?\s*\}\)\s*"
replacement = """professionals.append({
            "user_id": u.id,                      # <- era "id"
            "id": u.id,                           # mantém compatibilidade se algum JS usa id
            "name": name,
            "role": m.role,
            "role_label": ("Enfermeiro" if m.role == "nurse" else "Técnico"),
            "position": m.position,
            "matricula": matricula,
            "turno": getattr(u, "turno", None),
        })
"""

txt2, n = re.subn(pattern, replacement, txt, flags=re.S)
p.write_text(txt2, encoding="utf-8")
print("OK: editor_view professionals.append patch aplicado:", n)
