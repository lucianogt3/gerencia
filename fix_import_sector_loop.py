import re
from pathlib import Path

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# Esse erro do "continue not properly in loop" vem de um bloco do import_sector
# que ficou com indentação quebrada (if/continue fora do for).
#
# Vamos corrigir o trecho que começa em "for u in users:" e termina antes do "db.session.commit()"
# Deixando tudo DENTRO do for e mantendo a regra:
# - admin/manager: pula (skipped += 1; continue)
# - nurse/enfermeiro -> role = nurse ; senão technician
# - se já existe: skipped += 1; continue
# - senão adiciona membro

pattern = re.compile(
    r"(for u in users:\n"
    r"(?:[ \t].*\n){0,50}?)"
    r"\n[ \t]*db\.session\.commit\(\)",
    re.MULTILINE
)

m = pattern.search(txt)
if not m:
    print("ERRO: não achei o bloco do loop em import_sector para corrigir.")
    raise SystemExit(1)

old_block = m.group(1)

# Monta bloco correto (indentação consistente)
new_block = (
    "for u in users:\n"
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

# Substitui o bloco antigo pelo novo
txt2 = txt.replace(old_block, new_block)

# Segurança extra: remove qualquer "continue" que esteja no nível errado (fora de loop)
# (normalmente 4 espaços em início de linha dentro da função, sem estar dentro de for/while)
txt2 = re.sub(r"(?m)^\s{4}continue\s*$", "", txt2)

p.write_text(txt2, encoding="utf-8")
print("OK: import_sector loop reindentado e continue inválido removido.")
