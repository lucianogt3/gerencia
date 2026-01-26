from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")
lines = txt.splitlines(True)

# Heurística de stack de indentação para saber se estamos dentro de for/while
stack = []  # itens: (indent_level, kind) kind in {"loop","block"}

def leading_spaces(s: str) -> int:
    return len(s) - len(s.lstrip(" "))

def is_block_start(s: str) -> bool:
    s2 = s.strip()
    if not s2 or s2.startswith("#"):
        return False
    # ignora coisas tipo "}" ou ")" etc
    return s2.endswith(":") and not s2.startswith(("return", "pass"))

def block_kind(s: str) -> str:
    s2 = s.strip()
    if s2.startswith("for ") or s2.startswith("while "):
        return "loop"
    return "block"

changed = 0
changed_lines = []

for i, line in enumerate(lines):
    raw = line.rstrip("\n")

    # atualiza stack quando indent diminui
    indent = leading_spaces(raw) if raw.strip() else None
    if indent is not None:
        while stack and indent < stack[-1][0]:
            stack.pop()

    # se essa linha abre bloco (termina com :)
    if is_block_start(raw):
        indent_here = leading_spaces(raw)
        stack.append((indent_here + 4, block_kind(raw)))  # próximo nível esperado

    # detecta continue solto
    if raw.strip() == "continue":
        in_loop = any(k == "loop" for _, k in stack)
        if not in_loop:
            # troca por pass para não deixar bloco vazio
            lines[i] = (" " * leading_spaces(raw)) + "pass  # FIX: stray continue removed\n"
            changed += 1
            changed_lines.append(i + 1)

p.write_text("".join(lines), encoding="utf-8")
print(f"OK: trocados {changed} continue(s) fora de loop por pass.")
if changed_lines:
    print("Linhas ajustadas:", ", ".join(map(str, changed_lines)))
