from pathlib import Path
import re

ROOT = Path(".")
api_route = ROOT / r"app\blueprints\nursing\nursing_api\route.py"
routes_py = ROOT / r"app\blueprints\nursing\routes.py"

def fix_future_import_at_top(p: Path):
    if not p.exists():
        print(f"SKIP: {p} não existe.")
        return

    s = p.read_text(encoding="utf-8")

    target = "from __future__ import annotations"
    if target not in s:
        print(f"OK: {p} não tem __future__.")
        return

    lines = s.splitlines(True)

    # remove todas ocorrências (pra evitar duplicar)
    new_lines = [ln for ln in lines if target not in ln]

    # preserva shebang/encoding se existirem (primeiras 2 linhas típicas)
    head = []
    rest = new_lines[:]

    if rest and rest[0].startswith("#!"):
        head.append(rest.pop(0))
    if rest and re.match(r"^#.*coding[:=]\s*[-\w.]+", rest[0]):
        head.append(rest.pop(0))

    # remove linhas vazias no topo do resto
    while rest and rest[0].strip() == "":
        rest.pop(0)

    # monta arquivo final
    out = []
    out.extend(head)
    out.append(target + "\n")
    out.append("\n")
    out.extend(rest)

    p.write_text("".join(out), encoding="utf-8")
    print(f"OK: movido '__future__' para o topo em {p}")

def fix_stray_continue_in_routes(p: Path):
    if not p.exists():
        print(f"SKIP: {p} não existe.")
        return

    s = p.read_text(encoding="utf-8")
    # detecta "continue" com indentação que não está dentro de loop:
    # (isso é heuristic, mas resolve o seu caso: continue alinhado no nível do def/import)
    # remove 'continue' com 4 ou 8 espaços se estiver entre "for" e nada? — aqui vamos atacar o erro que você viu.
    # Melhor: remover linhas "continue" que aparecem dentro de uma função mas fora de bloco:
    # Pra não fazer besteira, só remove quando há um "return jsonify(...admin/manager...)" imediatamente antes e 'continue' logo abaixo.
    pat = re.compile(r"(?m)^\s*return\s+jsonify\([^\n]*admin/manager[^\n]*\)\s*,\s*400\s*\n\s*continue\s*\n")
    s2, n = pat.subn(lambda m: m.group(0).replace("\ncontinue\n", "\n"), s)

    if n:
        p.write_text(s2, encoding="utf-8")
        print(f"OK: removido(s) {n} bloco(s) 'return ... 400' + 'continue' inválido(s) em {p}")
    else:
        print(f"OK: nenhum 'continue' inválido encontrado em {p}")

fix_future_import_at_top(api_route)
fix_stray_continue_in_routes(routes_py)

print("DONE")
