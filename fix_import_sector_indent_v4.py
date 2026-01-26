from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# 1) acha import_sector
m = re.search(r"(?m)^(\s*)def\s+import_sector\s*\(", txt)
if not m:
    print("ERRO: def import_sector não encontrado")
    raise SystemExit(1)

fn_indent = m.group(1)
start = m.start()
tail = txt[start:]

# 2) pega bloco da função até próximo decorator/def no mesmo nível
m_end = re.search(r"(?m)^(?:" + re.escape(fn_indent) + r")(@bp\.|def\s+\w+\s*\()", tail[1:])
end = (m_end.start()+1) if m_end else len(tail)

block = tail[:end]
rest  = tail[end:]

# 3) encontra "users =" e "for u in users:"
m_users = re.search(r"(?m)^\s*users\s*=\s*.*$", block)
m_for   = re.search(r"(?m)^(\s*)for\s+u\s+in\s+users\s*:\s*$", block)

if not m_for:
    print("ERRO: for u in users: não encontrado dentro de import_sector")
    raise SystemExit(1)

for_indent = m_for.group(1)
inner = for_indent + "    "

# 4) encontra db.session.commit() depois do loop
m_commit = re.search(r"(?m)^\s*db\.session\.commit\(\)\s*$", block[m_for.end():])
if not m_commit:
    print("ERRO: db.session.commit() não encontrado após o loop")
    raise SystemExit(1)

commit_pos = m_for.end() + m_commit.start()

# 5) remove qualquer linha "u_role = ..." com indent esquisito fora do loop dentro da função
# (isso é o que causa unexpected indent)
block = re.sub(r"(?m)^\s+u_role\s*=\s*\(getattr\(u,\s*\"role\".*\)\.lower\(\)\s*$", "", block)

# 6) monta loop correto
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

# 7) substitui do "for u in users" até antes do commit
block2 = block[:m_for.start()] + new_loop + block[commit_pos:]

# 8) escreve de volta
new_txt = txt[:start] + block2 + rest
p.write_text(new_txt, encoding="utf-8")
print("OK: import_sector loop reconstruído e 'u_role' solto removido.")
