from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
tmpl = ROOT / "app" / "templates" / "nursing" / "scale_editor.html"

if not tmpl.exists():
    raise SystemExit(f"Não achei: {tmpl}")

t = tmpl.read_text(encoding="utf-8", errors="ignore")

# -----------------------
# 0) Limpar sujeira "corr" que apareceu no HTML
# -----------------------
t = t.replace(" corr       Setor:", "        Setor:")

# -----------------------
# 1) Garantir UTF-8 bom: trocar entidades quebradas comuns
# (isso ajuda quando já virou â€” etc)
# -----------------------
fix_map = {
    "â€”": "—",
    "Â—": "—",
    "â€¢": "•",
    "Â•": "•",
    "â†": "←",
    "Â←": "←",
    "Ã¡": "á",
    "Ã©": "é",
    "Ãª": "ê",
    "Ã£": "ã",
    "Ã§": "ç",
    "Ã³": "ó",
    "Ã´": "ô",
    "Ãº": "ú",
    "Ã­": "í",
    "Ã“": "Ó",
    "Ã‰": "É",
    "ÃŠ": "Ê",
    "Ã‡": "Ç",
    "ðŸ—“ï¸": "🗓️",
    "ðŸ‘¥": "👥",
    "âž•": "➕",
    "â¬‡ï¸": "⬇️",
    "âœ•": "✕",
    "âš™ï¸": "⚙️",
    "â€œ": "“",
    "â€": "”",
}
for k, v in fix_map.items():
    t = t.replace(k, v)

# -----------------------
# 2) Remover PROMPT e ligar modal bonito de célula (#modalCell)
# - cria grid com botões
# - salva no btnSaveCell
# -----------------------

# remove listener antigo de clique na célula (o que usa prompt)
t = re.sub(
    r"(?s)document\.addEventListener\(\"click\", async \(e\) => \{\s*const td = e\.target\.closest\(\"td\.cell\"\).*?\}\);\s*",
    "",
    t,
    count=1
)

# garantir SHIFT_CODES correto (caso tenha sido mexido)
t = re.sub(
    r"const\s+SHIFT_CODES\s*=\s*\[.*?\]\s*;",
    'const SHIFT_CODES = ["D","N","F","FE","FT","AT","LC","EX","CB","RM","—"];',
    t,
    count=1
)

# injetar JS novo (modal cell) antes das ações (⚙️) ou antes do final
marker = "// =========================\n  // ⚙️"
idx = t.find(marker)
if idx == -1:
    idx = t.rfind("function escapeHtml")
    if idx == -1:
        idx = t.rfind("{% endblock %}")

