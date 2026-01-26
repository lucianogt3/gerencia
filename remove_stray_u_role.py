from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

pat = re.compile(r'^\s+u_role\s*=\s*\(getattr\(u,\s*"role",\s*""\)\s*or\s*""\)\.lower\(\)\s*$')

removed = 0
out = []
for i, line in enumerate(lines):
    if pat.match(line):
        # olha 2 linhas acima para ver se estamos dentro de "for u in users:" ou "for u in"
        prev = "".join(lines[max(0, i-3):i])
        if re.search(r'(?m)^\s*for\s+u\s+in\s+\w+\s*:\s*$', prev) is None:
            removed += 1
            continue
    out.append(line)

p.write_text("".join(out), encoding="utf-8")
print(f"OK: removidas {removed} linha(s) 'u_role = ...' soltas.")
