# Portal Gerência de Enfermagem (Flask) — Estrutura Modular (Blueprints)

Este projeto é uma base pronta para evoluir módulos separados:
- Auth (login/cadastro/liberação pela gerência)
- Documentos (POPs/Protocolos/Políticas) com contador de abertura/leitura
- Escalas (upload/visualização por ano/mês/categoria/serviço)
- Trocas (estrutura pronta)
- Atestados (estrutura pronta)
- Indicadores (placeholder)

## Requisitos
- Python 3.10+ (recomendado 3.11)

## Rodar no Windows (PowerShell)
```powershell
cd nurse_manager_portal
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
flask --app wsgi run --debug
```

Abrir: http://127.0.0.1:5000

## Criar usuários de teste (seed)
```powershell
flask --app wsgi seed
```

Cria:
- Gerência: gerencia@local / admin123 (matrícula: 9001)
- Colaborador: colab@local / admin123 (matrícula: 1001)

> Troque as senhas depois.

## Uploads
Arquivos vão para: `instance/uploads/`
