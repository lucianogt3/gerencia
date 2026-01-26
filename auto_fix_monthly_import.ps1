from pathlib import Path
import re

routes = Path(r"app\blueprints\nursing\routes.py")
tmpl   = Path(r"templates\nursing\scale_editor.html")

if not routes.exists():
    raise SystemExit(f"Não achei {routes}")
if not tmpl.exists():
    raise SystemExit(f"Não achei {tmpl}")

txt = routes.read_text(encoding="utf-8")

# -----------------------------
# 1) Corrigir "continue" fora de loop (bloco import_sector quebrado)
# -----------------------------
# Vamos localizar o handler import_sector e garantir indentação correta,
# e principalmente remover blocos inválidos (if/return) fora do for.
# Estratégia: substituir o corpo do import_sector por uma versão segura.

import_sector_pattern = re.compile(
    r"@bp\.post\(\"/monthly/<int:schedule_id>/import_sector\"\)\s*\n"
    r"@login_required\s*\n"
    r"def\s+import_sector\s*\(\s*schedule_id\s*:\s*int\s*\)\s*:\s*\n"
    r"(?:.|\n)*?(?=\n@bp\.)",
    re.M
)

safe_import_sector = r'''@bp.post("/monthly/<int:schedule_id>/import_sector")
@login_required
def import_sector(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)

    # 🔒 se publicado (histórico), não altera
    if getattr(sched, "status", "") == "published":
        return jsonify({"error": "Escala publicada. Não pode alterar."}), 409

    data = request.get_json(silent=True) or {}
    auto_fill = bool(data.get("auto_fill", True))

    # usuários ativos do setor do schedule
    users = (User.query
             .filter(User.status == "active", User.sector_id == sched.sector_id)
             .order_by(User.nome.asc())
             .all())

    added = 0
    skipped = 0

    def next_position(role: str) -> int:
        last = (NursingMonthlyMember.query
                .filter_by(schedule_id=sched.id, role=role, active=True)
                .order_by(NursingMonthlyMember.position.desc())
                .first())
        return (last.position + 1) if last else 1

    for u in users:
        u_role = (getattr(u, "role", "") or "").lower()

        # admins/manager não entram como membro de escala
        if u_role in ("admin", "manager"):
            skipped += 1
            continue

        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"

        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
        if exists:
            # reativa se estava inativo
            if hasattr(exists, "active") and not bool(exists.active):
                exists.active = True
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

    db.session.commit()

    # opcional: auto_fill (se você tiver função pronta, plugue aqui)
    # if auto_fill:
    #     _autofill_month(sched)

    return jsonify({
        "ok": True,
        "schedule_id": sched.id,
        "sector_id": sched.sector_id,
        "imported": added,
        "skipped": skipped,
        "auto_fill": auto_fill,
    }), 200
'''

if import_sector_pattern.search(txt):
    txt = import_sector_pattern.sub(safe_import_sector + "\n\n", txt, count=1)
else:
    print("AVISO: não achei import_sector para substituir (talvez mudou).")


# -----------------------------
# 2) Garantir rota /sector_users
# -----------------------------
if 'def sector_users(' not in txt:
    insert_after = 'def import_sector(schedule_id: int):'
    # inserir logo após import_sector (antes do próximo @bp.)
    block = r'''
@bp.get("/monthly/<int:schedule_id>/sector_users")
@login_required
def sector_users(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)
    sector = Sector.query.get(sched.sector_id)

    users = (User.query
             .filter(User.status == "active", User.sector_id == sched.sector_id)
             .order_by(User.nome.asc())
             .all())

    items = []
    for u in users:
        # já está na escala?
        already = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id, active=True).first() is not None
        u_role = (getattr(u, "role", "") or "").lower()
        if u_role in ("admin", "manager"):
            continue

        items.append({
            "id": u.id,
            "name": (u.nome or "").strip(),
            "matricula": getattr(u, "matricula", "") or "",
            "turno": getattr(u, "turno", None),
            "role": "nurse" if u_role in ("nurse","enfermeiro") else "technician",
            "sector_id": sched.sector_id,
            "sector_name": (sector.name if sector else None) or "",
            "already_in": already,
        })

    return jsonify(items), 200
'''
    # coloca antes do próximo @bp.post("/monthly/<int:schedule_id>/publish") se existir
    m = re.search(r"@bp\.post\(\"/monthly/<int:schedule_id>/publish\"\)", txt)
    if m:
        txt = txt[:m.start()] + block + "\n" + txt[m.start():]
    else:
        txt += "\n" + block + "\n"


