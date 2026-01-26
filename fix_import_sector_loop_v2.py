from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# 1) acha a função import_sector
i_def = txt.find("def import_sector")
if i_def < 0:
    print("ERRO: não encontrei 'def import_sector' no routes.py")
    raise SystemExit(1)

# pega só o corpo da função (até próximo '@bp.' ou 'def ' no mesmo nível)
tail = txt[i_def:]
# tenta cortar no próximo decorator de rota
cut = tail.find("\n@bp.")
if cut < 0:
    # fallback: tenta próximo def
    cut = tail.find("\ndef ")
    if cut < 0:
        cut = len(tail)

block = tail[:cut]
rest  = tail[cut:]

# 2) dentro do bloco, acha o for u in users e o db.session.commit
i_for = block.find("for u in users:")
if i_for < 0:
    print("ERRO: não encontrei 'for u in users:' dentro de import_sector")
    raise SystemExit(1)

i_commit = block.find("db.session.commit()", i_for)
if i_commit < 0:
    print("ERRO: não encontrei 'db.session.commit()' após o loop dentro de import_sector")
    raise SystemExit(1)

# 3) monta o loop correto (respeitando indentação do seu arquivo)
# Observação: nesse arquivo, o corpo da função usa 4 espaços.
# O loop fica com 4 espaços; o conteúdo do loop com 8.
new_loop = (
    "    for u in users:\n"
    "        u_role = (getattr(u, \"role\", \"\") or \"\").lower()\n"
    "\n"
    "        # admins/manager não entram como membro de escala\n"
    "        if u_role in (\"admin\", \"manager\"):\n"
    "            skipped += 1\n"
    "            continue\n"
    "\n"
    "        role = \"nurse\" if u_role in (\"nurse\", \"enfermeiro\") else \"technician\"\n"
    "\n"
    "        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()\n"
    "        if exists:\n"
    "            skipped += 1\n"
    "            continue\n"
    "\n"
    "        db.session.add(NursingMonthlyMember(\n"
    "            schedule_id=sched.id,\n"
    "            user_id=u.id,\n"
    "            role=role,\n"
    "            position=next_position(role),\n"
    "            active=True,\n"
    "        ))\n"
    "        added += 1\n"
)

# substitui o trecho antigo: do "for u in users:" até logo antes do commit
old_loop = block[i_for:i_commit]
block_fixed = block[:i_for] + new_loop + block[i_commit:]

# segurança extra: remove qualquer linha "continue" solta que restou no corpo da função
lines = block_fixed.splitlines()
out = []
for ln in lines:
    if ln.strip() == "continue":
        # mantém somente se estiver indentado (>=8) — ou seja, dentro de loop/if
        if len(ln) - len(ln.lstrip(" ")) < 8:
            continue
    out.append(ln)
block_fixed = "\n".join(out) + "\n"

# reconstroi o arquivo
new_txt = txt[:i_def] + block_fixed + rest
p.write_text(new_txt, encoding="utf-8")
print("OK: import_sector refeito (loop corrigido) e continue solto removido.")