NEW_CELL_JS = r'''
  // =========================
  // EDITAR CÉLULA (modal bonito)
  // =========================
  const modalCell = "#modalCell";
  const shiftGrid = document.getElementById("shiftGrid");
  const btnSaveCell = document.getElementById("btnSaveCell");

  function buildShiftGrid() {
    if (!shiftGrid) return;
    const codes = ["D","N","F","FE","FT","AT","LC","EX","CB","RM","—"];
    const labels = {
      "D": "Diurno",
      "N": "Noturno",
      "F": "Folga",
      "FE": "Férias",
      "FT": "Falta",
      "AT": "Atestado",
      "LC": "Licença",
      "EX": "Extra",
      "CB": "Cobertura",
      "RM": "Remanejamento",
      "—": "Limpar",
    };

    shiftGrid.innerHTML = codes.map(c => `
      <button type="button" class="shift-btn" data-code="${c}">
        <div class="shift-code">${c}</div>
        <div class="shift-label">${labels[c] || ""}</div>
      </button>
    `).join("");
  }
  buildShiftGrid();

  function setSelectedShift(code) {
    document.getElementById("cellShiftVal").value = code;
    if (!shiftGrid) return;
    shiftGrid.querySelectorAll(".shift-btn").forEach(b => {
      b.classList.toggle("active", (b.dataset.code || "") === code);
    });
  }

  // abrir modal ao clicar na célula
  document.addEventListener("click", (e) => {
    const td = e.target.closest("td.cell");
    if (!td) return;

    const userId = Number(td.dataset.userId || 0);
    const day = Number(td.dataset.day || 0);
    const current = (td.dataset.current || "—").trim().toUpperCase() || "—";
    const userName = td.closest("tr")?.querySelector("td strong")?.textContent?.trim() || "—";

    if (!scheduleId || !userId || !day) return;

    document.getElementById("cellUserName").textContent = userName;
    document.getElementById("cellDay").textContent = String(day);
    document.getElementById("cellCurrent").textContent = current;

    document.getElementById("cellUserId").value = String(userId);
    document.getElementById("cellDayVal").value = String(day);

    setSelectedShift(SHIFT_CODES.includes(current) ? current : "—");

    openModal(modalCell);
  });

  // selecionar um código no grid
  if (shiftGrid) {
    shiftGrid.addEventListener("click", (e) => {
      const btn = e.target.closest(".shift-btn");
      if (!btn) return;
      const code = (btn.dataset.code || "—").toUpperCase();
      if (!SHIFT_CODES.includes(code)) return;
      setSelectedShift(code);
    });
  }

  // salvar
  if (btnSaveCell) {
    btnSaveCell.addEventListener("click", async () => {
      const userId = Number(document.getElementById("cellUserId").value || 0);
      const day = Number(document.getElementById("cellDayVal").value || 0);
      const code = (document.getElementById("cellShiftVal").value || "—").trim().toUpperCase();

      if (!userId || !day) return;

      // ✅ limpar manda "" pro backend
      const shiftToSend = (code === "—") ? "" : code;

      try {
        const res = await apiFetch(`/api/nursing/monthly/${scheduleId}/cell`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, day: day, shift: shiftToSend }),
        });

        const j = await res.json().catch(() => ({}));
        if (!res.ok) return alert(j.error || "Falha ao salvar célula");

        // atualiza a UI sem reload
        const td = document.querySelector(`td.cell[data-user-id="${userId}"][data-day="${day}"]`);
        if (td) {
          const uiCode = (code === "—") ? "—" : code;
          td.dataset.current = uiCode;
          td.innerHTML = (uiCode === "—")
            ? `<span class="muted">—</span>`
            : `<span class="pill">${escapeHtml(uiCode)}</span>`;
        }

        closeModal(modalCell);
      } catch (err) {
        alert("Erro de rede ao salvar célula.");
      }
    });
  }
'''

t = t[:idx] + NEW_CELL_JS + "\n\n" + t[idx:]

# -----------------------
# 3) Adicionar CSS do modal grid (no próprio template, simples)
# -----------------------
if ".shift-grid" not in t:
    t = t.replace(
        '<div class="shift-grid" id="shiftGrid"></div>',
        '''<style>
  .shift-grid{
    display:grid;
    grid-template-columns: repeat(4, minmax(140px, 1fr));
    gap:10px;
    margin-top:10px;
  }
  .shift-btn{
    display:flex;
    flex-direction:column;
    gap:4px;
    padding:12px;
    border-radius:14px;
    border:1px solid rgba(255,255,255,.10);
    background:rgba(255,255,255,.04);
    color:inherit;
    cursor:pointer;
    text-align:left;
  }
  .shift-btn:hover{
    border-color: rgba(120,170,255,.55);
    background: rgba(120,170,255,.10);
  }
  .shift-btn.active{
    border-color: rgba(120,170,255,.9);
    background: rgba(120,170,255,.18);
    box-shadow: 0 0 0 2px rgba(120,170,255,.18) inset;
  }
  .shift-code{
    font-weight:900;
    font-size:1.1rem;
  }
  .shift-label{
    font-size:.9rem;
    opacity:.85;
  }
  @media (max-width: 900px){
    .shift-grid{ grid-template-columns: repeat(2, minmax(140px, 1fr)); }
  }
</style>
<div class="shift-grid" id="shiftGrid"></div>'''
    )

# -----------------------
# 4) Salvar em UTF-8 (sem BOM)
# -----------------------
tmpl.write_text(t, encoding="utf-8", newline="\n")
print("OK: scale_editor.html corrigido (UTF-8 + modal bonito + salvar célula).")