# -----------------------------
# 3) Garantir rota /import_selected
# -----------------------------
if 'def import_selected(' not in txt:
    block = r'''
@bp.post("/monthly/<int:schedule_id>/import_selected")
@login_required
def import_selected(schedule_id: int):
    if not _require_manager():
        return jsonify({"error": "Sem permissão"}), 403

    sched = NursingMonthlySchedule.query.get_or_404(schedule_id)

    if getattr(sched, "status", "") == "published":
        return jsonify({"error": "Escala publicada. Não pode alterar."}), 409

    data = request.get_json(silent=True) or {}
    user_ids = data.get("user_ids") or []
    auto_fill = bool(data.get("auto_fill", True))

    try:
        user_ids = [int(x) for x in user_ids]
    except Exception:
        user_ids = []

    if not user_ids:
        return jsonify({"error": "user_ids é obrigatório"}), 400

    users = (User.query
             .filter(User.id.in_(user_ids), User.status == "active")
             .order_by(User.nome.asc())
             .all())

    added = 0
    skipped = 0

    def next_position(role: str) -> int:
        last = (NursingMonthlyMember.query
                .filter_by(schedule_id=sched.id, role=role, active=True)
                .order_by(NursingMonthlyMember.position.desc())
                .first())
        return (last.position + 1) if last else 1

    for u in users:
        u_role = (getattr(u, "role", "") or "").lower()
        if u_role in ("admin", "manager"):
            skipped += 1
            continue

        role = "nurse" if u_role in ("nurse", "enfermeiro") else "technician"

        exists = NursingMonthlyMember.query.filter_by(schedule_id=sched.id, user_id=u.id).first()
        if exists:
            if hasattr(exists, "active") and not bool(exists.active):
                exists.active = True
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

    db.session.commit()

    # opcional: auto_fill
    # if auto_fill:
    #     _autofill_month(sched)

    return jsonify({"ok": True, "added": added, "skipped": skipped, "auto_fill": auto_fill}), 200
'''
    m = re.search(r"@bp\.post\(\"/monthly/<int:schedule_id>/publish\"\)", txt)
    if m:
        txt = txt[:m.start()] + block + "\n" + txt[m.start():]
    else:
        txt += "\n" + block + "\n"


routes.write_text(txt, encoding="utf-8")
print("OK: routes.py corrigido/atualizado (import_sector + sector_users + import_selected).")

# -----------------------------
# 4) Corrigir template scale_editor.html
# -----------------------------
t = tmpl.read_text(encoding="utf-8")

# Remover scripts após endblock (qualquer coisa depois do endblock)
t = re.sub(r"(?s)\{% endblock %\}.*$", "{% endblock %}\n", t)

# Garantir que exista o container sectorUsersBox e controles no modalImport
if 'id="sectorUsersBox"' not in t:
    t = t.replace(
        '<div class="alert warn" style="margin-top:12px;">',
        '''
      <div style="margin-top:12px;">
        <div style="display:flex; gap:10px; align-items:center; justify-content:space-between;">
          <label class="check" style="display:flex;gap:10px;align-items:center;">
            <input type="checkbox" id="selectAllSectorUsers">
            <span>Selecionar todos</span>
          </label>

          <input class="input" id="filterSectorUsers" type="search"
                 placeholder="Filtrar por nome ou matrícula..."
                 style="max-width: 320px;">
        </div>

        <div id="sectorUsersBox"
             style="margin-top:10px; max-height:260px; overflow:auto; padding:8px;
                    border-radius:12px; border:1px solid rgba(255,255,255,.08);">
          <div class="muted">Carregando...</div>
        </div>

        <div class="muted" id="sectorUsersCount" style="margin-top:8px;">
          —
        </div>
      </div>

        <div class="alert warn" style="margin-top:12px;">
'''
    )

# Trocar listeners de abrir modal import para usar openImportModal()
t = t.replace(
    'if (btnImportSector1) btnImportSector1.addEventListener("click", () => openModal("#modalImport"));',
    'if (btnImportSector1) btnImportSector1.addEventListener("click", () => openImportModal());'
)
t = t.replace(
    'if (btnImportSector2) btnImportSector2.addEventListener("click", () => openModal("#modalImport"));',
    'if (btnImportSector2) btnImportSector2.addEventListener("click", () => openImportModal());'
)

# Trocar endpoint do confirmImport para import_selected
t = re.sub(
    r"fetch\(`/api/nursing/monthly/\$\{scheduleId\}/import_sector`",
    "fetch(`/api/nursing/monthly/${scheduleId}/import_selected`",
    t
)

