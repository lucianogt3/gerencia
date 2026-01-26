from pathlib import Path

root = Path("app")
count = 0

for f in root.rglob("*.py"):
    txt = f.read_text(encoding="utf-8", errors="ignore")
    if "from __future__ import annotations" not in txt:
        continue

    lines = txt.splitlines()

    # remove todas ocorrências
    lines = [l for l in lines if l.strip() != "from __future__ import annotations"]

    # reinsere no topo (linha 1)
    lines.insert(0, "from __future__ import annotations")

    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    count += 1

print(f"OK: __future__ imports corrigidos em {count} arquivo(s).")
