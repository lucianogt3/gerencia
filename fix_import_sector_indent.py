from pathlib import Path
import re

p = Path(r"app\blueprints\nursing\routes.py")
txt = p.read_text(encoding="utf-8")

# Substitui o bloco quebrado dentro do import_sector (onde o for está certo, mas o if admin/manager saiu do loop)
pattern = r'''(?ms)
^\s{4}for u in users:\s*\n
\s{8}u_role = \(getattr\(u, "role", ""\) or ""\)\.lower\(\)\s*\n
\s*\n
\s{4}\# admins/manager não entram como membro de escala\s*\n
\s{4}if u_role in \("admin", "manager"\):\s*\n
\s{8}return jsonify\(\{"error": "Usuário admin/manager não pode ser adicionado à escala"\}\), 400\s*\n
\s{8}role = "nurse" if u_role in \("nurse", "enfermeiro"\) else "technician"\s*\n
\s*\n
\s{8}exists = NursingMonthlyMember\.query\.filter_by\(schedule_id=sched\.id, user_id=u\.id\)\.first\(\)\s*\n
\s{8}if exists:\s*\n
\s{12}skipped \+= 1\s*\n
\s{12}continue\s*\n
\s*\n
\s{8}db\.session\.add\(NursingMonthlyMember\(\s*\n
\s{12}schedule_id=sched\.id,\s*\n
\s{12}user_id=u\.id,\s*\n
\s{12}role=role,\s*\n
\s{12}position=next_position\(role\),\s*\n
\s{12}active=True,\s*\n
\s{8}\)\)\s*\n
\s{8}added \+= 1\s*\n
'''

replacement = '''    for u in users:
        u_role = (getattr(u, "role", "") or "").lower()

        # admins/manager não entram como membro de escala (apenas ignora)
        if u_role in ("admin", "manager"):
            skipped += 1
            continue

        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"

        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
        if exists:
            skipped += 1
            continue

        db.session.add(NursingMonthlyMember(
            schedule_id=sched.id,
            user_id=u.id,
            role=role,
            position=next_position(role),
            active=True,
        ))
        added += 1
'''

txt2, n = re.subn(pattern, replacement, txt)
if n == 0:
    print("ERRO: não achei o bloco para patch. Vou tentar um patch menor do trecho 'admins/manager'...")

    # fallback: tenta só reindentar as linhas 252-269 pela assinatura dos comentários/linhas
    txt2 = txt.replace(
        '    # admins/manager não entram como membro de escala\n    if u_role in ("admin", "manager"):\n        return jsonify({"error": "Usuário admin/manager não pode ser adicionado à escala"}), 400\n        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"\n',
        '        # admins/manager não entram como membro de escala (apenas ignora)\n        if u_role in ("admin", "manager"):\n            skipped += 1\n            continue\n\n        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"\n'
    )
    n = 1

p.write_text(txt2, encoding="utf-8")
print(f"OK: import_sector corrigido (patch aplicado={n}).")
