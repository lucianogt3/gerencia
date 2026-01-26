from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# acha a função import_sector
m = re.search(r"(?m)^\s*def\s+import_sector\s*\(", txt)
if not m:
    print("ERRO: não encontrei def import_sector(")
    raise SystemExit(1)

start = m.start()
tail = txt[start:]

# corta até próximo decorator/def no mesmo nível
m_end = re.search(r"(?m)^\s*@bp\.", tail[1:]) or re.search(r"(?m)^\s*def\s+\w+\s*\(", tail[1:])
end = (m_end.start()+1) if m_end else len(tail)

block = tail[:end]
rest  = tail[end:]

# acha "for u in users:" (com indent)
mfor = re.search(r"(?m)^(\s*)for\s+u\s+in\s+users\s*:\s*$", block)
if not mfor:
    print("ERRO: não encontrei 'for u in users:' em import_sector")
    raise SystemExit(1)

for_indent = mfor.group(1)          # indent do "for"
inner = for_indent + "    "         # indent interno do loop

# acha commit depois do loop
mcommit = re.search(r"(?m)^\s*db\.session\.commit\(\)\s*$", block[mfor.end():])
if not mcommit:
    print("ERRO: não encontrei db.session.commit() após o loop")
    raise SystemExit(1)

commit_pos = mfor.end() + mcommit.start()

# monta loop correto com indent dinâmico
new_loop = (
    f"{for_indent}for u in users:\n"
    f"{inner}u_role = (getattr(u, \"role\", \"\") or \"\").lower()\n"
    f"{inner}\n"
    f"{inner}# admins/manager não entram como membro de escala\n"
    f"{inner}if u_role in (\"admin\", \"manager\"):\n"
    f"{inner}    skipped += 1\n"
    f"{inner}    continue\n"
    f"{inner}\n"
    f"{inner}role = \"nurse\" if u_role in (\"nurse\", \"enfermeiro\") else \"technician\"\n"
    f"{inner}\n"
    f"{inner}exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()\n"
    f"{inner}if exists:\n"
    f"{inner}    skipped += 1\n"
    f"{inner}    continue\n"
    f"{inner}\n"
    f"{inner}db.session.add(NursingMonthlyMember(\n"
    f"{inner}    schedule_id=sched.id,\n"
    f"{inner}    user_id=u.id,\n"
    f"{inner}    role=role,\n"
    f"{inner}    position=next_position(role),\n"
    f"{inner}    active=True,\n"
    f"{inner}))\n"
    f"{inner}added += 1\n"
)

# substitui do for até antes do commit
block2 = block[:mfor.start()] + new_loop + block[commit_pos:]

# segurança: remove "for u in users:" duplicado vazio (caso tenha sobrado)
block2 = re.sub(r"(?m)^(\s*)for\s+u\s+in\s+users\s*:\s*\n(\s*)$", "", block2)

# escreve arquivo
new_txt = txt[:start] + block2 + rest
p.write_text(new_txt, encoding="utf-8")
print("OK: loop do import_sector refeito com indent correto (fix v3).")