# Inserir JS utilitário (openImportModal/loadSectorUsers) se não existir
if "function openImportModal()" not in t:
    js_insert = r'''
  let sectorUsersCache = [];

  async function openImportModal() {
    openModal("#modalImport");
    await loadSectorUsers();
  }

  async function loadSectorUsers() {
    const box = document.getElementById("sectorUsersBox");
    const count = document.getElementById("sectorUsersCount");
    const filter = document.getElementById("filterSectorUsers");
    const selAll = document.getElementById("selectAllSectorUsers");

    if (!box) return;

    box.innerHTML = '<div class="muted">Carregando usuários...</div>';
    if (count) count.textContent = "—";

    try {
      const res = await fetch(`/api/nursing/monthly/${scheduleId}/sector_users`);
      const users = await res.json().catch(() => []);

      if (!res.ok) {
        box.innerHTML = `<div class="alert danger">Erro ao carregar usuários.</div>`;
        return;
      }

      sectorUsersCache = Array.isArray(users) ? users : [];
      renderSectorUsers();

      if (filter) {
        filter.value = "";
        filter.oninput = () => renderSectorUsers();
      }

      if (selAll) {
        selAll.checked = false;
        selAll.onchange = () => {
          const checks = box.querySelectorAll("input.ucheck:not(:disabled)");
          checks.forEach(c => { c.checked = selAll.checked; });
          updateCount();
        };
      }

      box.addEventListener("change", (ev) => {
        if (ev.target && ev.target.classList && ev.target.classList.contains("ucheck")) {
          updateCount();
        }
      });

      updateCount();

    } catch (e) {
      box.innerHTML = `<div class="alert danger">Erro de rede ao carregar usuários.</div>`;
    }
  }

  function renderSectorUsers() {
    const box = document.getElementById("sectorUsersBox");
    const filter = (document.getElementById("filterSectorUsers")?.value || "").trim().toLowerCase();

    if (!box) return;

    let users = sectorUsersCache;

    if (filter) {
      users = users.filter(u => {
        const name = String(u.name || "").toLowerCase();
        const mat = String(u.matricula || "").toLowerCase();
        return name.includes(filter) || mat.includes(filter);
      });
    }

    if (!users.length) {
      box.innerHTML = `<div class="muted">Nenhum usuário encontrado.</div>`;
      updateCount();
      return;
    }

    box.innerHTML = users.map(u => `
      <label style="display:flex;gap:10px;align-items:flex-start;padding:8px;border-radius:10px;
                    border:1px solid rgba(255,255,255,.06); margin-bottom:8px;
                    opacity:${u.already_in ? "0.65" : "1"};">
        <input type="checkbox" class="ucheck" value="${Number(u.id || 0)}"
               ${u.already_in ? "checked disabled" : ""}>
        <div style="flex:1;">
          <div style="font-weight:700;">${escapeHtml(u.name || "")}</div>
          <div class="muted" style="font-size:.85rem;">
            ${escapeHtml(u.matricula || "—")} • ${escapeHtml(u.role || "—")}
            ${u.already_in ? " • (já está na escala)" : ""}
          </div>
        </div>
      </label>
    `).join("");

    updateCount();
  }

  function getSelectedSectorUsers() {
    const box = document.getElementById("sectorUsersBox");
    if (!box) return [];
    const checks = Array.from(box.querySelectorAll("input.ucheck:checked"));
    return checks.filter(c => !c.disabled).map(c => Number(c.value || 0)).filter(Boolean);
  }

  function updateCount() {
    const total = sectorUsersCache.length;
    const selected = getSelectedSectorUsers().length;
    const count = document.getElementById("sectorUsersCount");
    if (count) count.textContent = `Usuários no setor: ${total} • Selecionados para importar: ${selected}`;
  }
'''
    # inserir logo após open/close modal helpers (antes do confirmImport)
    t = t.replace('  const confirmImport = document.getElementById("confirmImport");', js_insert + "\n\n  const confirmImport = document.getElementById(\"confirmImport\");")

# Ajustar confirmImport para enviar user_ids
t = re.sub(
    r"body:\s*JSON\.stringify\(\{\s*auto_fill:\s*autoFill\s*\}\s*\)",
    "body: JSON.stringify({ user_ids: getSelectedSectorUsers(), auto_fill: autoFill })",
    t
)

# Se não tem validação de selecionar pelo menos 1
if "Selecione pelo menos 1 usuário" not in t:
    t = t.replace(
        '      try {',
        '      const selected = getSelectedSectorUsers();\n      if (!selected.length) {\n        alert("Selecione pelo menos 1 usuário para importar.");\n        return;\n      }\n\n      try {'
    )

tmpl.write_text(t, encoding="utf-8")
print("OK: scale_editor.html atualizado (checkbox no import + import_selected).")

print("PRONTO.")
