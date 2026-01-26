from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

target = 254  # linha do erro do traceback
idx = target - 1

if idx < 0 or idx >= len(lines):
    print("ERRO: linha fora do arquivo, não achei.")
    raise SystemExit(1)

print("REMOVENDO:", lines[idx].rstrip("\n"))
lines.pop(idx)

p.write_text("".join(lines), encoding="utf-8")
print("OK: linha removida.")
