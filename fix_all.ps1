Write-Host "=== FIX AUTOMÁTICO ESCALA MENSAL ===" -ForegroundColor Cyan

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "❌ venv não encontrado" -ForegroundColor Red
    exit 1
}

$fixes = @(
    "fix_stray_continue.py",
    "fix_transfer_indent.py",
    "fix_import_sector_indent.py",
    "fix_import_sector_loop.py",
    "patch_import_role.py",
    "fix_members_roles_by_users.py",
    "patch_members_payload.py",
    "fix_future_imports.py"
)

foreach ($f in $fixes) {
    if (Test-Path $f) {
        Write-Host "▶ Executando $f" -ForegroundColor Yellow
        python $f
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Erro em $f" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "⚠ $f não encontrado (ignorado)" -ForegroundColor DarkYellow
    }
}

Write-Host "▶ Validando código (compileall)" -ForegroundColor Yellow
python -m compileall app | Out-Host

Write-Host "✅ FIX COMPLETO FINALIZADO" -ForegroundColor Green
